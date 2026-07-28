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
    "wall_time_s", "cpu_time_s", "peak_rss_gib", "index_size_bytes",
    "distinct_minimizers", "singleton_percent", "average_occurrences",
    "average_spacing",
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    with args.raw.open(encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle))
    if not raw:
        raise RuntimeError("raw table is empty")
    datasets = ("Phase 5A fixture",) if args.preflight else DATASETS
    expected_repeats = 1 if args.preflight else 3
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
            )
            for field in deterministic:
                values = {item[field] for item in group}
                row[field + "_repeat_consistent"] = int(len(values) == 1)
            summary.append(row)
    if not args.preflight and len(summary) != 6:
        raise RuntimeError("formal summary must have exactly six rows")
    output = args.output_dir
    write_csv(output / "supplementary_indexing_summary.csv", summary)
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
    write_csv(output / "supplementary_table_s1.csv", table_rows)
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
