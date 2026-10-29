"""Reproducible audit sampling (E3.3, issue #22).

scripts/sample_audit.py draws 20 Statut_qualité = OK offers with a fixed
seed; rerunning it with the same seed must give the same 20 Offre_IDs.
Runs the script as a subprocess: no network, no API key.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sample_audit.py"

# Drawn order of random.Random(2026).sample(sorted(ok_ids), 20) over the
# 206 Statut_qualité = OK rows; locked so a sampling change fails loudly.
EXPECTED_SEED_2026 = [
    "PUB-032", "PUB-087", "PUB-136", "PUB-139", "PUB-176",
    "PUB-028", "PUB-059", "PUB-164", "PUB-170", "PUB-153",
    "PUB-115", "PUB-219", "PUB-157", "PUB-151", "PUB-202",
    "PUB-217", "PUB-215", "PUB-133", "PUB-211", "PUB-216",
]


def run_sample(seed: int) -> list[str]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--seed", str(seed)],
        capture_output=True, text=True, cwd=ROOT, check=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def test_same_seed_gives_same_twenty_offers():
    assert run_sample(2026) == EXPECTED_SEED_2026


def test_sample_holds_twenty_unique_ok_offers():
    from src.domain.guide import OK_STATUS, load_offer_rows

    ok_ids = {row["Offre_ID"] for row in load_offer_rows()
              if row["Statut_qualité"] == OK_STATUS}
    sampled = run_sample(2026)
    assert len(sampled) == 20
    assert len(set(sampled)) == 20
    assert set(sampled) <= ok_ids


def test_different_seed_gives_different_sample():
    assert run_sample(21) != run_sample(2026)
