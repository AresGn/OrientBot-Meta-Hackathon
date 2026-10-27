import json
from pathlib import Path

from src.clients.meta_client import get_client
from src.clients.vision import request_grade_sheet
from src.domain.coefficients import SUPPORTED_SERIES, load_coefficients
from src.domain.subjects import UnknownSubjectError, normalize_subject

MIN_GRADE = 0  # grade scale of the Bac
MAX_GRADE = 20
# Printed on the sheets but not a ranking subject (src/domain/coefficients.py NON_RANKING_SUBJECTS).
EPS_SPELLINGS = ("eps", "education physique et sportive", "éducation physique et sportive")


class GradeSheetError(ValueError):
    """The model answer is not the expected JSON; the caller asks the student instead of guessing."""


def read_grade_sheet(image_path: str, client=None) -> dict:
    """Read a grade sheet photo into {"serie", "matieres": [{matiere, note, lisible, flags}]}.

    An unreadable grade is `note: None, lisible: False`. A grade outside 0-20, an unknown
    subject or a subject invalid for the serie is kept as read and carries a flag (FR-3):
    nothing is corrected or defaulted here.
    """
    path = Path(image_path)
    if not path.is_file():
        raise GradeSheetError(f"image not found: {image_path}")
    raw, finish_reason = request_grade_sheet(client or get_client(), path)
    sheet = _parse_sheet(raw, finish_reason)
    serie = sheet.get("serie")
    serie = serie.strip().upper() if isinstance(serie, str) else None
    return {"serie": serie, "matieres": [_build_entry(row, serie) for row in sheet["matieres"]]}


def _parse_sheet(raw: str, finish_reason: str) -> dict:
    if not raw.strip() and finish_reason == "length":
        raise GradeSheetError("empty answer, finish_reason=length: max_tokens too low")
    try:
        sheet = json.loads(raw)
    except json.JSONDecodeError as error:
        raise GradeSheetError(f"model answer is not valid JSON: {error}") from error
    if not isinstance(sheet, dict) or not isinstance(sheet.get("matieres"), list):
        raise GradeSheetError("schema: 'matieres' list is missing")
    for row in sheet["matieres"]:
        _check_row_schema(row)
    return sheet


def _check_row_schema(row: object) -> None:
    if not isinstance(row, dict) or not isinstance(row.get("matiere"), str):
        raise GradeSheetError("schema: each row needs a text 'matiere'")
    note = row.get("note")
    if note is not None and (isinstance(note, bool) or not isinstance(note, (int, float))):
        raise GradeSheetError(f"schema: 'note' must be a number or null for {row['matiere']!r}")
    if not isinstance(row.get("lisible"), bool):
        raise GradeSheetError(f"schema: 'lisible' must be a boolean for {row['matiere']!r}")


def _build_entry(row: dict, serie: str | None) -> dict:
    note = row["note"] if row["lisible"] else None
    lisible = row["lisible"] and note is not None
    matiere, flags = _resolve_subject(row["matiere"], serie)
    if note is not None and not MIN_GRADE <= note <= MAX_GRADE:
        flags.append("note_hors_plage")
    return {"matiere": matiere, "note": note, "lisible": lisible, "flags": flags}


def _resolve_subject(printed: str, serie: str | None) -> tuple[str, list[str]]:
    if printed.strip().casefold() in EPS_SPELLINGS:
        return "EPS", []
    flags = [] if serie in SUPPORTED_SERIES else ["serie_non_prise_en_charge"]
    try:
        subject = normalize_subject(printed)
    except UnknownSubjectError:
        return printed, [*flags, "matiere_inconnue"]
    if serie in SUPPORTED_SERIES and subject not in load_coefficients(serie):
        flags.append("matiere_invalide_pour_la_serie")
    return subject, flags
