# Final technical report

`main.tex` is the single maintained report; `main.pdf` is its compiled version. The course is ECE 5240. Fill the author field in `metadata.tex` before submission (the user has not provided a name).

Figures are the same vector PDFs used in `results/figures/`. Numerical macros in `metrics.tex` are generated from `results/summary.json`; do not update numbers by hand.

From the repository root:

```sh
python run.py --media --report --package
```

Or compile twice from this directory with `pdflatex main.tex` after running the experiments. The report ZIP has local `figures/` paths and can be uploaded directly to Overleaf; choose `main.tex` and pdfLaTeX.

The report uses single-column 11 pt text, 1.5 line spacing, 1-inch margins, a title page, a one-paragraph abstract, Introduction, Theory and Methods, Procedure, Results, a one-paragraph Conclusions section, and numbered IEEE-style references. The general section-length suggestions in WritingGuidelines are scaled to the 5–10-page midterm limit. No controller performance is invented for this sensor-only task.

This is synthetic model verification. Camera motor dynamics, feedback tracking, image-velocity measurements and physical-camera calibration are outside the implemented scope.
