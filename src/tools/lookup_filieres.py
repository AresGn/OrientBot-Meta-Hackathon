import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "filieres.csv"
VERIFIED = "verifie"


def lookup_filieres(serie: str | None = None, moyenne: float | None = None) -> list[dict]:
    """Return rows of data/filieres.csv with source_status == "verifie".

    Rows marked TODO are never returned. `moyenne` is accepted so the model can pass it,
    but access conditions are free text for now, so it is not used to filter yet.
    """
    with DATA.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["source_status"] == VERIFIED and r["source_url"]]
    if serie:
        rows = [r for r in rows if r["serie_bac_requise"] == serie]
    return rows
