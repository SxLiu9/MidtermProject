#!/usr/bin/env python3
"""Reproduce controlled experiments; optionally render media, report, and package."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ptcamera-mpl"))
os.environ.setdefault(
    "XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "ptcamera-cache")
)
import argparse
import json
import subprocess
from ptcamera.config import ROOT, load_config
from ptcamera.experiments import run_experiments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--media", action="store_true", help="render MP4 and GIF (requires FFmpeg)"
    )
    parser.add_argument(
        "--report", action="store_true", help="compile report twice (requires pdfLaTeX)"
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help="package current sources and artifacts after verification",
    )
    args = parser.parse_args()
    cfg = load_config()
    summary = run_experiments(cfg, ROOT / "results")
    print(json.dumps(summary, indent=2), flush=True)
    if args.media:
        from ptcamera.media import render_media

        render_media(cfg, ROOT / "results")
    from ptcamera.artifacts import write_metrics, write_gallery, package_project

    write_metrics(summary, ROOT / "report/metrics.tex")
    write_gallery(ROOT)
    if args.report:
        env = os.environ.copy()
        env.setdefault("TEXMFVAR", str(Path(tempfile.gettempdir()) / "ptcamera-texmf"))
        for i in range(2):
            with (ROOT / "report" / f"build-{i+1}.log").open("w") as log:
                subprocess.run(
                    [
                        "pdflatex",
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "main.tex",
                    ],
                    cwd=ROOT / "report",
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
        print("Report compiled: report/main.pdf", flush=True)
    if args.package:
        package_project(ROOT)
    print("Open index.html for results; details in results/summary.json.", flush=True)


if __name__ == "__main__":
    main()
