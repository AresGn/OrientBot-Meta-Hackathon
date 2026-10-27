import json
from pathlib import Path

from src.domain.subjects import normalize_subject

COEFFICIENTS_PATH = Path(__file__).resolve().parents[2] / "data" / "coefficients_bac_benin.json"
SUPPORTED_SERIES = ("C", "D")  # docs/prd.md: only series C and D are in scope
RANKING_GROUP = 1  # group 2 is the oral retake, never used for ranking
NON_RANKING_SUBJECTS = ("EPS",)  # counted in the official total but not a ranking subject


class UnknownSerieError(ValueError):
    """Raised for a serie with no coefficients in scope."""


def load_coefficients(serie: str) -> dict[str, int]:
    """Return {canonical subject: coefficient} for the group-1 ranking subjects of a serie."""
    if serie not in SUPPORTED_SERIES:
        raise UnknownSerieError(f"unsupported serie: {serie!r}")
    with COEFFICIENTS_PATH.open(encoding="utf-8") as f:
        entries = next(s for s in json.load(f)["series"] if s["serie"] == serie)["matieres"]
    return {
        normalize_subject(e["matiere"]): e["coefficient"]
        for e in entries
        if e["groupe"] == RANKING_GROUP and e["matiere"] not in NON_RANKING_SUBJECTS
    }
