"""Format the verified report for the student (E4.2, issue #27).

Deterministic: no model call, no network. The input is the draft report
JSON (proofs `grade`, `transcript`, `filiere`, `calc`) plus the verifier
context {"serie", "grades", "transcript"}. Every rendered line comes from a
verified claim or from the guide rows its filiere proofs point to.

Verified path (`refused_claims` is None): `verify_report` must return no
problem, otherwise ValueError is raised and nothing is rendered (FR-8).

Unverified path (loop stopped after 3 refusals, #26): `refused_claims`
are the claims of the last draft the verifier refused (loop contract:
matched by `claim_id`, None ignored). Only the verified claims are
presented; each refused claim is listed under "Ce que je n'ai pas pu
vérifier" by its `claim_id` and proof types, never with its values and
never as a fact. A problem on a claim not declared refused also raises.

Sections (docs/prd.md sections 3.3 and 3.4): accessibilité,
correspondance, quotas du guide, moyenne de classement (formula and
provenance), 3 choix pour apresmonbac.bj (at least one Faculte
classique, with the allocation and official-site reminders), and
"Ce que je n'ai pas pu vérifier". At most 5 offers; every offer shows
its Offre_ID and its guide page; with no verified offer the report says
so instead of recommending (FR-9). The text never promises admission
and never names a place: those words fail the report instead of
reaching the student.
"""

from src.domain.guide import (
    NOT_PUBLISHED,
    OK_STATUS,
    load_faculte_classique_by_id,
    load_offer_rows,
    load_pages_by_id,
)
from src.tools.compute_ranking_average import COEFFICIENT_SOURCE, FORMULA
from src.tools.verify_report import verify_report

MAX_OFFERS = 5  # docs/prd.md section 3.2: the report shows at most 5 offers
CONCOURS_NOTE = "les notes du Bac ne suffisent pas"  # docs/prd.md section 3.1
ALLOCATION_REMINDER = "tout changement de filière fait perdre l'allocation"
OFFICIAL_SITE_REMINDER = "apresmonbac.bj est le seul site officiel"
NO_OFFER_MESSAGE = "Aucune offre vérifiée pour ce profil ; aucune recommandation."

# Admission promises never reach the student: "admis" also covers
# "admission". "chances" is plural on purpose so "changement" stays
# allowed. Places are never added by the templates; the guide names in
# Etablissement are quoted as published.
_FORBIDDEN_SUBSTRINGS = (
    "seras admis",
    "serez admis",
    "seras admise",
    "serez admise",
    "admis",
    "admission",
    "chances",
    "probabilité",
    "probabilite",
)


def build_report(report: dict, context: dict,
                 refused_claims: list | None = None) -> str:
    """Render the verified report text; raise when a proof is missing.

    `refused_claims` is the loop `unverified` contract (#26): the refused
    claims of the last draft, as dicts with `claim_id` (plain ids are
    accepted too). None means the fully verified path.
    """
    problems = verify_report(report, context)
    if refused_claims is None:
        if problems:
            raise ValueError(_refusal_summary(problems))
        verified = _report_claims(report)
        refused_ids: set[str] = set()
    else:
        refused_ids = _refused_ids(refused_claims)
        _raise_on_undeclared(problems, refused_ids)
        verified = [claim for claim in _report_claims(report)
                    if claim.get("claim_id") not in refused_ids]
    for claim in verified:
        text_value = claim.get("text") if isinstance(claim, dict) else None
        if isinstance(text_value, str) and _contains_forbidden(text_value):
            raise ValueError(
                f"report promises admission: {claim.get('claim_id')!r}")
    by_type = _problems_by_claim(problems)
    text = _render(verified, context, refused_ids, by_type)
    _assert_no_forbidden_admission(text)
    return text


def _report_claims(report: object) -> list[dict]:
    if not isinstance(report, dict) or not isinstance(report.get("claims"), list):
        raise ValueError("report has no usable claims: asking, not guessing")
    return report["claims"]


def _refused_ids(refused_claims: list) -> set[str]:
    if not isinstance(refused_claims, list):
        raise ValueError("refused_claims must be a list of claims or ids")
    ids = set()
    for entry in refused_claims:
        if isinstance(entry, dict):
            claim_id = entry.get("claim_id")
        else:
            claim_id = entry
        if isinstance(claim_id, str) and claim_id.strip():
            ids.add(claim_id)
    return ids


def _raise_on_undeclared(problems: list, refused_ids: set[str]) -> None:
    for problem in problems:
        claim_id = problem.get("claim_id") if isinstance(problem, dict) else None
        if not isinstance(claim_id, str) or claim_id not in refused_ids:
            raise ValueError(_refusal_summary(problems))


def _refusal_summary(problems: list) -> str:
    parts = []
    for problem in problems:
        if not isinstance(problem, dict):
            continue
        parts.append(f"{problem.get('claim_id')}:{problem.get('type')}")
    detail = ", ".join(parts) if parts else "unverified report"
    return f"unverified report, {len(problems)} problem(s): {detail}"


