"""Vision call for grade sheets; the only place that knows the model parameters for it."""
import base64
from pathlib import Path

VISION_MODEL = "muse-spark-1.3"
VISION_MAX_TOKENS = 8000  # docs/decisions.md E0.4: reasoning tokens count, 8000 suffices (finish_reason = stop)
MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}  # only JPEG is tested (E0.4)

GRADE_SHEET_INSTRUCTION = """Tu lis un relevé de notes du Bac. Recopie uniquement ce qui est imprimé, sans rien calculer.
Réponds avec un seul objet JSON, sans texte autour, sans bloc de code, exactement de cette forme :
{"serie": "<lettre>", "matieres": [{"matiere": "<nom exact imprimé>", "note": <nombre ou null>, "coeff": <entier ou null>, "lisible": <true|false>}], "moyenne_affichee": <nombre ou null>}
Règles : une entrée par ligne du tableau, EPS comprise, sans les lignes de total ; virgule décimale convertie en point ;
si une valeur ne se lit pas, mets null et "lisible": false. Ne devine jamais."""


def request_grade_sheet(client, image_path: Path) -> tuple[str, str]:
    """Send the sheet photo to the model; return (raw answer text, finish_reason)."""
    media_type = MEDIA_TYPES.get(image_path.suffix.lower())
    if media_type is None:
        raise ValueError(f"unsupported image type: {image_path.suffix!r} (use .jpg, .jpeg or .png)")
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": GRADE_SHEET_INSTRUCTION},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}},
        ],
    }]
    response = client.chat.completions.create(model=VISION_MODEL, messages=messages, max_tokens=VISION_MAX_TOKENS)
    choice = response.choices[0]
    return choice.message.content or "", choice.finish_reason
