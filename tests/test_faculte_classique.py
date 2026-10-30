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

# Quarantined offers (E3.2) excluded from the file until E3.5 restores
# their page; the true etablissement stays a faculte for these three
# (FLASH-Adjarra page 23, FLLAC page 24, FLASH-Parakou page 53).
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

UNRECOGNIZED_LABELS = ["", "École de Commerce (EC)"]


def load_ok_offer_rows():
    return [row for row in load_offer_rows() if row["Statut_qualité"] == OK_STATUS]


def exception_rows(overrides=None):
    """One row per reviewed exception, labels replaced by overrides."""
    overrides = overrides or {}
    return [{"Offre_ID": offre_id,
             "Établissement": overrides.get(offre_id, REVIEWED_EXCEPTIONS[offre_id])}
            for offre_id in REVIEWED_EXCEPTIONS]


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


def test_quarantined_faculte_offers_are_excluded():
    for offre_id in QUARANTINED_FACULTE:
        assert offre_id not in COLUMN_BY_ID, offre_id


def test_reviewed_insti_offers_are_excluded():
    for offre_id in REVIEWED_EXCEPTIONS:
        assert offre_id not in COLUMN_BY_ID, offre_id


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


def test_exceptions_apply_while_labels_are_quarantined():
    column, warnings = build_faculte_column(exception_rows())
    assert [row["faculte_classique"] for row in column] == ["non"] * len(column)
    assert len(column) == len(REVIEWED_EXCEPTIONS)
    assert warnings == []


def test_insti_repair_warns_and_follows_rule():
    rows = exception_rows({"PUB-186":
                           "Institut National Supérieur de Technologie Industrielle (INSTI)"})
    column, warnings = build_faculte_column(rows)
    assert [row["faculte_classique"] for row in column] == ["non"] * len(column)
    assert len(warnings) == 1
    assert "PUB-186" in warnings[0] and "redundant" in warnings[0]


def test_repaired_label_contradicting_review_raises():
    rows = exception_rows({"PUB-186": "Faculté des Sciences (FS)"})
    with pytest.raises(ValueError, match="PUB-186"):
        build_faculte_column(rows)


@pytest.mark.parametrize("label", UNRECOGNIZED_LABELS)
def test_unrecognized_repaired_label_raises(label):
    rows = exception_rows({"PUB-186": label})
    with pytest.raises(ValueError, match="PUB-186"):
        build_faculte_column(rows)


def test_missing_exception_id_raises():
    rows = [{"Offre_ID": "PUB-062", "Établissement": "Faculté des Sciences de la Santé (FSS)"}]
    with pytest.raises(ValueError, match="stale"):
        build_faculte_column(rows)


def test_reviewed_exceptions_is_immutable():
    with pytest.raises(TypeError):
        REVIEWED_EXCEPTIONS["PUB-999"] = "Faculté (F)"


def test_script_output_matches_the_committed_file():
    completed = run_script()
    # Every exception still diverges from the rule; E3.5 must drop the
    # redundant ones when it regenerates this file (see its criterion).
    assert completed.stderr == ""
    assert [(row["Offre_ID"], row["faculte_classique"])
            for row in csv.DictReader(completed.stdout.splitlines())] == list(COLUMN_BY_ID.items())
