"""The faculte_classique column (E3.4, issue #23).

Page 9 of the guide strongly recommends choosing at least one program in
a "Faculté classique" among the three platform choices; build_report
(E4.2) applies that consigne from data/faculte_classique.csv, which
covers the Statut_qualité = OK offers only. Rule and reviewed
exceptions in src/domain/faculte_classique.py, file written by
scripts/make_faculte_classique.py. No network, no API key.
"""

import csv
import subprocess
import sys
from pathlib import Path

import pytest

from src.domain.faculte_classique import (
    REVIEWED_EXCEPTIONS,
    build_faculte_column,
    is_faculte_label,
)
from src.domain.guide import FACULTE_PATH, OK_STATUS, load_offer_rows

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_faculte_classique.py"


def _load_column() -> dict[str, str]:
    with FACULTE_PATH.open(newline="", encoding="utf-8-sig") as stream:
        return {row["Offre_ID"]: row["faculte_classique"]
                for row in csv.DictReader(stream) if row.get("Offre_ID")}


COLUMN_BY_ID = _load_column()  # the committed file, read once for every test

# Known oui offers, one per faculty kind: health (FSS), medicine (FM),
# sciences (FAST, C only), Natitingou (FAST/Natitingou).
KNOWN_OUI = ("PUB-062", "PUB-078", "PUB-133", "PUB-184")

# Known non offers: a research centre (PUB-001), the "Facultaire" trap
# (PUB-002 CIFRED, a centre whose name contains but never starts with
# "Faculté"), a quarantined school (PUB-025 ENSTIC), a cooperative UFR
# (PUB-211) and a shifted filiere label (PUB-216).
KNOWN_NON = ("PUB-001", "PUB-002", "PUB-025", "PUB-211", "PUB-216")

# Quarantined offers (E3.2) whose true etablissement stays a faculte:
# PUB-045 -> FLASH-Adjarra (page 23), PUB-048 -> FLLAC (page 24),
# PUB-142 -> FLASH-Parakou (page 53). Still oui after the E3.5 repair.
QUARANTINED_FACULTE = ("PUB-045", "PUB-048", "PUB-142")

LABEL_CASES = [
    ("Faculté de Médecine (FM)", True),
    ("  Faculté des Sciences Techniques (FAST)", True),  # leading space
    ("FACULTÉ DES SCIENCES (F)", True),  # case
    ("Faculte de Droit (FD)", True),  # OCR lost the accent
    ("Centre Inter Facultaire de Formation (CIFRED)", False),
    ("UFR Gestion du Développement (UFR/GD)", False),
    ("", False),
]


def load_ok_offer_rows():
    return [row for row in load_offer_rows() if row["Statut_qualité"] == OK_STATUS]


def run_script():
    return subprocess.run([sys.executable, str(SCRIPT)], capture_output=True,
                          text=True, cwd=ROOT, check=True)


def test_values_are_oui_or_non():
    assert COLUMN_BY_ID
    assert set(COLUMN_BY_ID.values()) <= {"oui", "non"}


def test_column_covers_exactly_the_ok_offers():
    assert set(COLUMN_BY_ID) == {row["Offre_ID"] for row in load_ok_offer_rows()}


def test_known_faculte_offers_are_oui():
    assert len(KNOWN_OUI) >= 3  # issue #23: at least 3 known offers
    for offre_id in KNOWN_OUI:
        assert COLUMN_BY_ID[offre_id] == "oui", offre_id


def test_known_non_faculte_offers_are_non():
    for offre_id in KNOWN_NON:
        assert COLUMN_BY_ID[offre_id] == "non", offre_id


def test_reviewed_insti_offers_are_non():
    for offre_id in REVIEWED_EXCEPTIONS:
        assert COLUMN_BY_ID[offre_id] == "non", offre_id


def test_quarantined_faculte_offers_stay_oui():
    for offre_id in QUARANTINED_FACULTE:
        assert COLUMN_BY_ID[offre_id] == "oui", offre_id


def test_final_column_is_rule_plus_reviewed_exceptions():
    offers = {row["Offre_ID"]: row for row in load_ok_offer_rows()}
    rule_non = {offre_id for offre_id, row in offers.items()
                if not is_faculte_label(row["Établissement"])}
    final_non = {offre_id for offre_id, value in COLUMN_BY_ID.items()
                 if value == "non"}
    assert rule_non <= final_non  # exceptions only remove oui, never add
    assert final_non - rule_non <= set(REVIEWED_EXCEPTIONS)  # every added non is reviewed
    for offre_id in REVIEWED_EXCEPTIONS:
        assert offre_id in offers  # no stale exception id


def test_normalization_changes_no_current_label():
    # The hand review checked exact labels, written out so the test cannot
    # pass by following the code constant; any OCR variant in the data
    # must fail loudly instead of silently following the rule.
    for row in load_offer_rows():
        label = row["Établissement"]
        assert is_faculte_label(label) == label.startswith("Faculté"), row["Offre_ID"]


@pytest.mark.parametrize("label, expected", LABEL_CASES)
def test_label_variants_follow_the_rule_intent(label, expected):
    assert is_faculte_label(label) == expected


def test_exception_applies_while_label_is_quarantined():
    rows = [{"Offre_ID": "PUB-186", "Établissement": REVIEWED_EXCEPTIONS["PUB-186"]}]
    column, warnings = build_faculte_column(rows)
    assert column == [{"Offre_ID": "PUB-186", "faculte_classique": "non"}]
    assert warnings == []


def test_repaired_label_matching_rule_warns_and_follows_rule():
    rows = [{"Offre_ID": "PUB-186",
             "Établissement": "Institut National Supérieur de Technologie Industrielle (INSTI)"}]
    column, warnings = build_faculte_column(rows)
    assert column == [{"Offre_ID": "PUB-186", "faculte_classique": "non"}]
    assert len(warnings) == 1
    assert "PUB-186" in warnings[0] and "redundant" in warnings[0]


def test_repaired_label_contradicting_review_raises():
    rows = [{"Offre_ID": "PUB-186", "Établissement": "Faculté des Sciences (FS)"}]
    with pytest.raises(ValueError, match="PUB-186"):
        build_faculte_column(rows)


def test_script_output_matches_the_committed_file():
    completed = run_script()
    assert completed.stderr == ""  # every exception still diverges from the rule
    assert [(row["Offre_ID"], row["faculte_classique"])
            for row in csv.DictReader(completed.stdout.splitlines())] == list(COLUMN_BY_ID.items())