def _problems_by_claim(problems: list) -> dict[str, list[str]]:
    by_claim: dict[str, list[str]] = {}
    for problem in problems:
        if not isinstance(problem, dict):
            continue
        claim_id = problem.get("claim_id")
        if isinstance(claim_id, str) and claim_id:
            by_claim.setdefault(claim_id, []).append(str(problem.get("type")))
    return by_claim


def _render(verified: list[dict], context: object,
            refused_ids: set[str], by_type: dict[str, list[str]]) -> str:
    serie = _context_serie(context)
    rows = {row["Offre_ID"]: row for row in load_offer_rows()}
    pages = load_pages_by_id()
    faculte = load_faculte_classique_by_id()
    offre_ids = _verified_offre_ids(verified, rows, pages)
    sections = [
        f"PathProof — rapport vérifié\nSérie : {serie}",
        _accessibility_section(verified, offre_ids, rows, serie),
        _correspondance_section(verified, offre_ids, rows),
        _quotas_section(offre_ids, rows),
        _average_section(verified, offre_ids, rows, serie),
        _choices_section(offre_ids, rows, faculte),
        _unverified_section(verified, refused_ids, by_type, offre_ids, rows),
    ]
    return "\n\n".join(sections)


def _context_serie(context: object) -> str:
    if isinstance(context, dict) and isinstance(context.get("serie"), str):
        serie = context["serie"].strip()
        if serie:
            return serie
    raise ValueError("context serie is missing: asking, not guessing")


def _verified_offre_ids(verified: list[dict], rows: dict, pages: dict) -> list[str]:
    offre_ids: list[str] = []
    for claim in verified:
        if not isinstance(claim, dict):
            continue
        for proof in claim.get("proofs", []):
            if not isinstance(proof, dict) or proof.get("type") != "filiere":
                continue
            offre_id = proof.get("offre_id")
            if not isinstance(offre_id, str) or not offre_id.strip():
                raise ValueError("offre sans Offre_ID: asking, not guessing")
            if offre_id not in offre_ids:
                offre_ids.append(offre_id)
    if len(offre_ids) > MAX_OFFERS:
        raise ValueError(f"au plus {MAX_OFFERS} offres, {len(offre_ids)} vérifiées")
    for offre_id in offre_ids:
        row = rows.get(offre_id)
        if row is None or row.get("Statut_qualité") != OK_STATUS:
            raise ValueError(f"offre {offre_id} sans ligne {OK_STATUS}: asking, not guessing")
        if offre_id not in pages:
            raise ValueError(f"offre {offre_id} sans page: asking, not guessing")
    return offre_ids


def _accessibility_section(verified: list[dict], offre_ids: list[str],
                           rows: dict, serie: str) -> str:
    lines = ["## Accessibilité"]
    if not offre_ids:
        return "\n".join([*lines, NO_OFFER_MESSAGE])
    for offre_id in offre_ids:
        row = rows[offre_id]
        lines.append(
            f"- {row.get('Filière', '')} ({row.get('Établissement', '')}) — "
            f"{offre_id}, page {load_pages_by_id().get(offre_id)} du guide officiel — "
            f"série {serie} dans Bac_recommandé ({row.get('Bac_recommandé', '')}) — "
            f"Mode d'entrée : {row.get('Mode_entrée', '')}")
    return "\n".join(lines)


def _correspondance_section(verified: list[dict], offre_ids: list[str], rows: dict) -> str:
    lines = ["## Correspondance"]
    quotes = []
    for claim in verified:
        if not isinstance(claim, dict):
            continue
        for proof in claim.get("proofs", []):
            if isinstance(proof, dict) and proof.get("type") == "transcript":
                quote = proof.get("quote")
                if isinstance(quote, str) and quote.strip() and quote not in quotes:
                    quotes.append(quote)
    if quotes:
        for quote in quotes:
            lines.append(f"- Tu as dit : « {quote} ».")
    for offre_id in offre_ids:
        row = rows[offre_id]
        lines.append(f"- {row.get('Filière', '')} ({offre_id}) : "
                     f"Débouchés « {row.get('Débouchés_Métiers', '')} ».")
    if len(lines) == 1:
        lines.append("Aucun rapprochement vérifié à afficher.")
    return "\n".join(lines)


def _quotas_section(offre_ids: list[str], rows: dict) -> str:
    lines = ["## Quotas du guide"]
    if not offre_ids:
        return "\n".join([*lines, "Sans offre vérifiée, aucun quota à afficher."])
    for offre_id in offre_ids:
        row = rows[offre_id]
        bourse = (row.get("Bourse") or "").strip()
        aide = (row.get("Aide_FPP") or "").strip()
        page = load_pages_by_id().get(offre_id)
        if bourse == NOT_PUBLISHED or aide == NOT_PUBLISHED:
            lines.append(f"- {row.get('Filière', '')} ({offre_id}) : "
                         f"le guide ne publie pas les quotas (Bourse, Aide_FPP), "
                         f"page {page}.")
        else:
            lines.append(f"- {row.get('Filière', '')} ({offre_id}) : "
                         f"{bourse} bourses et {aide} aides FPP prévues "
                         f"(guide, page {page}).")
    return "\n".join(lines)


