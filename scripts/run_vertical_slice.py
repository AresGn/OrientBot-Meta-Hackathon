"""Print the verified report of the E2.5 vertical slice for one JSON fixture.

Usage (from the repository root, no API key needed):

    python scripts/run_vertical_slice.py data/samples/vertical_slice_serie_d.json

The fixture path defaults to data/samples/vertical_slice_serie_d.json.
Exit code is 1 (and no report is printed) when verify_report refuses the
draft. See scripts/README.md.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.tools.run_vertical_slice import run_vertical_slice  # noqa: E402

DEFAULT_FIXTURE = ROOT / "data" / "samples" / "vertical_slice_serie_d.json"


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # accented report text on Windows consoles
    fixture_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_FIXTURE
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    result = run_vertical_slice(fixture)
    if result["problems"]:
        for problem in result["problems"]:
            print(f"refused: {problem}", file=sys.stderr)
        return 1
    print(result["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
