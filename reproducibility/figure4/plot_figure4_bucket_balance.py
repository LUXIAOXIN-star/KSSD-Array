#!/usr/bin/env python3
"""Render the six-panel Figure 4 bucket-balance plot."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


METHODS = ["KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "wyhash"]
K_VALUES = list(range(6, 15))
SEQUENCE_LENGTHS = [4_000_000, 8_000_000]
BINS = [101, 199, 499]
PANEL_LABELS = ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)"]
STYLES = {
    "KSSD-Array": dict(color="#1F77B4", linestyle="-", linewidth=2.0,
                       marker="o", markersize=3.2, zorder=3),
    "XXH3": dict(color="#FF7F0E", linestyle="--", linewidth=1.25,
                  marker="s", markersize=2.7, zorder=2),
    "XXH64": dict(color="#2CA02C", linestyle="-.", linewidth=1.25,
                   marker="^", markersize=2.7, zorder=2),
    "MurmurHash3": dict(color="#D62728", linestyle="--", linewidth=1.25,
                        marker="D", markersize=2.6, zorder=2),
    "wyhash": dict(color="#9467BD", linestyle=":", linewidth=1.35,
                   marker="v", markersize=2.7, zorder=2),
}


def normalize_method_labels(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize legacy capitalization without changing numeric columns."""
    result = data.copy()
    mask = result["method"].astype(str).str.lower() == "wyhash"
    result.loc[mask, "method"] = "wyhash"
    return result


def validate(data: pd.DataFrame) -> None:
    required = {
        "sequence_length", "bins", "k", "method",
        "non_rejection_rate_percent",
    }
    missing = required - set(data.columns)
    if missing:
        raise RuntimeError(f"summary is missing columns: {sorted(missing)}")
    if set(data["method"]) != set(METHODS):
        raise RuntimeError(f"unexpected method set: {sorted(data['method'].unique())}")
    expected = {
        (sequence_length, bins, k, method)
        for sequence_length in SEQUENCE_LENGTHS
        for bins in BINS
        for k in K_VALUES
        for method in METHODS
    }
    observed = set(data[["sequence_length", "bins", "k", "method"]]
                   .itertuples(index=False, name=None))
    if observed != expected:
        raise RuntimeError(
            f"summary grid mismatch: missing={len(expected - observed)} "
            f"extra={len(observed - expected)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    data = normalize_method_labels(pd.read_csv(args.summary))
    validate(data)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    plt.rcParams.update({
        "font.family": "Arial" if "Arial" in available_fonts else "DejaVu Sans",
        "font.size": 11,
        "axes.linewidth": 1.0,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    figure, axes = plt.subplots(
        2, 4, figsize=(15.8, 7.2), sharex=True, sharey=True,
        gridspec_kw={"width_ratios": [1, 1, 1, 0.45]},
    )
    panel = 0
    for row, sequence_length in enumerate(SEQUENCE_LENGTHS):
        for column, bins in enumerate(BINS):
            axis = axes[row, column]
            subset = data[(data["sequence_length"] == sequence_length) &
                          (data["bins"] == bins)]
            for method in METHODS:
                method_data = subset[subset["method"] == method].sort_values("k")
                axis.plot(
                    method_data["k"],
                    method_data["non_rejection_rate_percent"],
                    label=method, **STYLES[method],
                )
            axis.set_title(f"bins = {bins}", fontsize=12, pad=8, color="#222222")
            axis.set_xlim(5.6, 14.4)
            axis.set_ylim(-5, 105)
            axis.set_xticks(K_VALUES)
            axis.set_yticks(np.arange(0, 101, 20))
            axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{int(value)}%"))
            axis.grid(True, color="#d9d9d9", linewidth=0.8, alpha=0.65)
            for spine in axis.spines.values():
                spine.set_linewidth(0.9)
                spine.set_color("#bfbfbf")
            axis.tick_params(axis="both", labelsize=10)
            axis.text(0.025, 0.94, PANEL_LABELS[panel], transform=axis.transAxes,
                      ha="left", va="top", fontsize=11, fontweight="bold",
                      color="#222222")
            if row == 1:
                axis.set_xlabel("k-mer length", fontsize=11, color="#222222")
            if column == 0:
                axis.set_ylabel("Chi-square non-rejection rate (%)",
                                fontsize=11, color="#222222")
            panel += 1

    axes[0, 3].axis("off")
    axes[1, 3].axis("off")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    legend = axes[0, 3].legend(
        handles, labels, title="Method", loc="upper left", frameon=False,
        fontsize=11, borderpad=0.35, labelspacing=0.32,
        handlelength=1.4, handletextpad=0.35,
    )
    legend.get_title().set_fontsize(10)
    legend.get_title().set_color("#222222")
    figure.text(0.035, 0.72, "4M sequences", rotation=90,
                va="center", ha="center", fontsize=12, color="#222222")
    figure.text(0.035, 0.30, "8M sequences", rotation=90,
                va="center", ha="center", fontsize=12, color="#222222")
    plt.subplots_adjust(left=0.10, right=0.965, top=0.92, bottom=0.10,
                        wspace=0.16, hspace=0.28)

    png_path = args.output_dir / "figure4_bucket_balance.png"
    pdf_path = args.output_dir / "figure4_bucket_balance.pdf"
    figure.savefig(pdf_path, bbox_inches="tight", pad_inches=0.12,
                   facecolor="white")
    figure.savefig(png_path, bbox_inches="tight", pad_inches=0.12,
                   dpi=300, facecolor="white")
    plt.close(figure)
    print(f"PNG={png_path}")
    print(f"PDF={pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
