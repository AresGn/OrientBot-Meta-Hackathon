"""Draw a reproducible sample of Statut_qualité = OK offers for the hand audit.

Usage (from the repository root):

    python scripts/sample_audit.py --seed 2026

Prints one Offre_ID per line, in drawn order. Rerunning with the same
seed prints the same IDs. See docs/data-audit.md and issue #22.
"""

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.guide import OK_STATUS, load_offer_rows  # noqa: E402

DEFAULT_SEED = 2026  # issue #22: the audit sample is drawn with this seed
AUDIT_COUNT = 20  # docs/backlog.md E3.3: 20 OK rows checked by hand


def sample_ok_offers(seed: int, count: int) -> list[str]:
    """Return `count` OK offer IDs drawn with `seed`, in drawn order."""
    ok_ids = sorted(row["Offre_ID"] for row in load_offer_rows()
                    if row["Statut_qualité"] == OK_STATUS)
    if count > len(ok_ids):
        raise ValueError(f"cannot draw {count} offers from {len(ok_ids)} OK rows")
    return random.Random(seed).sample(ok_ids, count)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Sample OK offers for the hand audit.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--count", type=int, default=AUDIT_COUNT)
    args = parser.parse_args(argv[1:])
    for offre_id in sample_ok_offers(args.seed, args.count):
        print(offre_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
