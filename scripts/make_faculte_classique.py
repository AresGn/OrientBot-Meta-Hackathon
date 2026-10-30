"""Produce data/faculte_classique.csv from the guide offers (E3.4, issue #23).

One row per recommendable offer (Statut_qualité = OK with an established
page): a non-OK or page-less offer must never be picked as the page-9
"Faculté classique" choice. Rule and hand-reviewed exceptions in
src/domain/faculte_classique.py. Rerunning with the same data/ gives the
same file. Regenerate after E3.5 repairs the quarantined labels and
restores their pages, then drop the redundant exceptions the script
warns about on stderr.

Usage (from the repository root):

    python scripts/make_faculte_classique.py --output data/faculte_classique.csv
    python scripts/make_faculte_classique.py  # same CSV on stdout
"""

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.faculte_classique import build_faculte_column  # noqa: E402
from src.domain.guide import OK_STATUS, load_offer_rows, load_pages_by_id  # noqa: E402


def render_csv(rows: list[dict]) -> str:
    """Render rows as CSV text (CRLF, like data/pages_offres.csv)."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["Offre_ID", "faculte_classique"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Produce the faculte_classique column.")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv[1:])
    ok_rows = [row for row in load_offer_rows() if row["Statut_qualité"] == OK_STATUS]
    column, warnings = build_faculte_column(ok_rows)
    pages = load_pages_by_id()
    column = [row for row in column if row["Offre_ID"] in pages]
    for warning in warnings:
        print(warning, file=sys.stderr)
    text = render_csv(column)
    if args.output is None:
        sys.stdout.buffer.write(text.encode("utf-8"))
    else:
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            stream.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
