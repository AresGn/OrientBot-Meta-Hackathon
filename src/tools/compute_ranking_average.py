from src.domain.coefficients import COEFFICIENTS_PATH, load_coefficients
from src.domain.subjects import UnknownSubjectError, normalize_subject

MIN_GRADE = 0  # grade scale of the Bac
MAX_GRADE = 20
FORMULA = "M = Σ(mi·ci) / Σci"  # Guide d'information 2026-2027, page 8
COEFFICIENT_SOURCE = COEFFICIENTS_PATH.name


def compute_ranking_average(serie: str, offer_subjects: list[str], grades: list[dict]) -> dict:
    """Ranking average of one offer: M = Σ(mi·ci) / Σci over the offer's subjects.

    `grades` is [{"matiere": str, "note": float | None}]. Anything missing or invalid yields
    {"status": "non calculé", "reason": ...}: no default value is ever substituted.
    """
    try:
        coefficients = load_coefficients(serie)
        details = [_subject_detail(serie, raw, coefficients, grades) for raw in offer_subjects]
    except (ValueError, KeyError) as error:
        return _not_computed(str(error.args[0]))
    if not details:
        return _not_computed("no subject for this offer")
    total_coefficients = sum(d["coefficient"] for d in details)
    total_points = sum(d["note"] * d["coefficient"] for d in details)
    return {
        "status": "calculé",
        "moyenne": total_points / total_coefficients,
        "formule": FORMULA,
        "somme_coefficients": total_coefficients,
        "details": details,
    }


def _subject_detail(serie: str, raw_subject: str, coefficients: dict[str, int], grades: list[dict]) -> dict:
    subject = normalize_subject(raw_subject)
    if subject not in coefficients:
        raise KeyError(f"coefficient manquant: {subject} en série {serie}")
    return {
        "matiere": subject,
        "note": _find_grade(subject, grades),
        "coefficient": coefficients[subject],
        "provenance": {"fichier": COEFFICIENT_SOURCE, "serie": serie, "matiere": subject},
    }


def _find_grade(subject: str, grades: list[dict]) -> float:
    notes = []
    for entry in grades:
        try:
            if normalize_subject(entry["matiere"]) == subject:
                notes.append(entry.get("note"))
        except UnknownSubjectError:
            continue  # a sheet line for another subject is not this offer's concern
    if not notes:
        raise KeyError(f"note manquante: {subject}")
    if len(set(notes)) > 1:
        raise ValueError(f"notes contradictoires: {subject}")
    note = notes[0]
    if isinstance(note, bool) or not isinstance(note, (int, float)):
        raise ValueError(f"note illisible: {subject}")
    if not MIN_GRADE <= note <= MAX_GRADE:
        raise ValueError(f"note hors de {MIN_GRADE}-{MAX_GRADE}: {subject} = {note}")
    return note


def _not_computed(reason: str) -> dict:
    return {"status": "non calculé", "reason": reason}
