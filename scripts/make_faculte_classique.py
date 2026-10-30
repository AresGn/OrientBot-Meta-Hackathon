"""Produce data/faculte_classique.csv from the guide offers (E3.4, issue #23).

Rule (docs/prd.md section 6, point 5): an offer is "oui" when its
Etablissement starts with "Faculte". REVIEWED_EXCEPTIONS holds the
hand-review overrides: the only C/D offers marked oui whose CSV label
is wrong (PDF-checked, see docs/data-audit.md). Rerunning with the same
data/ gives the same file. Regenerate after E3.5 repairs the 7
quarantined labels (the INSTI overrides then agree with the rule).

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

from src.domain.guide import load_offer_rows  # noqa: E402

# Offre_ID -> faculte_classique override. The PDF shows INSTI (an
# institut, not a faculte) on pages 57, 59 and 58 while the CSV still
# carries the quarantined FAST/Natitingou label (E3.2); E3.5 repairs it.
REVIEWED_EXCEPTIONS = {
    "PUB-186": "non",
    "PUB-187": "non",
    "PUB-188": "non",
}


def build_column() -> list[dict]:
    """Return [{Offre_ID, faculte_classique}] in source order."""
    rows = []
    for row in load_offer_rows():
        offre_id = row["Offre_ID"]
        value = "oui" if row["Établissement"].startswith("Faculté") else "non"
        rows.append({"Offre_ID": offre_id,
                     "faculte_classique": REVIEWED_EXCEPTIONS.get(offre_id, value)})
    return rows


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
    text = render_csv(build_column())
    if args.output is None:
        sys.stdout.buffer.write(text.encode("utf-8"))
    else:
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            stream.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
