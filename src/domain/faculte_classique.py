"""The faculte_classique column rule (E3.4, issue #23).

Page 9 of the guide strongly recommends choosing at least one program in
a "Faculté classique" among the three platform choices.
scripts/make_faculte_classique.py builds data/faculte_classique.csv
(Statut_qualité = OK rows only) from the rule below plus the
hand-reviewed exceptions; build_report (E4.2) reads the file to apply
the consigne. Pure data logic: no network, no SDK.
"""

import unicodedata

FACULTE_PREFIX = "Faculté"  # docs/prd.md section 6, point 5: the name starts with "Faculté"

# Offre_ID -> CSV label seen at review time. The PDF shows INSTI (an
# institut, not a faculte) on pages 57, 59 and 58 while the CSV still
# carries the quarantined FAST/Natitingou label (E3.2); E3.5 repairs it.
# Keyed on (id, label): the override applies only while the label is
# unchanged, so a repaired label is never masked (PR #69 review).
REVIEWED_EXCEPTIONS = {
    "PUB-186": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
    "PUB-187": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
    "PUB-188": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
}


def _fold(text: str) -> str:
    """Lowercase without accents (same folding as subjects._to_key)."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def is_faculte_label(etablissement: str) -> bool:
    """True when the label starts with "Faculté", ignoring case, accents and surrounding spaces, so an OCR variant never yields a silent non (PR #69 review)."""
    return _fold(etablissement.strip()).startswith(_fold(FACULTE_PREFIX))


def build_faculte_column(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Return ([{Offre_ID, faculte_classique}], [warnings]) for OK offer rows, in order.

    Warnings name the exceptions whose label was repaired and now agrees
    with the rule: drop them from REVIEWED_EXCEPTIONS. A repaired label
    that contradicts the review raises ValueError: the review no longer
    applies and a human must decide.
    """
    column = []
    warnings = []
    for row in rows:
        value, warning = _resolve(row)
        if warning is not None:
            warnings.append(warning)
        column.append({"Offre_ID": row["Offre_ID"], "faculte_classique": value})
    return column, warnings


def _resolve(row: dict) -> tuple[str, str | None]:
    offre_id = row["Offre_ID"]
    rule_value = "oui" if is_faculte_label(row["Établissement"]) else "non"
    if offre_id not in REVIEWED_EXCEPTIONS:
        return rule_value, None
    expected = REVIEWED_EXCEPTIONS[offre_id]
    if row["Établissement"] == expected:
        return "non", None  # reviewed truth: the PDF shows INSTI, not a faculte
    if rule_value == "non":
        return rule_value, (f"{offre_id}: label repaired, exception redundant, "
                            f"remove it (was {expected!r}, now {row['Établissement']!r})")
    raise ValueError(f"{offre_id}: label changed ({expected!r} -> "
                     f"{row['Établissement']!r}) and the rule now says {rule_value!r}; "
                     f"the INSTI review no longer applies, needs a human")
