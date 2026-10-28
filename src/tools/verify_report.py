"""Verify every proof of a draft report against its source, in pure code.

No model call, no network: this is the code verifier of docs/prd.md section 4.
"""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.domain.proofs import STRUCTURE, validate_report
from src.domain.subjects import UnknownSubjectError, normalize_subject
from src.tools.compute_ranking_average import FORMULA, compute_ranking_average

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OFFERS_PATH = DATA_DIR / "offres_publiques_2026_2027.csv"  # guide rows, Statut_qualité included
PAGES_PATH = DATA_DIR / "pages_offres.csv"  # Offre_ID -> page of the official PDF
OK_STATUS = "OK"  # docs/prd.md section 3.1: only Statut_qualité = OK rows are recommended


def verify_report(report: object, context: object) -> list[dict]:
    """Return the problems of a draft report; an empty list means fully proven.

    `context` is {"serie", "grades", "transcript"}: the serie and the grades as
    returned in `read_grade_sheet(...)["matieres"]` ([{"matiere", "note", "lisible"}]),
    plus the voice-note transcript. That is the only accepted context shape.
    Filiere proofs are always checked against the guide CSVs in `data/`, loaded
    once per call; the context can never replace the official guide. Each problem is
    {"claim_id", "type", "reason"}; `type` is the refused proof type (or
    `structure` for the shape problems of `validate_report`, reused as they are).

    Fail closed: a malformed report, a missing context or an exception raised by
    a check returns a problem, never an empty list. Reasons never carry the
    expected value, so the agent cannot copy the recalculated answer (a wrong
    calc is refused without its correct result).
    """
    try:
        problems = validate_report(report)
    except Exception:
        return [_problem(None, STRUCTURE, "report could not be verified")]
    if problems:
        return problems
    refused = []
    guide = _guide_for(report)
    for claim in report["claims"]:
        for proof in claim["proofs"]:
            refused.extend(_verify_proof(claim["claim_id"], proof, context, guide))
    return refused


def _problem(claim_id: str | None, proof_type: str, reason: str) -> dict:
    return {"claim_id": claim_id, "type": proof_type, "reason": reason}


def _verify_proof(claim_id: str, proof: dict, context: object, guide: object) -> list[dict]:
    proof_type = proof["type"]
    try:
        if proof_type == "filiere":
            return _verify_filiere(claim_id, proof, guide)
        check = {"grade": _verify_grade, "transcript": _verify_transcript,
                 "calc": _verify_calc}[proof_type]
        return check(claim_id, proof, context)
    except Exception:
        return [_problem(claim_id, proof_type, f"{proof_type} proof could not be verified")]


def _verify_grade(claim_id: str, proof: dict, context: object) -> list[dict]:
    subject = normalize_subject(proof["matiere"])
    notes = [entry["note"] for entry in _context_grades(context)
             if _entry_subject(entry) == subject and entry.get("lisible") is True
             and entry.get("note") is not None]
    if len(set(notes)) != 1 or not _numbers_equal(notes[0], proof["note"]):
        return [_problem(claim_id, "grade",
                         "grade proof does not match the grade read on the grade sheet")]
    return []


def _verify_transcript(claim_id: str, proof: dict, context: object) -> list[dict]:
    if not isinstance(context, dict) or not isinstance(context.get("transcript"), str):
        raise TypeError("context transcript is missing")
    if proof["quote"] not in context["transcript"]:
        return [_problem(claim_id, "transcript",
                         "transcript proof quote was not found word for word in the transcript")]
    return []


def _verify_filiere(claim_id: str, proof: dict, guide: object) -> list[dict]:
    row, page = _offer_reference(proof["offre_id"], guide)
    if row is None or row.get("Statut_qualité") != OK_STATUS:
        return [_problem(claim_id, "filiere",
                         "filiere proof does not reference an offer row with Statut_qualité = OK")]
    champ = proof["champ"]
    if champ not in row or not _values_equal(row[champ], proof["valeur"]):
        return [_problem(claim_id, "filiere",
                         "filiere proof does not match the guide row for the stated field")]
    if page is None or not _numbers_equal(page, proof["page_pdf"]):
        return [_problem(claim_id, "filiere",
                         "filiere proof does not match the PDF page of the guide row")]
    return []


def _verify_calc(claim_id: str, proof: dict, context: object) -> list[dict]:
    refused = _problem(claim_id, "calc",
                       "calc proof does not match the ranking average recomputed "
                       "from the grades and coefficients")
    if proof["formula"] != FORMULA:
        return [refused]
    result = compute_ranking_average(_context_serie(context),
                                     [entry["matiere"] for entry in proof["inputs"]],
                                     _context_grades(context))
    if result.get("status") != "calculé" or not _numbers_equal(result["moyenne_arrondie"],
                                                               proof["result"]):
        return [refused]
    if not _calc_inputs_match(proof["inputs"], result["details"]):
        return [refused]
    return []


def _calc_inputs_match(inputs: list[dict], details: list[dict]) -> bool:
    by_subject = {detail["matiere"]: detail for detail in details}
    for entry in inputs:
        detail = by_subject.get(normalize_subject(entry["matiere"]))
        if detail is None or detail["coefficient"] != entry["coefficient"]:
            return False
        if not _numbers_equal(detail["note"], entry["note"]):
            return False
    return True


def _context_grades(context: object) -> list[dict]:
    if not isinstance(context, dict):
        raise TypeError("context is missing")
    grades = context.get("grades")
    if not isinstance(grades, list) or not all(isinstance(entry, dict) for entry in grades):
        raise TypeError("context grades are missing")
    return grades


def _context_serie(context: object) -> str:
    if not isinstance(context, dict):
        raise TypeError("context is missing")
    serie = context.get("serie")
    if not isinstance(serie, str) or not serie.strip():
        raise TypeError("context serie is missing")
    return serie


def _entry_subject(entry: dict) -> str | None:
    try:
        return normalize_subject(entry["matiere"])
    except UnknownSubjectError:
        return None


def _guide_for(report: dict) -> object:
    """Load the official guide once per call, only if a filiere proof needs it.

    Returns (rows, pages) or the exception the load raised, so a filiere check
    turns it into its own problem instead of letting verify_report crash.
    """
    has_filiere = any(proof.get("type") == "filiere"
                      for claim in report["claims"] for proof in claim["proofs"])
    if not has_filiere:
        return None
    try:
        with OFFERS_PATH.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        with PAGES_PATH.open(newline="", encoding="utf-8-sig") as stream:
            return rows, _pages_by_id(list(csv.DictReader(stream)))
    except Exception as error:
        return error


def _offer_reference(offre_id: str, guide: object) -> tuple[dict | None, object]:
    if isinstance(guide, Exception):
        raise guide
    rows, pages = guide
    row = next((candidate for candidate in rows if candidate.get("Offre_ID") == offre_id), None)
    return row, pages.get(offre_id)


def _pages_by_id(pages: list[dict]) -> dict:
    return {row["Offre_ID"]: row["page_pdf"] for row in pages
            if isinstance(row, dict) and row.get("Offre_ID") is not None}


def _numbers_equal(left: object, right: object) -> bool:
    left_number, right_number = _as_number(left), _as_number(right)
    return left_number is not None and left_number == right_number


def _values_equal(csv_value: object, proof_value: object) -> bool:
    csv_number, proof_number = _as_number(csv_value), _as_number(proof_value)
    if csv_number is not None and proof_number is not None:
        return csv_number == proof_number
    return str(csv_value).strip() == str(proof_value).strip()


def _as_number(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return Decimal(repr(value))
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return None
    return None
