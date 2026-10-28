from decimal import ROUND_HALF_UP, Decimal

from src.domain.coefficients import COEFFICIENTS_PATH, load_coefficients
from src.domain.grade_scale import MAX_GRADE, MIN_GRADE, is_on_grade_scale
from src.domain.subjects import UnknownSubjectError, normalize_subject

FORMULA = "M = Σ(mi·ci) / Σci"  # Guide d'information 2026-2027, page 8
DISPLAY_DECIMALS = Decimal("0.01")  # docs/decisions.md: 2 decimals, half up
COEFFICIENT_SOURCE = COEFFICIENTS_PATH.name


def compute_ranking_average(serie: str, offer_subjects: list[str], grades: list[dict]) -> dict:
    """Ranking average of one offer: M = Σ(mi·ci) / Σci over the offer's subjects.

    `grades` is [{"matiere": str, "note": float | None}]. Anything missing or invalid yields
    {"status": "non calculé", "reason": ...}: no default value is ever substituted. An entry
    with `lisible` false counts as unreadable even if it carries a note.
    """
    try:
        coefficients = load_coefficients(serie)
        subjects = _normalize_offer_subjects(offer_subjects)
        details = [_subject_detail(serie, subject, coefficients, grades) for subject in subjects]
    except (ValueError, KeyError, TypeError) as error:
        return _not_computed(str(error.args[0]))
    if not details:
        return _not_computed("no subject for this offer")
    total_coefficients = sum(d["coefficient"] for d in details)
    total_points = sum(d["note"] * d["coefficient"] for d in details)
    return {
        "status": "calculé",
        "moyenne": total_points / total_coefficients,
        "moyenne_arrondie": _round_for_display(details),
        "formule": FORMULA,
        "somme_coefficients": total_coefficients,
        "details": details,
    }


def _normalize_offer_subjects(offer_subjects: list[str]) -> list[str]:
    subjects = [normalize_subject(raw) for raw in offer_subjects]
    for subject in subjects:
        if subjects.count(subject) > 1:
            raise ValueError(f"matière en double: {subject}")
    return subjects


def _subject_detail(serie: str, subject: str, coefficients: dict[str, int], grades: list[dict]) -> dict:
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
        if not isinstance(entry, dict) or "matiere" not in entry:
            raise ValueError("entrée de note invalide: clé matiere absente")
        try:
            if normalize_subject(entry["matiere"]) == subject:
                notes.append(entry.get("note") if entry.get("lisible", True) else None)
        except UnknownSubjectError:
            continue  # a sheet line for another subject is not this offer's concern
    if not notes:
        raise KeyError(f"note manquante: {subject}")
    if len(set(notes)) > 1:
        raise ValueError(f"notes contradictoires: {subject}")
    note = notes[0]
    if isinstance(note, bool) or not isinstance(note, (int, float)):
        raise ValueError(f"note illisible: {subject}")
    if not is_on_grade_scale(note):
        raise ValueError(f"note hors de {MIN_GRADE}-{MAX_GRADE}: {subject} = {note}")
    return note


def _not_computed(reason: str) -> dict:
    return {"status": "non calculé", "reason": reason}


def _round_for_display(details: list[dict]) -> float:
    # Decimal built from each grade's text avoids float artefacts (10.005 must give 10.01).
    points = sum(Decimal(repr(d["note"])) * d["coefficient"] for d in details)
    exact = points / sum(d["coefficient"] for d in details)
    return float(exact.quantize(DISPLAY_DECIMALS, rounding=ROUND_HALF_UP))
