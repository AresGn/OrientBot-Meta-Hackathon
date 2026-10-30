"""The faculte_classique column (E3.4, issue #23).

Page 9 of the guide strongly recommends choosing at least one program in
a "Faculté classique" among the three platform choices; build_report
(E4.2) applies that consigne from data/faculte_classique.csv, which
covers the recommendable offers only (Statut_qualité = OK with an
established page). Rule and reviewed exceptions in
src/domain/faculte_classique.py, file written by
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
from src.domain.guide import FACULTE_PATH, OK_STATUS, load_offer_rows, load_pages_by_id

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_faculte_classique.py"


def _load_column() -> dict[str, str]:
    with FACULTE_PATH.open(newline="", encoding="utf-8-sig") as stream:
        return {row["Offre_ID"]: row["faculte_classique"]
                for row in csv.DictReader(stream) if row.get("Offre_ID")}


COLUMN_BY_ID = _load_column()  # the committed file, read once for every test

# Known oui offers, one per faculty kind: health (FSS), medicine (FM),
# sciences (FAST, C only), Natitingou (FAST/Natitingou, PDF-checked).
KNOWN_OUI = ("PUB-062", "PUB-078", "PUB-133", "PUB-184")

# Known non offers: a research centre (PUB-001), the "Facultaire" trap
# (PUB-002 CIFRED, a centre whose name contains but never starts with
# the word "Faculté"), a cooperative UFR (PUB-211), a shifted filiere
# label (PUB-216) and an interstate school (PUB-220 EAMAU).
KNOWN_NON = ("PUB-001", "PUB-002", "PUB-211", "PUB-216", "PUB-220")

# Restored in E3.5 (issue #24): labels repaired and pages back
# (FLASH-Adjarra page 23, FLLAC page 24, FLASH page 53), so these three
# faculte offers are in the file again, marked oui by the rule.
QUARANTINED_FACULTE = ("PUB-045", "PUB-048", "PUB-142")

LABEL_CASES = [
    ("Faculté de Médecine (FM)", True),
    ("Faculté", True),
    ("  Faculté des Sciences Techniques (FAST)", True),  # leading space
    ("FACULTÉ DES SCIENCES (F)", True),  # case
    ("Faculte de Droit (FD)", True),  # OCR lost the accent
    ("Facultés des Sciences (FS)", False),  # word end required
    ("Facultaire de Formation (FF)", False),
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


def test_column_covers_exactly_the_recommendable_offers():
    ok_ids = {row["Offre_ID"] for row in load_ok_offer_rows()}
    assert set(COLUMN_BY_ID) == ok_ids & set(load_pages_by_id())


def test_known_faculte_offers_are_oui():
    assert len(KNOWN_OUI) >= 3  # issue #23: at least 3 known offers
    for offre_id in KNOWN_OUI:
        assert COLUMN_BY_ID[offre_id] == "oui", offre_id


def test_known_non_faculte_offers_are_non():
    for offre_id in KNOWN_NON:
        assert COLUMN_BY_ID[offre_id] == "non", offre_id


def test_restored_faculte_offers_are_included_as_oui():
    for offre_id in QUARANTINED_FACULTE:
        assert COLUMN_BY_ID[offre_id] == "oui", offre_id


def test_restored_insti_offers_are_included_as_non():
    # PUB-186/187/188: INSTI label repaired in E3.5, pages 57/59/58 back,
    # so the rule marks them non without any exception left.
    assert REVIEWED_EXCEPTIONS == {}
    for offre_id in ("PUB-186", "PUB-187", "PUB-188"):
        assert COLUMN_BY_ID[offre_id] == "non", offre_id


def test_non_exception_rows_follow_the_rule():
    offers = {row["Offre_ID"]: row for row in load_offer_rows()}
    for offre_id, value in COLUMN_BY_ID.items():
        if offre_id in REVIEWED_EXCEPTIONS:
            assert value == "non", offre_id  # reviewed truth survives any filter
        else:
            expected = "oui" if is_faculte_label(offers[offre_id]["Établissement"]) else "non"
            assert value == expected, offre_id


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


def test_insti_label_is_non_by_the_rule_without_exception():
    rows = [{"Offre_ID": "PUB-186",
             "Établissement": "Institut National Supérieur de Technologie Industrielle (INSTI)"}]
    column, warnings = build_faculte_column(rows)
    assert column == [{"Offre_ID": "PUB-186", "faculte_classique": "non"}]
    assert warnings == []


def test_reviewed_exceptions_is_immutable():
    with pytest.raises(TypeError):
        REVIEWED_EXCEPTIONS["PUB-999"] = "Faculté (F)"


def test_script_output_matches_the_committed_file():
    completed = run_script()
    # No reviewed exception is left since E3.5 repaired the labels.
    assert completed.stderr == ""
    assert [(row["Offre_ID"], row["faculte_classique"])
            for row in csv.DictReader(completed.stdout.splitlines())] == list(COLUMN_BY_ID.items())