def _average_section(verified: list[dict], offre_ids: list[str],
                     rows: dict, serie: str) -> str:
    lines = ["## Moyenne de classement",
             f"Formule : {FORMULA} (guide, page 8). "
             f"Coefficients : {COEFFICIENT_SOURCE}, série {serie}."]
    if not offre_ids:
        return "\n".join([*lines, "Sans offre vérifiée, aucune moyenne à afficher."])
    calc_by_offre = _calc_by_offre(verified)
    for offre_id in offre_ids:
        row = rows[offre_id]
        calc = calc_by_offre.get(offre_id)
        if calc is None:
            if row.get("Mode_entrée") == "Concours":
                lines.append(f"- {row.get('Filière', '')} ({offre_id}) : "
                             f"Concours : {CONCOURS_NOTE}, par épreuve séparée.")
            else:
                lines.append(f"- {row.get('Filière', '')} ({offre_id}) : "
                             f"moyenne non calculée pour cette offre.")
            continue
        detail = ", ".join(f"{entry['matiere']} {_format_number(entry['note'])} "
                            f"× {entry['coefficient']}"
                            for entry in calc["inputs"])
        lines.append(f"- {row.get('Filière', '')} ({offre_id}) : "
                     f"{detail} : {_format_number(calc['result'])} / 20.")
    return "\n".join(lines)


def _calc_by_offre(verified: list[dict]) -> dict[str, dict]:
    """First verified calc proof of each claim carrying a filiere proof."""
    calc_by_offre: dict[str, dict] = {}
    for claim in verified:
        if not isinstance(claim, dict):
            continue
        proofs = claim.get("proofs", [])
        if not isinstance(proofs, list):
            continue
        filiere_ids = [proof.get("offre_id") for proof in proofs
                       if isinstance(proof, dict) and proof.get("type") == "filiere"
                       and isinstance(proof.get("offre_id"), str)]
        calcs = [proof for proof in proofs
                 if isinstance(proof, dict) and proof.get("type") == "calc"]
        for offre_id in filiere_ids:
            if offre_id not in calc_by_offre and calcs:
                calc_by_offre[offre_id] = calcs[0]
    return calc_by_offre


def _choices_section(offre_ids: list[str], rows: dict, faculte: dict) -> str:
    lines = ["## 3 choix pour apresmonbac.bj"]
    if not offre_ids:
        lines.append(NO_OFFER_MESSAGE)
    else:
        ranked = sorted(offre_ids,
                        key=lambda oid: (faculte.get(oid) != "oui", oid))
        for rank, offre_id in enumerate(ranked[:3], start=1):
            row = rows[offre_id]
            classique = faculte.get(offre_id, "non")
            lines.append(f"{rank}. {row.get('Filière', '')} "
                         f"({row.get('Établissement', '')}) — {offre_id}, "
                         f"page {load_pages_by_id().get(offre_id)} "
                         f"(Faculté classique : {classique})")
    lines.append(f"Rappel : {ALLOCATION_REMINDER}.")
    lines.append(f"Rappel : {OFFICIAL_SITE_REMINDER}.")
    lines.append("Tu restes libre : l'agent explique, il ne choisit pas à ta place.")
    return "\n".join(lines)


def _unverified_section(verified: list[dict], refused_ids: set[str],
                        by_type: dict[str, list[str]],
                        offre_ids: list[str], rows: dict) -> str:
    lines = ["## Ce que je n'ai pas pu vérifier"]
    for claim_id in sorted(refused_ids):
        kinds = ", ".join(by_type.get(claim_id, ["preuve"]))
        lines.append(f"- {claim_id} : affirmation non vérifiée, non retenue "
                     f"(preuve {kinds}).")
    for offre_id in offre_ids:
        row = rows[offre_id]
        if (row.get("Bourse") or "").strip() == NOT_PUBLISHED \
                or (row.get("Aide_FPP") or "").strip() == NOT_PUBLISHED:
            lines.append(f"- {offre_id} : quotas non publiés par le guide "
                         f"(Bourse, Aide_FPP).")
    if len(lines) == 1:
        lines.append("Toutes les affirmations ci-dessus sont vérifiées.")
    return "\n".join(lines)


def _format_number(value: object) -> str:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError("calc result is not a number: asking, not guessing")
    text = str(number).replace(".", ",")
    return text.rstrip("0").rstrip(",") if "," in text else text


def _assert_no_forbidden_admission(text: str) -> None:
    if _contains_forbidden(text):
        for marker in _FORBIDDEN_SUBSTRINGS:
            if marker in text.casefold():
                raise ValueError(f"report promises admission or places: {marker!r}")


def _contains_forbidden(text: str) -> bool:
    folded = text.casefold()
    return any(marker in folded for marker in _FORBIDDEN_SUBSTRINGS)
