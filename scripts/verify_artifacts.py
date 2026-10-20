#!/usr/bin/env python3
"""Verify delivered data, images, media, configuration provenance, and PDF."""
import csv
import hashlib
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    r = ROOT / "results"
    s = json.loads((r / "summary.json").read_text())
    cfg = json.loads((ROOT / "config/experiments.json").read_text())
    used = json.loads((r / "config_used.json").read_text())
    assert cfg == used, "result configuration is stale"
    digest = hashlib.sha256(
        (json.dumps(cfg, sort_keys=True, indent=2) + "\n").encode()
    ).hexdigest()
    assert s["config_sha256"] == digest
    expected = {
        "scene": 4,
        "height": 5,
        "pan": 121,
        "tilt": 51,
        "target_motion": 601,
        "occlusion": 51,
        "noise": 6,
        "jacobian": 4,
    }
    for name, count in expected.items():
        with (r / "data" / f"{name}.csv").open() as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == count, (name, len(rows))
    assert s["experiment_checks_passed"] == 6
    assert s["target_motion"]["classification_mismatches"] == 0
    assert s["occlusion"]["classification_mismatches"] == 0
    for name in ["scene", "height", "orientation", "motion_occlusion", "validation"]:
        with Image.open(r / "figures" / f"{name}.png") as im:
            im.verify()
        assert (r / "figures" / f"{name}.pdf").stat().st_size > 1000
    media = json.loads((r / "media/summary.json").read_text())
    assert media["config_sha256"] == digest, "media configuration is stale"
    with (r / "media/measurements.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == media["frames"] * len(cfg["media"]["targets"])
    for row in rows:
        assert (row["visible"] == "1") == (
            row["image_x_m"] != "nan" and row["image_y_m"] != "nan"
        )
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=nb_frames,duration",
                "-of",
                "json",
                str(r / "media/pt_motion.mp4"),
            ],
            text=True,
        )
    )["streams"][0]
    assert int(probe["nb_frames"]) == media["frames"] == 120
    assert abs(float(probe["duration"]) - media["duration_s"]) < 1e-6
    with Image.open(r / "media/pt_motion.gif") as im:
        assert im.n_frames == media["frames"]
    info = subprocess.check_output(
        ["pdfinfo", str(ROOT / "report/main.pdf")], text=True
    )
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    assert 5 <= pages <= 10, f"PDF has {pages} pages"
    text = subprocess.check_output(
        ["pdftotext", str(ROOT / "report/main.pdf"), "-"], text=True
    )
    assert "??" not in text, "unresolved report reference"
    log = ROOT / "report/main.log"
    if log.exists():
        assert not re.search(
            r"Overfull|undefined|LaTeX Warning", log.read_text()
        ), "check report build warnings"

    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, val in attrs:
                if key in ("href", "src", "poster") and not val.startswith(
                    ("http", "#", "data:")
                ):
                    assert (ROOT / val).exists(), f"Broken local link: {val}"

    Links().feed((ROOT / "index.html").read_text())
    print(
        f"PASS: configuration provenance, 8 CSV tables, 5 figure pairs, 120-frame MP4/GIF, {pages}-page report, and gallery links."
    )


if __name__ == "__main__":
    main()
