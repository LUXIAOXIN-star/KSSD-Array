#!/usr/bin/env python3
"""Summarize Phase 5C alignment metrics and generate Supplementary Table S2."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
import math
from pathlib import Path


METHODS = ("Original Minimap2", "KSSD-Array")
DATASETS = ("Human", "Zea mays")
READ_LENGTHS = (100, 150)
METRIC_FIELDS = (
    "total_reads", "mapped_reads", "mapped_read_percentage",
    "primary_mapped_reads", "primary_alignment_percentage",
    "truth_matched_primary_alignments", "correct_alignments",
    "global_accuracy", "global_correct_over_total_truth",
    "repetitive_region_mapped_reads", "repetitive_region_correct_alignments",
    "repetitive_region_accuracy", "mapq60_alignments", "mapq60_rate",
    "supplementary_alignment_count", "secondary_alignment_count",
    "output_record_count", "identity_value",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def manuscript_percentage(value: float) -> str:
    proportion = Decimal(str(value / 100.0)).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )
    percentage = (proportion * Decimal(100)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    return "{:+.3f}%".format(percentage)


def main() -> int:
    args = parse_args()
    with args.raw.open(encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle))
    expected = 2 if args.preflight else 8
    if len(raw) != expected:
        raise RuntimeError("unexpected raw row count: {} != {}".format(len(raw), expected))
    for row in raw:
        if row["exit_status"] != "0":
            raise RuntimeError("nonzero formal alignment status")
        for field in METRIC_FIELDS:
            if not math.isfinite(float(row[field])):
                raise RuntimeError("non-finite metric: " + field)
    metrics_rows = []
    for row in raw:
        metrics_rows.append({
            "dataset": row["dataset"], "read_length": row["read_length"],
            "method": row["method"],
            **{field: row[field] for field in METRIC_FIELDS},
        })
    write_csv(args.output_dir / "supplementary_alignment_metrics.csv", metrics_rows)
    if args.preflight:
        print("PREFLIGHT_METRIC_ROWS=2")
        return 0
    by_key = {
        (row["dataset"], int(row["read_length"]), row["method"]): row
        for row in raw
    }
    table_rows = []
    for dataset in DATASETS:
        for read_length in READ_LENGTHS:
            original = by_key[(dataset, read_length, "Original Minimap2")]
            integrated = by_key[(dataset, read_length, "KSSD-Array")]
            global_delta = 100.0 * (
                float(integrated["global_accuracy"]) - float(original["global_accuracy"])
            )
            repeat_delta = 100.0 * (
                float(integrated["repetitive_region_accuracy"])
                - float(original["repetitive_region_accuracy"])
            )
            mapq_delta = 100.0 * (
                float(integrated["mapq60_rate"]) - float(original["mapq60_rate"])
            )
            table_rows.append({
                "dataset": dataset,
                "read_length_bp": read_length,
                "original_global_accuracy": original["global_accuracy"],
                "kssd_array_global_accuracy": integrated["global_accuracy"],
                "global_accuracy_delta_percentage_points": global_delta,
                "original_repetitive_region_accuracy": original["repetitive_region_accuracy"],
                "kssd_array_repetitive_region_accuracy": integrated["repetitive_region_accuracy"],
                "repetitive_region_accuracy_delta_percentage_points": repeat_delta,
                "original_mapq60_rate": original["mapq60_rate"],
                "kssd_array_mapq60_rate": integrated["mapq60_rate"],
                "mapq60_delta_percentage_points": mapq_delta,
            })
    write_csv(args.output_dir / "supplementary_table_s2.csv", table_rows)
    lines = [
        "| Reference | Read length | Global accuracy delta | Repetitive-region accuracy delta | MAPQ = 60 delta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in table_rows:
        lines.append(
            "| {} | {} bp | {} | {} | {} |".format(
                row["dataset"], row["read_length_bp"],
                manuscript_percentage(float(row["global_accuracy_delta_percentage_points"])),
                manuscript_percentage(float(row["repetitive_region_accuracy_delta_percentage_points"])),
                manuscript_percentage(float(row["mapq60_delta_percentage_points"])),
            )
        )
    (args.output_dir / "supplementary_table_s2.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("TABLE_S2_ROWS=4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
