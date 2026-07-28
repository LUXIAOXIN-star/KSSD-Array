#!/usr/bin/env python3
"""Format a Table 4 summary CSV as machine-readable CSV and Markdown."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path


METHODS = ("KSSD-Array", "ntHash")


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--digits", type=int, default=4,
                        help="digits used only in the Markdown preview")
    return parser.parse_args()


def read_summary(path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("summary CSV has no data rows")
    grouped = {}
    for row in rows:
        method = row.get("method")
        if method not in METHODS:
            raise ValueError("summary contains an unsupported method: {}".format(method))
        grouped.setdefault(row["dataset"], {})[method] = row
    for dataset, methods in grouped.items():
        if set(methods) != set(METHODS):
            raise ValueError("dataset {} does not contain exactly two methods".format(dataset))
    return grouped


def decimal(row, field):
    try:
        return Decimal(row[field])
    except (InvalidOperation, KeyError) as error:
        raise ValueError("invalid numeric field {}".format(field)) from error


def format_rows(grouped):
    rows = []
    for dataset, methods in sorted(grouped.items()):
        kssd = methods["KSSD-Array"]
        nthash = methods["ntHash"]
        kssd_runtime = decimal(kssd, "runtime_s_mean")
        nthash_runtime = decimal(nthash, "runtime_s_mean")
        kssd_throughput = decimal(kssd, "throughput_mwindows_s_mean")
        nthash_throughput = decimal(nthash, "throughput_mwindows_s_mean")
        rows.append({
            "result_status": kssd["result_status"],
            "dataset": dataset,
            "k_start": kssd["k_start"],
            "k_end": kssd["k_end"],
            "w_rule": kssd["w_rule"],
            "repeats_per_k": kssd["repeats_per_k"],
            "kssd_runtime_s_mean": kssd["runtime_s_mean"],
            "kssd_runtime_s_sd": kssd["runtime_s_sd"],
            "nthash_runtime_s_mean": nthash["runtime_s_mean"],
            "nthash_runtime_s_sd": nthash["runtime_s_sd"],
            "runtime_speedup_nthash_over_kssd": str(nthash_runtime / kssd_runtime),
            "kssd_throughput_mwindows_s_mean": kssd["throughput_mwindows_s_mean"],
            "kssd_throughput_mwindows_s_sd": kssd["throughput_mwindows_s_sd"],
            "nthash_throughput_mwindows_s_mean": nthash["throughput_mwindows_s_mean"],
            "nthash_throughput_mwindows_s_sd": nthash["throughput_mwindows_s_sd"],
            "throughput_speedup_kssd_over_nthash": str(
                kssd_throughput / nthash_throughput),
            "measurements_per_method": kssd["n"],
        })
    return rows


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def rounded(value, digits):
    return "{:.{}f}".format(Decimal(value), digits)


def write_markdown(path, rows, digits):
    columns = [
        "Dataset", "k range", "Repeats per k", "KSSD-Array runtime [s]",
        "ntHash runtime [s]", "Runtime speedup", "KSSD-Array throughput [M windows/s]",
        "ntHash throughput [M windows/s]", "Throughput speedup",
    ]
    lines = ["| " + " | ".join(columns) + " |",
             "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        values = [
            row["dataset"],
            "{}-{}".format(row["k_start"], row["k_end"]),
            row["repeats_per_k"],
            "{} +/- {}".format(rounded(row["kssd_runtime_s_mean"], digits),
                                rounded(row["kssd_runtime_s_sd"], digits)),
            "{} +/- {}".format(rounded(row["nthash_runtime_s_mean"], digits),
                                rounded(row["nthash_runtime_s_sd"], digits)),
            rounded(row["runtime_speedup_nthash_over_kssd"], digits) + "x",
            "{} +/- {}".format(
                rounded(row["kssd_throughput_mwindows_s_mean"], digits),
                rounded(row["kssd_throughput_mwindows_s_sd"], digits)),
            "{} +/- {}".format(
                rounded(row["nthash_throughput_mwindows_s_mean"], digits),
                rounded(row["nthash_throughput_mwindows_s_sd"], digits)),
            rounded(row["throughput_speedup_kssd_over_nthash"], digits) + "x",
        ]
        lines.append("| " + " | ".join(values) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    arguments = parse_arguments()
    summary = Path(arguments.summary).expanduser().resolve()
    output_dir = Path(arguments.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = format_rows(read_summary(summary))
    write_csv(output_dir / "table4_nthash_formatted.csv", rows)
    write_markdown(output_dir / "table4_nthash_formatted.md", rows,
                   arguments.digits)


if __name__ == "__main__":
    main()
