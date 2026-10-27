"""Spike E0.4 (issue #6): can muse-spark-1.3 read the series D sheet into stable JSON?

Throwaway script: sends data/samples/releve_serie_d.jpg RUNS times with a strict JSON
instruction, writes each parsed answer to docs/spikes/vision/runN.json and the token
usage to docs/spikes/vision/usage.json. Only the docs/ output matters.

Usage: python scripts/spike_vision.py
"""

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.clients.meta_client import get_client  # noqa: E402

MODEL = "muse-spark-1.3"
RUNS = 3  # issue #6
MAX_TOKENS = 8000  # reasoning tokens count against max_tokens (AGENTS.md)
IMAGE_PATH = ROOT / "data" / "samples" / "releve_serie_d.jpg"
OUT_DIR = ROOT / "docs" / "spikes" / "vision"
# data/samples/README.md
EXPECTED_NOTES = {"SCIENCES DE LA VIE ET DE LA TERRE": 15, "MATHEMATIQUES": 12, "PHYSIQUE, CHIMIE ET TECHNOLOGIE": 12}

INSTRUCTION = """Tu lis un relevé de notes du Bac. Recopie uniquement ce qui est imprimé, sans rien calculer.
Réponds avec un seul objet JSON, sans texte autour, sans bloc de code, exactement de cette forme :
{"serie": "<lettre>", "matieres": [{"matiere": "<nom exact imprimé>", "note": <nombre ou null>, "coeff": <entier ou null>, "lisible": <true|false>}], "moyenne_affichee": <nombre ou null>}
Règles : une entrée par ligne du tableau, EPS comprise, sans les lignes de total ; virgule décimale convertie en point ;
si une valeur ne se lit pas, mets null et "lisible": false. Ne devine jamais."""


def build_messages(image_path: Path) -> list[dict]:
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    return [{
        "role": "user",
        "content": [
            {"type": "text", "text": INSTRUCTION},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
        ],
    }]


def check_expected_notes(sheet: dict) -> dict[str, bool]:
    notes = {row["matiere"].strip().upper(): row["note"] for row in sheet.get("matieres", [])}
    return {matiere: notes.get(matiere) == note for matiere, note in EXPECTED_NOTES.items()}


def main() -> None:
    client = get_client()
    messages = build_messages(IMAGE_PATH)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    usage_rows = []
    for run in range(1, RUNS + 1):
        response = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=MAX_TOKENS)
        choice = response.choices[0]
        raw = choice.message.content or ""
        (OUT_DIR / f"run{run}.raw.txt").write_text(raw, encoding="utf-8")
        sheet = json.loads(raw)
        (OUT_DIR / f"run{run}.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        usage = response.usage.model_dump() if response.usage else {}
        usage_rows.append({"run": run, "finish_reason": choice.finish_reason, "usage": usage,
                           "expected_notes_ok": check_expected_notes(sheet)})
        print(f"run {run}: finish={choice.finish_reason} usage={usage} expected={usage_rows[-1]['expected_notes_ok']}")
    summary = {"model": MODEL, "max_tokens": MAX_TOKENS, "image": IMAGE_PATH.name,
               "image_bytes": IMAGE_PATH.stat().st_size, "image_format": "data URL base64 image/jpeg",
               "runs": usage_rows}
    (OUT_DIR / "usage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
