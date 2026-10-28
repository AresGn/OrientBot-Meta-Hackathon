"""Voice transcription call; the only place that knows the model parameters for it."""
import json
import subprocess
from pathlib import Path

import httpx

# https://dev.meta.ai/docs/api-reference/voice/transcribe and .../voice/schemas
VOICE_MODEL = "muse-voice-transcribe-1.0"
TRANSCRIBE_PATH = "asr/transcribe"
SAMPLE_RATE = 24000  # engine-native rate, https://dev.meta.ai/docs/speech-to-text
LANGUAGE_BIAS = ["French"]  # free-text language names, .../voice/schemas
# Recognition biasing, same page: the terms the agent cannot afford to mishear.
# Both supported series (E1.1) plus the domain words the E0.5 spike tested.
KEYWORDS = ["série C", "série D", "SVT", "Cotonou"]
TIMEOUT_SECONDS = 120


def convert_to_wav(source: Path, target: Path) -> None:
    """Convert any audio ffmpeg reads to the WAV the endpoint requires.

    Mono 16-bit PCM at 24 kHz (the API rejects anything else with a 400,
    docs/decisions.md E0.5). Command from https://dev.meta.ai/docs/speech-to-text.
    """
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(source), "-ac", "1",
                    "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-map_metadata", "-1",
                    str(target)], check=True)


def request_transcript(client, wav_path: Path, keywords: list[str] | None = None):
    """POST the WAV to the transcribe endpoint; return the raw HTTP response."""
    request = {"model": VOICE_MODEL, "audioEncoding": "WAV", "languageBias": LANGUAGE_BIAS,
               "keywords": keywords if keywords is not None else KEYWORDS}
    return httpx.post(
        f"{client.base_url}{TRANSCRIBE_PATH}",
        headers={"Authorization": f"Bearer {client.api_key}", "Accept": "application/json"},
        files={"request": (None, json.dumps(request), "application/json"),
               "audio": (wav_path.name, wav_path.read_bytes(), "audio/wav")},
        timeout=TIMEOUT_SECONDS,
    )
