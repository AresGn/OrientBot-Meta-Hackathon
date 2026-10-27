"""Spike E0.5 (issue #7): does Muse Voice Transcribe read the French voice notes?

Throwaway script. Converts each MP3 of data/samples/ to the WAV format required by the
file endpoint, adds a noisy copy of the contradictory note, sends each clip once (with and
without keyword biasing for the contradictory note) to
POST /asr/transcribe, and writes the raw JSON answer plus a word-by-word diff against
the spoken text to docs/spikes/voice/. A last call sends the MP3 unconverted to check
the documented "WAV only" rule. Only the docs/ output matters.

Usage: python scripts/spike_voice.py
"""

import difflib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.make_voice_notes import VOICE_NOTES  # noqa: E402
from src.clients.meta_client import get_client  # noqa: E402

# https://dev.meta.ai/docs/api-reference/voice/transcribe and .../voice/schemas
MODEL = "muse-voice-transcribe-1.0"
TRANSCRIBE_PATH = "asr/transcribe"
SAMPLE_RATE = 24000  # engine-native rate, https://dev.meta.ai/docs/speech-to-text
LANGUAGE_BIAS = ["French"]  # free-text language names, https://dev.meta.ai/docs/api-reference/voice/schemas
# Recognition biasing, same page; the terms the agent cannot afford to mishear
KEYWORDS = ["série D", "SVT", "Cotonou"]
TIMEOUT_SECONDS = 120
# White-noise amplitude per case; the note's mean level is -34.2 dBFS (ffmpeg volumedetect), so
# 0.01 (-44.8 dBFS RMS) gives about +10 dB SNR and 0.08 (-26.7 dBFS RMS) about -7.5 dB SNR
NOISE_AMPLITUDES = {"moderee": 0.01, "forte": 0.08}
RUNS = 2  # the first manual run showed the transcript changes between calls
SAMPLES_DIR = ROOT / "data" / "samples"
OUT_DIR = ROOT / "docs" / "spikes" / "voice"
CONTRADICTORY = "note_vocale_contradictoire.mp3"
COHERENT = "note_vocale_coherente.mp3"


def convert_to_wav(source: Path, target: Path, noise_amplitude: float | None) -> None:
    """ffmpeg command from https://dev.meta.ai/docs/speech-to-text, optionally mixed with white noise."""
    command = ["ffmpeg", "-y", "-v", "error", "-i", str(source)]
    if noise_amplitude:
        command += ["-f", "lavfi", "-i", f"anoisesrc=color=white:amplitude={noise_amplitude}:sample_rate={SAMPLE_RATE}",
                    "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0"]
    command += ["-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-map_metadata", "-1", str(target)]
    subprocess.run(command, check=True)


def transcribe(client, audio_path: Path, audio_encoding: str, content_type: str,
               keywords: list[str] | None = None) -> httpx.Response:
    request = {"model": MODEL, "audioEncoding": audio_encoding, "languageBias": LANGUAGE_BIAS}
    if keywords:
        request["keywords"] = keywords
    return httpx.post(
        f"{client.base_url}{TRANSCRIBE_PATH}",
        headers={"Authorization": f"Bearer {client.api_key}", "Accept": "application/json"},
        files={"request": (None, json.dumps(request), "application/json"),
               "audio": (audio_path.name, audio_path.read_bytes(), content_type)},
        timeout=TIMEOUT_SECONDS,
    )


def split_words(text: str) -> list[str]:
    """Lowercase words without punctuation: the diff is about words heard, not about commas."""
    return re.findall(r"[\w']+", text.lower().replace("’", "'"))


def diff_words(expected: str, transcript: str) -> list[dict]:
    expected_words, heard_words = split_words(expected), split_words(transcript)
    matcher = difflib.SequenceMatcher(a=expected_words, b=heard_words, autojunk=False)
    return [{"op": op, "expected": " ".join(expected_words[i1:i2]), "heard": " ".join(heard_words[j1:j2])}
            for op, i1, i2, j1, j2 in matcher.get_opcodes() if op != "equal"]


def run_case(client, run_dir: Path, name: str, wav_path: Path, expected: str, keywords: list[str] | None) -> dict:
    response = transcribe(client, wav_path, "WAV", "audio/wav", keywords)
    (run_dir / f"{name}.raw.json").write_text(response.text, encoding="utf-8")
    result = {"case": name, "status": response.status_code, "wav_bytes": wav_path.stat().st_size,
              "keywords": keywords}
    if response.status_code == 200:
        body = response.json()
        result["response_fields"] = sorted(body)
        result["word_diff"] = diff_words(expected, body["transcript"])
        result["word_count_expected"] = len(split_words(expected))
    print(f"{run_dir.name}/{name}: HTTP {response.status_code}, {len(result.get('word_diff', []))} differences")
    return result


def build_cases() -> list[tuple[str, str, float | None, list[str] | None]]:
    cases = [("contradictoire", CONTRADICTORY, None, None),
             ("contradictoire_mots_cles", CONTRADICTORY, None, KEYWORDS),
             ("coherente", COHERENT, None, None)]
    for level, amplitude in NOISE_AMPLITUDES.items():
        cases += [(f"contradictoire_bruit_{level}", CONTRADICTORY, amplitude, None),
                  (f"contradictoire_bruit_{level}_mots_cles", CONTRADICTORY, amplitude, KEYWORDS)]
    return cases


def main() -> None:
    client = get_client()
    results = []
    with tempfile.TemporaryDirectory() as work_dir:
        work = Path(work_dir)
        for name, mp3_name, noise_amplitude, _ in build_cases():
            convert_to_wav(SAMPLES_DIR / mp3_name, work / f"{name}.wav", noise_amplitude)
        for run in range(1, RUNS + 1):
            run_dir = OUT_DIR / f"run{run}"
            run_dir.mkdir(parents=True, exist_ok=True)
            for name, mp3_name, _, keywords in build_cases():
                result = run_case(client, run_dir, name, work / f"{name}.wav", VOICE_NOTES[mp3_name], keywords)
                results.append({"run": run, **result})
    mp3_response = transcribe(client, SAMPLES_DIR / CONTRADICTORY, "WAV", "audio/mpeg")
    (OUT_DIR / "mp3_unconverted.raw.txt").write_text(f"HTTP {mp3_response.status_code}\n{mp3_response.text}\n",
                                                     encoding="utf-8")
    summary = {"model": MODEL, "endpoint": f"POST {client.base_url}{TRANSCRIBE_PATH}",
               "audio_format": f"WAV mono pcm_s16le {SAMPLE_RATE} Hz", "language_bias": LANGUAGE_BIAS,
               "noise_amplitudes": NOISE_AMPLITUDES, "mp3_unconverted_status": mp3_response.status_code,
               "cases": results}
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
