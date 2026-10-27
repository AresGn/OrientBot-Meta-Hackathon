"""Generate the fictional voice notes of data/samples/ with ElevenLabs (story E0.3, issue #5).

Reads ELEVENLABS_API_KEY from .env (never printed). Each note must last 30 to 60 s;
the duration is checked with ffprobe after generation.

Usage: python scripts/make_voice_notes.py [file_name ...]   (default: all notes)
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT_DIR / "data" / "samples"
API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
VOICE_ID = "cYITNPiqwVi5OklXGv3H"  # young female voice, West African French accent (ElevenLabs library)
MODEL_ID = "eleven_multilingual_v2"
# Lower stability = more natural, varied delivery; docs.elevenlabs.io voice settings
VOICE_SETTINGS = {"stability": 0.35, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True, "speed": 0.95}
MIN_SECONDS, MAX_SECONDS = 30, 60  # issue #5 acceptance criteria

# Same student as releve_serie_d.jpg: moyenne générale 11,20
VOICE_NOTES = {
    "note_vocale_coherente.mp3": (
        "Bonjour... Alors, euh, je suis en terminale, série D, D comme Daniel. Au bac, j'ai eu onze virgule deux de moyenne. "
        "Ce que j'aime le plus, c'est la biologie, les SVT... vraiment, c'est ma matière préférée. "
        "Plus tard, j'aimerais travailler dans la santé... peut-être médecin. "
        "Depuis petite, je veux soigner les gens, aider ma famille, mon quartier. "
        "Pour la ville, euh... je préfère rester à Cotonou, près de mes parents. "
        "Et, honnêtement, j'aurai besoin d'une bourse, parce que les études, ça coûte cher chez nous. "
        "Voilà... merci de m'écouter."
    ),
    # docs/prd.md section 2.1, kept word for word, with spoken fillers around it
    "note_vocale_contradictoire.mp3": (
        "Euh... oui, bonjour. Bonjour, je suis en série D, j'ai eu 14 de moyenne. "
        "Voilà... J'aime beaucoup la biologie et j'aimerais travailler dans la santé, peut-être médecin. "
        "Au lycée, ce que je préférais, c'était les travaux pratiques en SVT, avec le microscope. "
        "Je préfère rester à Cotonou, et j'aurai besoin d'une bourse. "
        "Mes parents m'ont dit de bien chercher les filières où il y a des bourses... "
        "Donc, euh, je compte sur vous pour m'aider à choisir. Merci beaucoup, hein."
    ),
}


def read_api_key() -> str:
    for line in (ROOT_DIR / ".env").read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "ELEVENLABS_API_KEY" and value.strip():
            return value.strip()
    raise RuntimeError("ELEVENLABS_API_KEY missing from .env")


def synthesize_speech(text: str, api_key: str) -> bytes:
    body = json.dumps({"text": text, "model_id": MODEL_ID, "voice_settings": VOICE_SETTINGS}).encode()
    request = urllib.request.Request(
        API_URL.format(voice_id=VOICE_ID), data=body, method="POST",
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def measure_duration(path: Path) -> float:
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(output.stdout.strip())


def main() -> None:
    api_key = read_api_key()
    selected_names = sys.argv[1:] or list(VOICE_NOTES)
    for file_name in selected_names:
        text = VOICE_NOTES[file_name]
        path = SAMPLES_DIR / file_name
        path.write_bytes(synthesize_speech(text, api_key))
        duration = measure_duration(path)
        status = "OK" if MIN_SECONDS <= duration <= MAX_SECONDS else "HORS 30-60 s"
        print(f"{file_name}: {duration:.1f} s, {os.path.getsize(path) / 1e6:.2f} Mo, {status}")


if __name__ == "__main__":
    main()
