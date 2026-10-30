"""The faculte_classique column rule (E3.4, issue #23).

Page 9 of the guide strongly recommends choosing at least one program in
a "Faculté classique" among the three platform choices.
scripts/make_faculte_classique.py builds data/faculte_classique.csv
(recommendable offers only: Statut_qualité = OK with an established
page) from the rule below plus the hand-reviewed exceptions;
build_report (E4.2) reads the file to apply the consigne. Pure data
logic: no network, no SDK.
"""

import re
import types
import unicodedata

FACULTE_PREFIX = "Faculté"  # docs/prd.md section 6, point 5: the name starts with "Faculté"

# The PDF truth behind REVIEWED_EXCEPTIONS (pages 57, 59, 58): a repaired
# label only retires an exception when it still points at INSTI.
INSTI_PREFIX = "Institut"

# Offre_ID -> CSV label seen at review time. The PDF shows INSTI (an
# institut, not a faculte) while the CSV still carries the quarantined
# FAST/Natitingou label (E3.2); E3.5 repairs the label and restores the
# page. Keyed on (id, label): the override applies only while the label
# is unchanged, so a repaired label is never masked.
REVIEWED_EXCEPTIONS = types.MappingProxyType({
    "PUB-186": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
    "PUB-187": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
    "PUB-188": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
})


def _fold(text: str) -> str:
    """Lowercase without accents (same folding as subjects._to_key)."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


# Folded FACULTE_PREFIX with a word end: "Facultés" or "Facultaire" must
# not match, a silent oui is as bad as a silent non.
_FACULTE_WORD = re.compile(_fold(FACULTE_PREFIX) + r"\b")


def is_faculte_label(etablissement: str) -> bool:
    """True when the label starts with the word "Faculté".

    Case, accents and surrounding spaces are ignored, so an OCR variant
    never yields a silent non; the word end rejects "Facultés" and
    "Facultaire", so a near miss never yields a silent oui.
    """
    return _FACULTE_WORD.match(_fold(etablissement.strip())) is not None


def build_faculte_column(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Return ([{Offre_ID, faculte_classique}], [warnings]) for OK offer rows, in order.

    Warnings name the exceptions whose label was repaired to INSTI and
    now agrees with the rule: drop them from REVIEWED_EXCEPTIONS. Any
    other changed label, or an exception id missing from the rows,
    raises ValueError: the review no longer applies and a human must
    decide.
    """
    received = {row["Offre_ID"] for row in rows}
    missing = [offre_id for offre_id in REVIEWED_EXCEPTIONS if offre_id not in received]
    if missing:
        raise ValueError(f"stale exception ids, absent from the received rows: {missing}")
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
    label = row["Établissement"]
    if label == REVIEWED_EXCEPTIONS[offre_id]:
        return "non", None  # reviewed truth: the PDF shows INSTI, not a faculte
    if rule_value == "non" and _fold(label).startswith(_fold(INSTI_PREFIX)):
        return rule_value, (f"{offre_id}: label repaired to INSTI, exception redundant, "
                            f"remove it (was {REVIEWED_EXCEPTIONS[offre_id]!r})")
    raise ValueError(f"{offre_id}: label changed ({REVIEWED_EXCEPTIONS[offre_id]!r} -> "
                     f"{label!r}); neither the quarantined label nor the reviewed "
                     f"INSTI repair, needs a human")
