import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "filieres.csv"


def lookup_filieres(serie: str | None = None) -> list[dict]:
    """Return rows of data/filieres.csv, excluding unverified (TODO) rows."""
    with DATA.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["source_url"] != "TODO"]
    if serie:
        rows = [r for r in rows if r["serie_bac_requise"] == serie]
    return rows
