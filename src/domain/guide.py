"""Access to the official guide CSVs in data/ (rows and PDF pages).

Shared by verify_report and the vertical slice; lookup_filieres (E3.5) will
read the same rows. Pure file reading: no network, no SDK.
"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OFFERS_PATH = DATA_DIR / "offres_publiques_2026_2027.csv"  # guide rows, Statut_qualité included
PAGES_PATH = DATA_DIR / "pages_offres.csv"  # Offre_ID -> page of the official PDF
OK_STATUS = "OK"  # docs/prd.md section 3.1: only Statut_qualité = OK rows are recommended
PAGE_STATUSES = frozenset({"unique", "sigle", "verifie_main",
                           "page_non_etablie"})  # issue #21: finished page_statut values
PAGE_NON_ETABLIE = "page_non_etablie"  # issue #21: page not established, offer not recommendable


def load_offer_rows() -> list[dict]:
    """Return every row of the guide offers CSV, Statut_qualité included."""
    with OFFERS_PATH.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def load_pages_by_id() -> dict[str, str]:
    """Return {Offre_ID: page_pdf} for the rows of data/pages_offres.csv that carry both.

    Offers with page_statut = page_non_etablie (empty page_pdf) are absent, so
    verify_report refuses their filiere proofs and searches skip them: without
    a page, an offer is not recommendable (issue #21).
    """
    with PAGES_PATH.open(newline="", encoding="utf-8-sig") as stream:
        return {row["Offre_ID"]: row["page_pdf"] for row in csv.DictReader(stream)
                if row.get("Offre_ID") and row.get("page_pdf")}
