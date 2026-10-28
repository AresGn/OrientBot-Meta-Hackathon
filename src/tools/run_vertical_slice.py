"""Deterministic vertical slice: JSON input, calculation, provisional search,
draft report with proofs, then verify_report. No model, no network, no API key.

The search is provisional (E2.5): it only keeps guide rows with
Statut_qualité = OK whose Bac_recommandé lists the serie, and only reads the
subjects of rows whose Matières cell has a single "<series> : <subjects>"
segment for that serie. E3.1/E3.5 replace it with the real per-serie parser
and the rewritten lookup_filieres.
"""

import csv
import unicodedata
from pathlib import Path

from src.domain.proofs import SCHEMA_VERSION
from src.domain.subjects import UnknownSubjectError, normalize_subject
from src.tools.compute_ranking_average import FORMULA, compute_ranking_average
from src.tools.verify_report import verify_report

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OFFERS_PATH = DATA_DIR / "offres_publiques_2026_2027.csv"  # guide rows, Statut_qualité included
PAGES_PATH = DATA_DIR / "pages_offres.csv"  # Offre_ID -> page of the official PDF
OK_STATUS = "OK"  # docs/prd.md section 3.1: only Statut_qualité = OK rows are recommended


def search_offers_provisional(serie: str) -> list[dict]:
    """Return guide rows with Statut_qualité = OK open to `serie` (provisional, E2.5)."""
    with OFFERS_PATH.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    return [row for row in rows
            if row.get("Statut_qualité") == OK_STATUS
            and serie in _split_values(row.get("Bac_recommandé", ""))]


def run_vertical_slice(fixture: dict) -> dict:
    """Run the whole deterministic path for one JSON fixture.

    `fixture` is {"serie", "grades", "transcript", "profile"}: grades as
    [{"matiere", "note", "lisible"}], profile as the extract_profile shape
    {"metier_vise": {"value", "quote"}}. Returns {"status", "report",
    "problems", "text"}; "text" is only rendered when verify_report returns
    no problem, and every line of it is one proven claim. A missing or
    incoherent fixture raises ValueError: nothing is guessed.
    """
    serie, grades, transcript, metier = _read_fixture(fixture)
    pages = _load_pages()
    kept = _calculable_offers(serie, grades, metier["value"], pages)
    if not kept:
        return {"status": "unverified", "report": None, "text": "",
                "problems": [{"claim_id": None, "type": "filiere",
                              "reason": "no calculable offer matches the profile"}]}
    report = _build_draft(serie, grades, transcript, metier, kept, pages)
    context = {"serie": serie, "grades": grades, "transcript": transcript}
    problems = verify_report(report, context)
    text = "" if problems else "\n".join(claim["text"] for claim in report["claims"])
    return {"status": "unverified" if problems else "verified",
            "report": report, "problems": problems, "text": text}


def _read_fixture(fixture: object) -> tuple[str, list, str, dict]:
    if not isinstance(fixture, dict):
        raise ValueError("fixture must be a JSON object")
    serie, grades = fixture.get("serie"), fixture.get("grades")
    transcript, profile = fixture.get("transcript"), fixture.get("profile")
    if not isinstance(serie, str) or not serie.strip():
        raise ValueError("fixture serie is missing")
    if not isinstance(grades, list) or not grades:
        raise ValueError("fixture grades are missing")
    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError("fixture transcript is missing")
    metier = profile.get("metier_vise") if isinstance(profile, dict) else None
    if not isinstance(metier, dict) or not metier.get("value") or not metier.get("quote"):
        raise ValueError("fixture profile metier_vise with value and quote is missing")
    if metier["quote"] not in transcript:
        raise ValueError("metier_vise quote is not in the transcript: asking, not guessing")
    return serie, grades, transcript, metier


def _calculable_offers(serie: str, grades: list, metier_value: str, pages: dict) -> list:
    kept = []
    for row in search_offers_provisional(serie):
        if not _matches_metier(row, metier_value) or row["Offre_ID"] not in pages:
            continue
        subjects = _offer_subjects(row, serie)
        if subjects is None:
            continue
        result = compute_ranking_average(serie, subjects, grades)
        if result.get("status") == "calculé":
            kept.append((row, result))
    return kept


def _matches_metier(row: dict, metier_value: str) -> bool:
    haystack = _folded(f"{row.get('Filière', '')} {row.get('Débouchés_Métiers', '')}")
    return _folded(metier_value) in haystack


def _offer_subjects(row: dict, serie: str) -> list[str] | None:
    raw = row.get("Matières", "")
    if raw.count(":") != 1:  # multi-segment cells are E3.1's job, not the provisional search
        return None
    prefix, rest = raw.split(":", 1)
    if serie not in _split_values(prefix):
        return None
    try:
        return [normalize_subject(name) for name in _split_values(rest)]
    except UnknownSubjectError:
        return None


def _build_draft(serie: str, grades: list, transcript: str, metier: dict,
                 kept: list, pages: dict) -> dict:
    claims = _grade_claims(kept)
    claims.append({"claim_id": "metier-vise",
                   "text": f"Tu as dit vouloir être {metier['value']} (« {metier['quote']} »).",
                   "proofs": [{"type": "transcript", "quote": metier["quote"]}]})
    for row, result in kept:
        claims.append(_offer_claim(row, result, pages[row["Offre_ID"]]))
    return {"schema_version": SCHEMA_VERSION, "claims": claims}


def _grade_claims(kept: list) -> list[dict]:
    claims, seen = [], set()
    for _row, result in kept:
        for detail in result["details"]:
            if detail["matiere"] in seen:
                continue
            seen.add(detail["matiere"])
            claims.append({
                "claim_id": f"grade-{len(claims) + 1}",
                "text": f"{detail['matiere']} : {_format_number(detail['note'])}/20 au relevé.",
                "proofs": [{"type": "grade", "matiere": detail["matiere"],
                            "note": detail["note"]}]})
    return claims


def _offer_claim(row: dict, result: dict, page: str) -> dict:
    offre_id = row["Offre_ID"]
    proofs = [{"type": "filiere", "offre_id": offre_id, "page_pdf": int(page),
               "champ": champ, "valeur": _csv_value(row[champ])}
              for champ in ("Filière", "Établissement", "Bourse")]
    proofs.append({"type": "calc", "formula": FORMULA,
                   "inputs": [{"matiere": d["matiere"], "note": d["note"],
                               "coefficient": d["coefficient"]} for d in result["details"]],
                   "result": result["moyenne_arrondie"]})
    return {"claim_id": f"offre-{offre_id.lower()}",
            "text": (f"{row['Filière']} ({row['Établissement']}) — {offre_id} : "
                     f"{row['Bourse']} bourses prévues, moyenne de classement "
                     f"{_format_number(result['moyenne_arrondie'])}."),
            "proofs": proofs}


def _load_pages() -> dict:
    with PAGES_PATH.open(newline="", encoding="utf-8-sig") as stream:
        return {row["Offre_ID"]: row["page_pdf"] for row in csv.DictReader(stream)
                if row.get("Offre_ID") and row.get("page_pdf")}


def _split_values(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def _csv_value(raw: str) -> int | str:
    return int(raw) if raw.strip().isdigit() else raw


def _format_number(value: float) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number).replace(".", ",")


def _folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))
