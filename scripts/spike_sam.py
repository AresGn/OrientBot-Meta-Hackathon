"""Spike E0.6 (issue #8): can SAM 3.1 locate one table cell from a text prompt?

Throwaway script. Sends the sharp and the blurry series D sheets RUNS times each to
sam-3.1 with a noun phrase naming the SVT note cell, plus a "table" control prompt, and
checks whether a returned box contains the target cell. Raw answers and the summary go
to docs/spikes/sam/. Only the docs/ output matters.

Usage: python scripts/spike_sam.py
"""

import base64
import json
import math
import os
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.clients.meta_client import DEFAULT_BASE_URL  # noqa: E402

# https://dev.meta.ai/docs/sam/segmenting and https://dev.meta.ai/docs/sam/reading-segmentation
MODEL = "sam-3.1"
RESPONSES_PATH = "/responses"
RUNS = 3  # issue #8: GO if the box contains the cell in at least 2 runs out of 3
GO_THRESHOLD = 2
TIMEOUT_SECONDS = 120
CELL_PROMPT = "SVT grade"  # docs: one short noun phrase, no command or question
CONTROL_PROMPT = "table"
OUT_DIR = ROOT / "docs" / "spikes" / "sam"
SAMPLES_DIR = ROOT / "data" / "samples"

# scripts/make_grade_sheets.py: columns 590-730 (Note /20), table top 550, row height 46,
# SVT is the 7th subject row, so y = 550 + 7 * 46 = 872 to 918
SVT_NOTE_CELL = (590, 872, 730, 918)
PAGE_CENTER = (620, 877)  # 1240x1754 page, PIL rotates around the centre
BLUR_ROTATION_DEGREES = -1.5  # make_grade_sheets.blur_sheet
TOLERANCE_PIXELS = 4  # line width and anti-aliasing
BOX_PATTERN = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);[^|]*?(?:c=([\d.]+))?\|>")


def rotate_box(box: tuple, degrees: float) -> tuple:
    """Axis-aligned bounds of box after PIL's Image.rotate (counter-clockwise for positive degrees)."""
    angle = math.radians(degrees)
    corners = [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]
    rotated = []
    for x, y in corners:
        dx, dy = x - PAGE_CENTER[0], y - PAGE_CENTER[1]
        rotated.append((PAGE_CENTER[0] + dx * math.cos(angle) + dy * math.sin(angle),
                        PAGE_CENTER[1] - dx * math.sin(angle) + dy * math.cos(angle)))
    xs, ys = [x for x, _ in rotated], [y for _, y in rotated]
    return (round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys)))


def box_contains(outer: tuple, inner: tuple) -> bool:
    return (outer[0] <= inner[0] + TOLERANCE_PIXELS and outer[1] <= inner[1] + TOLERANCE_PIXELS
            and outer[2] >= inner[2] - TOLERANCE_PIXELS and outer[3] >= inner[3] - TOLERANCE_PIXELS)


def segment(image_path: Path, prompt: str) -> str:
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    body = {
        "model": MODEL,
        "input": [{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}"},
        ]}],
        "metadata": {"include_confidence": "true", "mask_encoding": "one_bit"},
    }
    base_url = os.environ.get("MUSE_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    response = httpx.post(base_url + RESPONSES_PATH, json=body, timeout=TIMEOUT_SECONDS,
                          headers={"Authorization": f"Bearer {os.environ['MUSE_API_KEY']}"})
    response.raise_for_status()
    return response.json()["output"][0]["content"][0]["text"]


def parse_boxes(output_text: str) -> list[dict]:
    return [{"box": [int(x1), int(y1), int(x2), int(y2)], "c": float(c) if c else None}
            for x1, y1, x2, y2, c in BOX_PATTERN.findall(output_text)]


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = {
        "net": (SAMPLES_DIR / "releve_serie_d.jpg", SVT_NOTE_CELL),
        "flou": (SAMPLES_DIR / "releve_serie_d_flou.jpg", rotate_box(SVT_NOTE_CELL, BLUR_ROTATION_DEGREES)),
    }
    summary = {"model": MODEL, "cell_prompt": CELL_PROMPT, "control_prompt": CONTROL_PROMPT,
               "tolerance_pixels": TOLERANCE_PIXELS, "cases": {}}
    for case, (image_path, target) in cases.items():
        runs = []
        for run in range(1, RUNS + 1):
            for prompt in (CELL_PROMPT, CONTROL_PROMPT):
                text = segment(image_path, prompt)
                label = "cell" if prompt == CELL_PROMPT else "control"
                (OUT_DIR / f"{case}_{label}_run{run}.raw.txt").write_text(text, encoding="utf-8")
                boxes = parse_boxes(text)
                hit = any(box_contains(tuple(found["box"]), target) for found in boxes)
                runs.append({"run": run, "prompt": prompt, "boxes": boxes, "contains_target": hit})
                print(f"{case} run {run} '{prompt}': {len(boxes)} box(es), contains target: {hit}")
        cell_hits = sum(row["contains_target"] for row in runs if row["prompt"] == CELL_PROMPT)
        summary["cases"][case] = {"image": image_path.name, "target_cell": list(target), "runs": runs,
                                  "cell_hits": cell_hits, "is_go": cell_hits >= GO_THRESHOLD}
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
