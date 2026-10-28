import re
import subprocess
import tempfile
import wave
from pathlib import Path

import httpx

from src.clients.meta_client import get_client
from src.clients.voice import SAMPLE_RATE, convert_to_wav, request_transcript

SUPPORTED_AUDIO_TYPES = {".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".webm"}
MAX_AUDIO_BYTES = 32 * 1024 * 1024  # request body limit, else HTTP 413 (docs/decisions.md E0.5)
MAX_DURATION_SECONDS = 10 * 60  # clip limit, else HTTP 400 (same source)
# French number words heard in grades, normalized to digits so "quatorze" reads 14
# (E0.5: the API spells numbers out; the eval case voice_contradicts_sheet says "14").
# "un"/"une" are left out on purpose: they are usually articles, not grades.
# Hyphenated compounds ("quatre-vingt-dix") are left untouched: standalone words only.
NUMBER_WORDS = {
    "zéro": "0", "zero": "0", "deux": "2", "trois": "3", "quatre": "4", "cinq": "5",
    "six": "6", "sept": "7", "huit": "8", "neuf": "9", "dix": "10", "onze": "11",
    "douze": "12", "treize": "13", "quatorze": "14", "quinze": "15", "seize": "16",
    "dix-sept": "17", "dix sept": "17", "dix-huit": "18", "dix huit": "18",
    "dix-neuf": "19", "dix neuf": "19", "vingt": "20",
}
_NUMBER_PATTERN = re.compile(
    r"(?<![\w-])(" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")(?![\w-])",
    re.IGNORECASE)


class TranscriptionError(ValueError):
    """The voice note could not be transcribed; the caller asks the student instead of guessing."""


def transcribe_voice(audio_path: str, client=None) -> dict:
    """Transcribe a voice note into {"text", "text_normalized", "confidence"}.

    `text` is the transcript as heard: this is the field E2.2 quotes and the
    `transcript` proofs point to. `text_normalized` is the same text with
    standalone French number words as digits ("quatorze" reads 14), for number
    extraction only. `confidence` is None until the API provides one (it
    currently does not, E0.5), so the agent confirms the series (FR-4).
    Any failure is a TranscriptionError, never an empty text presented as a success.
    """
    path = _check_audio_file(audio_path)
    with tempfile.TemporaryDirectory(prefix="pathproof-voice-") as work_dir:
        wav_path = _prepare_wav(path, Path(work_dir))
        _check_converted_wav(wav_path)
        try:
            response = request_transcript(client or get_client(), wav_path)
        except httpx.HTTPError as error:
            raise TranscriptionError(f"transcription request failed: {error}") from error
    if response.status_code != 200:
        raise TranscriptionError(
            f"transcription API error {response.status_code}: {response.text[:200]}")
    try:
        body = response.json()
    except ValueError as error:
        raise TranscriptionError(f"transcription answer is not valid JSON: {error}") from error
    transcript = body.get("transcript") if isinstance(body, dict) else None
    if not isinstance(transcript, str) or not transcript.strip():
        raise TranscriptionError("empty transcript: nothing heard, asking the student instead")
    return {"text": transcript, "text_normalized": _normalize_number_words(transcript),
            "confidence": body.get("confidence")}


def _check_audio_file(audio_path: str) -> Path:
    path = Path(audio_path)
    if not path.is_file():
        raise TranscriptionError(f"audio not found: {audio_path}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_TYPES:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_TYPES))
        raise TranscriptionError(f"unsupported audio type: {path.suffix!r} (use {supported})")
    size = path.stat().st_size
    if size == 0:
        raise TranscriptionError(f"empty audio file: {audio_path}")
    if size > MAX_AUDIO_BYTES:
        raise TranscriptionError(f"audio too large: {size} bytes (32 MB at most)")
    return path


def _prepare_wav(path: Path, work_dir: Path) -> Path:
    target = work_dir / f"{path.stem}.wav"
    try:
        convert_to_wav(path, target)
    except FileNotFoundError as error:
        raise TranscriptionError("ffmpeg is not installed: cannot convert the audio") from error
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise TranscriptionError(f"audio conversion failed: {error}") from error
    return target


def _check_converted_wav(wav_path: Path) -> None:
    if not wav_path.is_file():
        raise TranscriptionError(f"conversion produced no file: {wav_path.name}")
    size = wav_path.stat().st_size
    if size > MAX_AUDIO_BYTES:
        raise TranscriptionError(f"converted audio too large: {size} bytes (32 MB at most)")
    try:
        with wave.open(str(wav_path), "rb") as wav:
            channels, width, rate, frames = (wav.getnchannels(), wav.getsampwidth(),
                                             wav.getframerate(), wav.getnframes())
    except (wave.Error, EOFError, OSError) as error:
        raise TranscriptionError(f"conversion produced an unreadable WAV: {wav_path.name}") from error
    if channels != 1 or width != 2 or rate != SAMPLE_RATE:
        raise TranscriptionError(
            f"conversion produced an unexpected WAV: {wav_path.name} "
            f"(mono 16-bit PCM at {SAMPLE_RATE} Hz only)")
    if frames / rate > MAX_DURATION_SECONDS:
        raise TranscriptionError(
            f"audio too long: {frames / rate:.0f} seconds (10 minutes at most)")


def _normalize_number_words(transcript: str) -> str:
    return _NUMBER_PATTERN.sub(lambda match: NUMBER_WORDS[match.group(0).lower()], transcript)
