#!/usr/bin/env python3
"""Summarize formal Minimap2 indexing rows and render Table S1."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import statistics


METHODS = ("Original Minimap2", "KSSD-Array")
DATASETS = ("Arabidopsis thaliana", "Human GRCh38", "Zea mays")
MEASURES = (
    "wall_time_s", "time_v_wall_time_s", "cpu_time_s", "peak_rss_gib",
    "index_size_bytes",
    "distinct_minimizers", "singleton_percent", "average_occurrences",
    "average_spacing", "distinct_minimizer_density_per_base",
    "minimizer_occurrence_density_per_base",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args()


def mean(values: list[float]) -> float:
    return statistics.mean(values)


def sample_sd(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> int:
    args = parse_args()
    with args.raw.open(encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle))
    if not raw:
        raise RuntimeError("raw table is empty")
    datasets = ("Phase 5A fixture",) if args.preflight else DATASETS
    expected_repeats = 1 if args.preflight else 5
    expected = len(datasets) * len(METHODS) * expected_repeats
    if len(raw) != expected:
        raise RuntimeError("unexpected raw row count: {} != {}".format(len(raw), expected))
    summary: list[dict[str, object]] = []
    for dataset in datasets:
        for method in METHODS:
            group = [row for row in raw if row["dataset"] == dataset and row["method"] == method]
            if len(group) != expected_repeats:
                raise RuntimeError("incomplete group: {} {}".format(dataset, method))
            row: dict[str, object] = {
                "dataset": dataset,
                "dataset_key": group[0]["dataset_key"],
                "accession": group[0]["accession"],
                "version": group[0]["version"],
                "method": method,
                "repeats": len(group),
                "threads": int(group[0]["threads"]),
                "k": int(group[0]["k"]),
                "w": int(group[0]["w"]),
                "hpc": int(group[0]["hpc"]),
                "sequence_count": int(group[0]["sequence_count"]),
                "total_bases": int(group[0]["total_bases"]),
                "reference_sha256": group[0]["reference_sha256"],
                "executable_sha256": group[0]["executable_sha256"],
                "index_magic_hex": group[0]["index_magic_hex"],
            }
            for field in MEASURES:
                values = [float(item[field]) for item in group]
                row[field + "_mean"] = mean(values)
                row[field + "_sd"] = sample_sd(values)
            deterministic = (
                "distinct_minimizers", "singleton_percent",
                "average_occurrences", "average_spacing", "index_size_bytes",
                "index_sha256", "index_magic_hex",
            )
            for field in deterministic:
                values = {item[field] for item in group}
                row[field + "_repeat_consistent"] = int(len(values) == 1)
            summary.append(row)
    if not args.preflight and len(summary) != 6:
        raise RuntimeError("formal summary must have exactly six rows")
    output = args.output_dir
    write_csv(output / "supplementary_indexing_summary.csv", summary)
    pairwise_rows: list[dict[str, object]] = []
    if not args.preflight:
        raw_index = {
            (row["dataset"], int(row["repeat"]), row["method"]): row
            for row in raw
        }
        for dataset in DATASETS:
            ratios = []
            staged = []
            for repeat in range(1, expected_repeats + 1):
                original = raw_index[(dataset, repeat, METHODS[0])]
                kssd = raw_index[(dataset, repeat, METHODS[1])]
                ratio = (float(kssd["wall_time_s"]) /
                         float(original["wall_time_s"]))
                ratios.append(ratio)
                staged.append((repeat, original, kssd, ratio))
            median_ratio = statistics.median(ratios)
            faster = sum(value < 1.0 for value in ratios)
            slower = sum(value > 1.0 for value in ratios)
            if median_ratio < 0.95 and faster >= 4:
                classification = "KSSD faster"
            elif median_ratio > 1.05 and slower >= 4:
                classification = "KSSD slower"
            else:
                classification = "Inconclusive/comparable"
            for repeat, original, kssd, ratio in staged:
                pairwise_rows.append({
                    "dataset": dataset,
                    "dataset_key": original["dataset_key"],
                    "repeat": repeat,
                    "first_method": (METHODS[0] if
                        int(original["order_position"]) == 1 else METHODS[1]),
                    "original_order_position": original["order_position"],
                    "kssd_order_position": kssd["order_position"],
                    "original_wall_time_s": original["wall_time_s"],
                    "kssd_wall_time_s": kssd["wall_time_s"],
                    "kssd_over_original_wall_ratio":
                        "{:.12f}".format(ratio),
                    "median_paired_ratio": "{:.12f}".format(median_ratio),
                    "paired_direction_count_kssd_faster": faster,
                    "paired_direction_count_kssd_slower": slower,
                    "classification": classification,
                    "original_peak_rss_gib": original["peak_rss_gib"],
                    "kssd_peak_rss_gib": kssd["peak_rss_gib"],
                    "kssd_over_original_memory_ratio": "{:.12f}".format(
                        float(kssd["peak_rss_gib"]) /
                        float(original["peak_rss_gib"])),
                })
        write_csv(output / "supplementary_indexing_pairwise_ratios.csv",
                  pairwise_rows)
    table_rows = []
    for row in summary:
        table_rows.append({
            "Dataset": row["dataset"],
            "Method": row["method"],
            "Real time mean (s)": row["wall_time_s_mean"],
            "Real time SD (s)": row["wall_time_s_sd"],
            "CPU time mean (s)": row["cpu_time_s_mean"],
            "CPU time SD (s)": row["cpu_time_s_sd"],
            "Peak RSS mean (GiB)": row["peak_rss_gib_mean"],
            "Peak RSS SD (GiB)": row["peak_rss_gib_sd"],
            "Distinct minimizers": row["distinct_minimizers_mean"],
            "Average occurrences": row["average_occurrences_mean"],
            "Average spacing": row["average_spacing_mean"],
        })
    table_name = ("supplementary_table_s1.csv" if args.preflight else
                  "supplementary_table_s1_final.csv")
    write_csv(output / table_name, table_rows)
    headers = list(table_rows[0])
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in table_rows:
        formatted = [
            str(row["Dataset"]), str(row["Method"]),
            "{:.2f}".format(float(row["Real time mean (s)"])),
            "{:.2f}".format(float(row["Real time SD (s)"])),
            "{:.2f}".format(float(row["CPU time mean (s)"])),
            "{:.2f}".format(float(row["CPU time SD (s)"])),
            "{:.3f}".format(float(row["Peak RSS mean (GiB)"])),
            "{:.3f}".format(float(row["Peak RSS SD (GiB)"])),
            "{:,.0f}".format(float(row["Distinct minimizers"])),
            "{:.3f}".format(float(row["Average occurrences"])),
            "{:.3f}".format(float(row["Average spacing"])),
        ]
        lines.append("| " + " | ".join(formatted) + " |")
    (output / "supplementary_table_s1.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("SUMMARY_ROWS=" + str(len(summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
