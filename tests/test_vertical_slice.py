import copy
import json
import subprocess
import sys
from pathlib import Path

from src.vertical_slice import run_vertical_slice, search_offers_provisional
from src.tools.verify_report import verify_report

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "data" / "samples" / "vertical_slice_serie_d.json"


def load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def context_of(fixture):
    return {"serie": fixture["serie"], "grades": fixture["grades"],
            "transcript": fixture["transcript"]}


def test_vertical_slice_report_passes_verify_report_without_api():
    fixture = load_fixture()
    result = run_vertical_slice(fixture)
    assert result["problems"] == []
    assert verify_report(result["report"], context_of(fixture)) == []
    assert "PUB-062" in result["text"]
    assert "PUB-133" in result["text"]
    assert "13,15" in result["text"]


def test_provisional_search_only_keeps_ok_rows_for_the_serie():
    rows = search_offers_provisional("D")
    assert rows
    assert all(row["Statut_qualité"] == "OK" for row in rows)
    assert all("D" in [s.strip() for s in row["Bac_recommandé"].split(",")] for row in rows)
    offre_ids = [row["Offre_ID"] for row in rows]
    assert "PUB-062" in offre_ids
    assert "PUB-064" not in offre_ids  # Pharmacie row is not Statut_qualité = OK


def test_changed_grade_in_fixture_makes_verify_report_fail():
    # Tamper with the verifier context, not a re-run of the slice: re-running
    # would rebuild a draft coherent with the new grade and pass again. The
    # falsification is that the already-built report no longer matches the
    # (changed) grades it claims to prove.
    fixture = load_fixture()
    result = run_vertical_slice(fixture)
    assert result["problems"] == []
    tampered = copy.deepcopy(fixture)
    for entry in tampered["grades"]:
        if entry["matiere"] == "SVT":
            entry["note"] = 14
    problems = verify_report(result["report"], context_of(tampered))
    assert problems
    assert {p["type"] for p in problems} & {"grade", "calc"}


def test_script_command_prints_the_verified_report():
    completed = subprocess.run(
        [sys.executable, "scripts/run_vertical_slice.py", str(FIXTURE_PATH)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert completed.returncode == 0, completed.stderr
    assert "PUB-062" in completed.stdout
    assert "PUB-133" in completed.stdout
