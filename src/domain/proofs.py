"""Proof schema shared by the draft report, verify_report and the web UI.

Frozen by E1.4: after J2 this format only changes with an entry in
docs/decisions.md. Only the shape is validated here; whether a referenced
grade, quote, offer or result really exists is verify_report's job (E2.4).
"""

SCHEMA_VERSION = 1  # docs/architecture.md: frozen proof schema, J2
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "grade": ("matiere", "note"),
    "transcript": ("quote",),
    "filiere": ("offre_id", "page_pdf"),
    "calc": ("formula", "inputs", "result"),
}
PROOF_TYPES = tuple(REQUIRED_FIELDS)  # docs/prd.md section 4: grade, transcript, filiere, calc


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
    return problems


def validate_report(report: object) -> list[str]:
    """Return the structural problems of a draft report; an empty list means valid.

    A report is {"schema_version": 1, "claims": [{"text", "proofs": [...]}]}
    where every claim carries at least one proof.
    """
    if not isinstance(report, dict):
        return ["report must be an object"]
    if report.get("schema_version") != SCHEMA_VERSION:
        return [f"unsupported schema_version: {report.get('schema_version')!r} (want {SCHEMA_VERSION})"]
    claims = report.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["report has no claim"]
    problems = []
    for index, claim in enumerate(claims):
        problems.extend(_validate_claim(claim, index))
    return problems


def _validate_claim(claim: object, index: int) -> list[str]:
    if not isinstance(claim, dict):
        return [f"claim {index}: must be an object"]
    problems = []
    if not isinstance(claim.get("text"), str) or not claim["text"].strip():
        problems.append(f"claim {index}: missing text")
    proofs = claim.get("proofs")
    if not isinstance(proofs, list) or not proofs:
        return [*problems, f"claim {index}: carries no proof"]
    for proof in proofs:
        problems.extend(f"claim {index}: {problem}" for problem in validate_proof(proof))
    return problems


def _check_field(proof_type: str, field: str, value: object) -> list[str]:
    if value is None:
        return [f"{proof_type}: missing field {field!r}"]
    if field in ("matiere", "quote", "offre_id", "formula"):
        if not isinstance(value, str) or not value.strip():
            return [f"{proof_type}: {field!r} must be a non-empty string"]
    elif field in ("note", "result"):
        if not _is_number(value):
            return [f"{proof_type}: {field!r} must be a number"]
    elif field == "page_pdf":
        if not _is_positive_int(value):
            return [f"{proof_type}: {field!r} must be a positive integer"]
    elif field == "inputs":
        if not isinstance(value, list) or not value:
            return [f"{proof_type}: {field!r} must be a non-empty list"]
    return []


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1
