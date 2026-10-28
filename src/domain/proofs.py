"""Proof schema shared by the draft report, verify_report and the web UI.

Frozen by E1.4: after J2 this format only changes with an entry in
docs/decisions.md. Only the shape is validated here; whether a referenced
grade, quote, offer or result really exists is verify_report's job (E2.4).
"""

import math

SCHEMA_VERSION = 1  # docs/architecture.md: frozen proof schema, J2
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "grade": ("matiere", "note"),
    "transcript": ("quote",),
    "filiere": ("offre_id", "page_pdf", "champ", "valeur"),
    "calc": ("formula", "inputs", "result"),
}
PROOF_TYPES = tuple(REQUIRED_FIELDS)  # docs/prd.md section 4: grade, transcript, filiere, calc
STRUCTURE = "structure"  # problem type for shape problems, reused by verify_report (E2.4)


def validate_proof(proof: object) -> list[str]:
    """Return the structural problems of one proof; an empty list means valid."""
    if not isinstance(proof, dict):
        return ["proof must be an object"]
    proof_type = proof.get("type")
    if proof_type not in REQUIRED_FIELDS:
        return [f"unknown proof type: {proof_type!r}"]
    problems = []
    for field in REQUIRED_FIELDS[proof_type]:
        problems.extend(_check_field(proof_type, field, proof.get(field)))
    for field in proof:
        if field != "type" and field not in REQUIRED_FIELDS[proof_type]:
            problems.append(f"{proof_type}: unknown field {field!r}")
    return problems


def validate_report(report: object) -> list[dict[str, str | None]]:
    """Return the structural problems of a draft report; an empty list means valid.

    A report is {"schema_version": 1, "claims": [{"claim_id", "text", "proofs": [...]}]}
    where every claim carries a unique id and at least one proof. Each problem is
    {"claim_id", "type", "reason"} so verify_report (E2.4) reuses them as they are;
    report-level problems carry a null claim_id. Unknown keys are refused at every
    level (report, claim, proof).
    """
    if not isinstance(report, dict):
        return [_problem(None, "report must be an object")]
    if report.get("schema_version") != SCHEMA_VERSION:
        return [_problem(None, f"unsupported schema_version: {report.get('schema_version')!r} "
                               f"(want {SCHEMA_VERSION})")]
    problems = []
    for key in report:
        if key not in ("schema_version", "claims"):
            problems.append(_problem(None, f"unknown field {key!r}"))
    claims = report.get("claims")
    if not isinstance(claims, list) or not claims:
        return [*problems, _problem(None, "report has no claim")]
    seen: set[str] = set()
    for claim in claims:
        problems.extend(_validate_claim(claim, seen))
    return problems


def _problem(claim_id: str | None, reason: str) -> dict[str, str | None]:
    return {"claim_id": claim_id, "type": STRUCTURE, "reason": reason}


def _validate_claim(claim: object, seen: set[str]) -> list[dict[str, str | None]]:
    if not isinstance(claim, dict):
        return [_problem(None, "claim must be an object")]
    raw_id = claim.get("claim_id")
    claim_id = raw_id if isinstance(raw_id, str) and raw_id.strip() else None
    problems = []
    for key in claim:
        if key not in ("claim_id", "text", "proofs"):
            problems.append(_problem(claim_id, f"unknown field {key!r}"))
    if raw_id is None:
        problems.append(_problem(None, "missing claim_id"))
    elif claim_id is None:
        problems.append(_problem(None, "'claim_id' must be a non-empty string"))
    elif claim_id in seen:
        problems.append(_problem(claim_id, "duplicate claim_id"))
    else:
        seen.add(claim_id)
    if not isinstance(claim.get("text"), str) or not claim["text"].strip():
        problems.append(_problem(claim_id, "missing text"))
    proofs = claim.get("proofs")
    if not isinstance(proofs, list) or not proofs:
        return [*problems, _problem(claim_id, "carries no proof")]
    for proof in proofs:
        problems.extend(_problem(claim_id, reason) for reason in validate_proof(proof))
    return problems


def _check_field(label: str, field: str, value: object) -> list[str]:
    """Check one field; label is the proof type or an inputs entry ('calc: inputs[0]')."""
    if value is None:
        return [f"{label}: missing field {field!r}"]
    if field in ("matiere", "quote", "offre_id", "formula", "champ"):
        if not isinstance(value, str) or not value.strip():
            return [f"{label}: {field!r} must be a non-empty string"]
    elif field in ("note", "result"):
        if not _is_number(value):
            return [f"{label}: {field!r} must be a finite number"]
    elif field in ("page_pdf", "coefficient"):
        if not _is_positive_int(value):
            return [f"{label}: {field!r} must be a positive integer"]
    elif field == "valeur":
        if not _is_valeur(value):
            return [f"{label}: {field!r} must be a non-empty string or a finite number"]
    elif field == "inputs":
        return _check_inputs(value)
    return []


def _check_inputs(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["calc: 'inputs' must be a non-empty list"]
    problems = []
    for index, entry in enumerate(value):
        problems.extend(_check_inputs_entry(index, entry))
    return problems


def _check_inputs_entry(index: int, entry: object) -> list[str]:
    if not isinstance(entry, dict):
        return [f"calc: inputs[{index}] must be an object"]
    # Only the fields verify_report recomputes with are required: an entry mirrors a
    # compute_ranking_average detail, which also carries provenance.
    label = f"calc: inputs[{index}]"
    problems = []
    for field in ("matiere", "note", "coefficient"):
        problems.extend(_check_field(label, field, entry.get(field)))
    return problems


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_valeur(value: object) -> bool:
    return _is_number(value) or (isinstance(value, str) and bool(value.strip()))


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1
