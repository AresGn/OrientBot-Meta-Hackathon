import json
from pathlib import Path

from src.clients.meta_client import get_client
from src.clients.vision import MEDIA_TYPES, request_grade_sheet
from src.domain.coefficients import SUPPORTED_SERIES
from src.domain.subjects import UnknownSubjectError, normalize_subject

MIN_GRADE = 0  # grade scale of the Bac
MAX_GRADE = 20
# Printed on the sheets but not a ranking subject (src/domain/coefficients.py NON_RANKING_SUBJECTS).
EPS_SPELLINGS = ("eps", "education physique et sportive", "éducation physique et sportive")


class GradeSheetError(ValueError):
    """The model answer is not the expected JSON; the caller asks the student instead of guessing."""


def read_grade_sheet(image_path: str, client=None) -> dict:
    """Read a grade sheet photo into {"serie", "matieres": [{matiere, note, lisible, flags}],
    "moyenne_affichee", "flags"}.

    `moyenne_affichee` is the average printed on the sheet, copied and never computed (FR-5
    compares it with the declared one).

    An unreadable grade is `note: None, lisible: False`. A grade outside 0-20 or an unknown
    subject is kept as read and carries a flag (FR-3):
    nothing is corrected or defaulted here.
    """
    path = Path(image_path)
    if not path.is_file():
        raise GradeSheetError(f"image not found: {image_path}")
    if path.suffix.lower() not in MEDIA_TYPES:
        raise GradeSheetError(f"unsupported image type: {path.suffix!r} (use .jpg, .jpeg or .png)")
    raw, finish_reason = request_grade_sheet(client or get_client(), path)
    sheet = _parse_sheet(raw, finish_reason)
    serie = sheet.get("serie")
    serie = serie.strip().upper() if isinstance(serie, str) else None
    return {
        "serie": serie,
        "matieres": [_build_entry(row, serie) for row in sheet["matieres"]],
        "moyenne_affichee": sheet.get("moyenne_affichee"),
        "flags": _average_flags(sheet.get("moyenne_affichee")),
    }


def _parse_sheet(raw: str, finish_reason: str) -> dict:
    if not raw.strip() and finish_reason == "length":
        raise GradeSheetError("empty answer, finish_reason=length: max_tokens too low")
    try:
        sheet = json.loads(raw)
    except json.JSONDecodeError as error:
        if finish_reason == "length":
            raise GradeSheetError("answer cut off, finish_reason=length: max_tokens too low") from error
        raise GradeSheetError(f"model answer is not valid JSON: {error}") from error
    if not isinstance(sheet, dict) or not isinstance(sheet.get("matieres"), list):
        raise GradeSheetError("schema: 'matieres' list is missing")
    _check_number_or_null(sheet.get("moyenne_affichee"), "moyenne_affichee")
    for row in sheet["matieres"]:
        _check_row_schema(row)
    return sheet


def _check_row_schema(row: object) -> None:
    if not isinstance(row, dict) or not isinstance(row.get("matiere"), str):
        raise GradeSheetError("schema: each row needs a text 'matiere'")
    _check_number_or_null(row.get("note"), f"note for {row['matiere']!r}")
    if not isinstance(row.get("lisible"), bool):
        raise GradeSheetError(f"schema: 'lisible' must be a boolean for {row['matiere']!r}")


def _check_number_or_null(value: object, label: str) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
        raise GradeSheetError(f"schema: '{label}' must be a number or null")


def _average_flags(average: float | None) -> list[str]:
    if average is not None and not MIN_GRADE <= average <= MAX_GRADE:
        return ["moyenne_hors_plage"]
    return []


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
    return subject, flags
