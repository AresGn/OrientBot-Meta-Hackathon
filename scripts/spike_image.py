"""Spike E0.8 (issue #46): can muse-image-1.0 draw a parent card without wrong figures?

Throwaway script: sends the series D sheet figures to the image endpoint RUNS times, saves
the raw images to docs/spikes/image/runN.png, and renders the same data with code
(HTML to PNG through a local headless Chrome or Edge) to docs/spikes/image/code_render.png.
The generated image is never a verified report (it does not go through verify_report).

Usage: python scripts/spike_image.py
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.clients.meta_client import get_client  # noqa: E402

MODEL = "muse-image-1.0"  # https://dev.meta.ai/docs/image-generation
RUNS = 3  # issue #46
SIZE = "1024x1536"  # aspect ratio only, per the official doc
OUTPUT_FORMAT = "png"
OUT_DIR = ROOT / "docs" / "spikes" / "image"
BROWSER_CANDIDATES = [
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
]

# data/samples/README.md (releve_serie_d.jpg) and data/offres_publiques_2026_2027.csv
CARD = {
    "moyenne_bac": "11,2",
    "moyenne_classement_medecine": "13,15",
    "formule": "(SVT × 5 + Maths × 4 + PCT × 4) / 13",
    "filieres": [
        {"offre_id": "PUB-062", "nom": "Médecine Générale", "etablissement": "Faculté des Sciences de la Santé (FSS)",
         "bourse": 95, "aide_fpp": 20, "total": 115},
        {"offre_id": "PUB-133", "nom": "Médecine Humaine", "etablissement": "Faculté de Médecine (FM)",
         "bourse": 100, "aide_fpp": 30, "total": 130},
        {"offre_id": "PUB-061", "nom": "Kinésithérapie", "etablissement": "Faculté des Sciences de la Santé (FSS)",
         "bourse": 20, "aide_fpp": 15, "total": 35},
    ],
}


def build_prompt(card: dict) -> str:
    lines = [
        "Crée une carte récapitulative vertical en français pour les parents d'une élève du Bac série D.",
        "Écris EXACTEMENT ces textes et ces chiffres, sans rien ajouter ni modifier :",
        f"- Moyenne au Bac : {card['moyenne_bac']} / 20",
        f"- Moyenne de classement pour Médecine : {card['moyenne_classement_medecine']} / 20 {card['formule']}",
        "- Trois filières :",
    ]
    for item in card["filieres"]:
        lines.append(
            f"  * {item['nom']} — {item['etablissement']} — Bourse {item['bourse']}, "
            f"Aide FPP {item['aide_fpp']}, Total {item['total']}"
        )
    lines.append("Style simple et lisible, texte net, accents corrects, aucune autre information.")
    return "\n".join(lines)


def render_html(card: dict) -> str:
    rows = "".join(
        f"<tr><td><b>{i['nom']}</b><br><small>{i['etablissement']}</small></td>"
        f"<td>{i['bourse']}</td><td>{i['aide_fpp']}</td><td>{i['total']}</td></tr>"
        for i in card["filieres"]
    )
    return f"""<!doctype html><html lang="fr"><meta charset="utf-8"><body style="font-family:Arial;width:1024px;margin:0;padding:48px;box-sizing:border-box">
<h1>Carte pour les parents — Bac série D</h1>
<p style="font-size:32px">Moyenne au Bac : <b>{card['moyenne_bac']} / 20</b></p>
<p style="font-size:32px">Moyenne de classement pour Médecine : <b>{card['moyenne_classement_medecine']} / 20</b><br>
<small>{card['formule']}</small></p>
<table style="font-size:26px;border-collapse:collapse;width:100%" border="1" cellpadding="12">
<tr><th>Filière</th><th>Bourse</th><th>Aide FPP</th><th>Total</th></tr>{rows}</table></body></html>"""


def render_with_code(card: dict) -> bool:
    browser = next((path for path in BROWSER_CANDIDATES if path.exists()), None)
    if browser is None:
        print("no local Chrome/Edge found: code render skipped")
        return False
    html_path = OUT_DIR / "code_render.html"
    html_path.write_text(render_html(card), encoding="utf-8")
    subprocess.run(
        [str(browser), "--headless", "--disable-gpu", "--hide-scrollbars", "--window-size=1024,900",
         f"--screenshot={OUT_DIR / 'code_render.png'}", html_path.as_uri()],
        check=True, capture_output=True, timeout=60,
    )
    return True


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = get_client()
    prompt = build_prompt(CARD)
    (OUT_DIR / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    runs = []
    for run in range(1, RUNS + 1):
        response = client.images.generate(
            model=MODEL, prompt=prompt, n=1, size=SIZE, output_format=OUTPUT_FORMAT,
        )
        (OUT_DIR / f"run{run}.png").write_bytes(base64.b64decode(response.data[0].b64_json))
        usage = response.usage.model_dump() if getattr(response, "usage", None) else {}
        runs.append({"run": run, "usage": usage})
        print(f"run {run}: saved run{run}.png usage={usage}")
    (OUT_DIR / "usage.json").write_text(
        json.dumps({"model": MODEL, "size": SIZE, "runs": runs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("code render:", render_with_code(CARD))


if __name__ == "__main__":
    main()
