#!/usr/bin/env python3
"""Plot Supplementary Figure S1 from a new indexing summary."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


METHODS = ("Original Minimap2", "KSSD-Array")
DATASETS = ("Arabidopsis thaliana", "Human GRCh38", "Zea mays")
DISPLAY_DATASETS = ("Arabidopsis", "Human\n(GRCh38)", "Zea mays")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.summary.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    datasets = ("Phase 5A fixture",) if args.preflight else DATASETS
    display = ("Phase 5A fixture",) if args.preflight else DISPLAY_DATASETS
    expected = {(dataset, method) for dataset in datasets for method in METHODS}
    observed = {(row["dataset"], row["method"]) for row in rows}
    if observed != expected or len(rows) != len(expected):
        raise RuntimeError("summary dataset/method grid does not match Figure S1")
    by_key = {(row["dataset"], row["method"]): row for row in rows}
    original = np.array([
        float(by_key[(dataset, METHODS[0])]["wall_time_s_mean"])
        for dataset in datasets
    ])
    integrated = np.array([
        float(by_key[(dataset, METHODS[1])]["wall_time_s_mean"])
        for dataset in datasets
    ])
    original_sd = np.array([
        float(by_key[(dataset, METHODS[0])]["wall_time_s_sd"])
        for dataset in datasets
    ])
    integrated_sd = np.array([
        float(by_key[(dataset, METHODS[1])]["wall_time_s_sd"])
        for dataset in datasets
    ])
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    plt.rcParams.update({
        "font.family": "Arial" if "Arial" in available_fonts else "DejaVu Sans",
        "font.size": 12,
        "axes.linewidth": 1.2,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    y = np.arange(len(datasets))
    figure, axis = plt.subplots(figsize=(8.4, 5.2))
    original_bars = axis.barh(
        y - 0.18, original, height=0.32, xerr=original_sd,
        capsize=2.5, color="#9BBB59", label="Minimap2 v2.30 (original)",
        error_kw={"elinewidth": 0.8, "capthick": 0.8},
    )
    integrated_bars = axis.barh(
        y + 0.18, integrated, height=0.32, xerr=integrated_sd,
        capsize=2.5, color="#4F81BD", label="Minimap2 v2.30 + KSSD-Array",
        error_kw={"elinewidth": 0.8, "capthick": 0.8},
    )
    axis.invert_yaxis()
    axis.set_title("Time (s)", fontsize=15, fontweight="bold", loc="left", pad=10)
    axis.set_yticks(y)
    axis.set_yticklabels(display, fontsize=13)
    maximum = float(max(np.max(original + original_sd),
                        np.max(integrated + integrated_sd)))
    x_limit = max(1, int(np.ceil((maximum * 1.18) / 10.0) * 10))
    if not args.preflight:
        x_limit = max(190, int(np.ceil((maximum + 18.0) / 50.0) * 50))
        axis.set_xticks(np.arange(0, x_limit + 1, 50))
    axis.set_xlim(0, x_limit)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(axis="both", width=1.0, length=4)
    offset = max(maximum * 0.018, 0.03)
    for bars, values, deviations in (
            (original_bars, original, original_sd),
            (integrated_bars, integrated, integrated_sd)):
        for bar, value, deviation in zip(bars, values, deviations):
            axis.text(
                value + deviation + offset,
                bar.get_y() + bar.get_height() / 2,
                "{:.3f}".format(value), va="center", ha="left",
                fontsize=11, fontweight="bold",
            )
    axis.legend(loc="upper right", frameon=True, fontsize=12,
                handlelength=1.6, borderpad=0.5, labelspacing=0.4)
    figure.tight_layout()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    png = args.output_dir / "supplementary_figure_s1.png"
    pdf = args.output_dir / "supplementary_figure_s1.pdf"
    figure.savefig(pdf, bbox_inches="tight", pad_inches=0.08,
                   transparent=True)
    figure.savefig(png, bbox_inches="tight", pad_inches=0.08,
                   transparent=True)
    plt.close(figure)
    print("PNG=" + str(png))
    print("PDF=" + str(pdf))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
