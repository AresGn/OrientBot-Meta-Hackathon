"""The faculte_classique column (E3.4, issue #23).

Page 9 of the guide strongly recommends choosing at least one program in
a "Faculte Classique" among the three platform choices; build_report
(E4.2) applies that consigne from data/faculte_classique.csv. The file
is produced by scripts/make_faculte_classique.py (rule: the
Etablissement starts with "Faculte", plus hand-reviewed exceptions) and
read through src/domain/guide.load_faculte_classique_by_id. No network,
no API key.
"""

import csv
import subprocess
import sys
from pathlib import Path

from src.domain.guide import FACULTE_PATH, load_faculte_classique_by_id, load_offer_rows

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_faculte_classique.py"

# The only reviewed C/D offers whose CSV label is wrong: the PDF shows
# INSTI (an institut, not a faculte) on pages 57, 59 and 58 while the CSV
# still carries the quarantined FAST/Natitingou label (E3.2). E3.5 repairs
# the labels; the overrides below then agree with the rule. See
# docs/data-audit.md (E3.4 review) and docs/decisions.md.
REVIEWED_NON_FACULTE = ("PUB-186", "PUB-187", "PUB-188")

# Quarantined offers (E3.2) whose true etablissement stays a faculte:
# PUB-045 -> FLASH-Adjarra (page 23), PUB-048 -> FLLAC (page 24),
# PUB-142 -> FLASH-Parakou (page 53). Still oui after the E3.5 repair.
QUARANTINED_FACULTE = ("PUB-045", "PUB-048", "PUB-142")

# Known oui offers, one per faculty kind: health (FSS), medicine (FM),
# sciences (FAST, C only), Natitingou (FAST/Natitingou).
KNOWN_OUI = ("PUB-062", "PUB-078", "PUB-133", "PUB-184")

# Known non offers: a research centre (PUB-001), the "Facultaire" trap
# (PUB-002 CIFRED, a centre whose name contains but never starts with
# "Faculte"), a cooperative UFR (PUB-211), a shifted filiere label
# (PUB-216) and an empty etablissement (PUB-195).
KNOWN_NON = ("PUB-001", "PUB-002", "PUB-195", "PUB-211", "PUB-216")


def load_column_rows():
    with FACULTE_PATH.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def run_script_rows():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True, cwd=ROOT, check=True,
    )
    return list(csv.DictReader(completed.stdout.splitlines()))


def test_values_are_oui_or_non():
    rows = load_column_rows()
    assert rows
    assert {row["faculte_classique"] for row in rows} <= {"oui", "non"}


def test_every_offer_has_exactly_one_row():
    offer_ids = [row["Offre_ID"] for row in load_offer_rows()]
    column_ids = [row["Offre_ID"] for row in load_column_rows()]
    assert len(offer_ids) == 224
    assert sorted(column_ids) == sorted(offer_ids)


def test_known_faculte_offers_are_oui():
    column = {row["Offre_ID"]: row["faculte_classique"] for row in load_column_rows()}
    assert len(KNOWN_OUI) >= 3
    for offre_id in KNOWN_OUI:
        assert column[offre_id] == "oui", offre_id


def test_known_non_faculte_offers_are_non():
    column = {row["Offre_ID"]: row["faculte_classique"] for row in load_column_rows()}
    for offre_id in KNOWN_NON:
        assert column[offre_id] == "non", offre_id


def test_reviewed_insti_offers_are_non():
    column = {row["Offre_ID"]: row["faculte_classique"] for row in load_column_rows()}
    assert len(REVIEWED_NON_FACULTE) == 3
    for offre_id in REVIEWED_NON_FACULTE:
        assert column[offre_id] == "non", offre_id


def test_quarantined_faculte_offers_stay_oui():
    column = {row["Offre_ID"]: row["faculte_classique"] for row in load_column_rows()}
    assert len(QUARANTINED_FACULTE) == 3
    for offre_id in QUARANTINED_FACULTE:
        assert column[offre_id] == "oui", offre_id


def test_final_oui_is_the_rule_minus_the_three_reviewed_exceptions():
    offers = {row["Offre_ID"]: row for row in load_offer_rows()}
    column = {row["Offre_ID"]: row["faculte_classique"] for row in load_column_rows()}
    rule_oui = {offre_id for offre_id, row in offers.items()
                if row["Établissement"].startswith("Faculté")}
    final_oui = {offre_id for offre_id, value in column.items() if value == "oui"}
    assert len(rule_oui) == 65
    assert rule_oui - final_oui == set(REVIEWED_NON_FACULTE)
    assert final_oui - rule_oui == set()
    assert len(final_oui) == 62


def test_script_output_matches_the_committed_file():
    assert run_script_rows() == load_column_rows()


def test_loader_returns_the_column():
    column = load_faculte_classique_by_id()
    assert column == {row["Offre_ID"]: row["faculte_classique"]
                      for row in load_column_rows()}
    assert column["PUB-062"] == "oui"
    assert column["PUB-002"] == "non"
