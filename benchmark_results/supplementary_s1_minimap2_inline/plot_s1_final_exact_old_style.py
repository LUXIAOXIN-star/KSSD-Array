#!/usr/bin/env python3
"""Re-render Supplementary Figure S1 without changing indexing data."""

from __future__ import annotations

import csv
import math
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_INPUT = Path("supplementary_indexing_summary.csv")
DEFAULT_OUT = Path(".")
STEM = "supplementary_figure_s1_final_exact_old_style"
DATASET_KEYS = ["Arabidopsis", "Human_GRCh38", "Zea_mays"]
DATASET_LABELS = ["Arabidopsis", "Human\nGRCh38.p14", "Zea mays"]
DISPLAY_NAME = {
    "Original": "Minimap2 v2.30 (original)",
    "PermLib-KSSD": "Minimap2 v2.30 + KSSD-Array",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    with args.summary.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected = {
        (dataset, method)
        for dataset in DATASET_KEYS
        for method in ("Original Minimap2", "KSSD-Array")
    }
    observed = {(row["dataset_key"], row["method"]) for row in rows}
    if observed != expected or len(rows) != len(expected):
        raise RuntimeError("Input is not the verified 3x2 Supplementary Figure S1 grid")
    by_key = {(row["dataset_key"], row["method"]): row for row in rows}

    original, original_sd, modified, modified_sd = [], [], [], []
    for dataset in DATASET_KEYS:
        mean = float(by_key[(dataset, "Original Minimap2")]["wall_time_s_mean"])
        sd = float(by_key[(dataset, "Original Minimap2")]["wall_time_s_sd"])
        original.append(mean)
        original_sd.append(sd)
        mean = float(by_key[(dataset, "KSSD-Array")]["wall_time_s_mean"])
        sd = float(by_key[(dataset, "KSSD-Array")]["wall_time_s_sd"])
        modified.append(mean)
        modified_sd.append(sd)
    original = np.array(original)
    original_sd = np.array(original_sd)
    modified = np.array(modified)
    modified_sd = np.array(modified_sd)

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "axes.linewidth": 1.2,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "axes.grid": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    y = np.arange(len(DATASET_KEYS))
    figure, axis = plt.subplots(figsize=(8.4, 5.2))
    original_bars = axis.barh(
        y - 0.18,
        original,
        height=0.32,
        xerr=original_sd,
        capsize=2.5,
        error_kw={"elinewidth": 0.8, "capthick": 0.8},
        color="#9BBB59",
        label=DISPLAY_NAME["Original"],
    )
    modified_bars = axis.barh(
        y + 0.18,
        modified,
        height=0.32,
        xerr=modified_sd,
        capsize=2.5,
        error_kw={"elinewidth": 0.8, "capthick": 0.8},
        color="#4F81BD",
        label=DISPLAY_NAME["PermLib-KSSD"],
    )
    axis.invert_yaxis()
    axis.set_title("Time (s)", fontsize=15, fontweight="bold", loc="left", pad=10)
    axis.set_yticks(y)
    axis.set_yticklabels(DATASET_LABELS, fontsize=13)
    maximum = float(max(np.max(original + original_sd), np.max(modified + modified_sd)))
    x_limit = max(190, int(math.ceil((maximum + 18) / 50.0) * 50))
    axis.set_xlim(0, x_limit)
    axis.set_xticks(np.arange(0, x_limit + 1, 50))
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(axis="both", width=1.0, length=4)

    for bars, values, deviations in (
        (original_bars, original, original_sd),
        (modified_bars, modified, modified_sd),
    ):
        for bar, value, deviation in zip(bars, values, deviations):
            axis.text(
                value + deviation + (3.0 if value < 20 else 3.5),
                bar.get_y() + bar.get_height() / 2,
                f"{value:.3f}",
                va="center",
                ha="left",
                fontsize=11,
                fontweight="bold",
            )
    axis.legend(
        loc="upper right",
        frameon=True,
        fontsize=12,
        handlelength=1.6,
        borderpad=0.5,
        labelspacing=0.4,
    )
    figure.tight_layout()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output_dir / f"{STEM}.pdf", bbox_inches="tight", pad_inches=0.08, transparent=True)
    figure.savefig(args.output_dir / f"{STEM}.png", bbox_inches="tight", pad_inches=0.08, transparent=True)
    plt.close(figure)


if __name__ == "__main__":
    main()
