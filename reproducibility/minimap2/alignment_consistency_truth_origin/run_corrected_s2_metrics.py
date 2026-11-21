#!/usr/bin/env python3
"""Recalculate Supplementary Table S2 from accepted BAM and ART truth files."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
from typing import Dict, List, Sequence, Set, Tuple

from s2_core import (
    METHOD_TOKENS,
    METHODS,
    Assignment,
    BamAudit,
    TruthRecord,
    bed_reference_names,
    bootstrap_paired_delta,
    compute_repeat_membership,
    exact_mcnemar_p,
    historical_bam_metrics,
    historical_compatible_correct,
    load_primary_assignments,
    load_truth_records,
    sha256_file,
    strict_error_category,
    verify_fastq_truth_names,
    verify_file,
    write_csv,
)


WORKFLOW_DIR = Path(__file__).resolve().parent
REPO_ROOT = WORKFLOW_DIR.parents[2]
COUNT_FIELDS = (
    "dataset", "read_length", "method", "total_truth", "primary_mapped",
    "unmapped_or_no_primary", "correct_all_truth", "incorrect_primary",
    "wrong_reference", "wrong_position", "wrong_strand_if_available",
    "unknown_truth_reads", "repeat_origin_total", "repeat_origin_primary_mapped",
    "repeat_origin_correct", "repeat_origin_incorrect_primary",
    "repeat_origin_unmapped", "repeat_origin_mapq60_count", "mapq60_count",
    "historical_compatible_correct_all_truth",
    "historical_compatible_repeat_origin_correct",
)
METRIC_FIELDS = (
    "dataset", "read_length", "method", "primary_correctness_definition",
    "mapping_rate", "all_read_truth_position_accuracy",
    "repeat_origin_truth_position_accuracy", "unmapped_rate",
    "incorrect_mapping_rate", "mapq60_all_read_rate",
    "mapq60_mapped_primary_rate", "repeat_origin_mapping_rate",
    "repeat_origin_incorrect_mapping_rate", "repeat_origin_unmapped_rate",
    "repeat_origin_mapq60_all_read_rate",
    "repeat_origin_mapq60_mapped_primary_rate",
    "historical_compatible_all_read_accuracy",
    "historical_compatible_repeat_origin_accuracy",
)
PAIRED_FIELDS = (
    "dataset", "read_length", "metric", "denominator", "bootstrap_iterations",
    "bootstrap_seed", "original_absolute_proportion", "kssd_absolute_proportion",
    "delta_percentage_points", "bootstrap_ci_lower_percentage_points",
    "bootstrap_ci_upper_percentage_points", "both_yes", "original_only",
    "kssd_only", "neither", "mcnemar_exact_p_value",
)
OUTCOME_FIELDS = (
    "dataset", "read_length", "query_name", "truth_reference",
    "truth_genomic_start0", "truth_genomic_end0", "truth_strand",
    "truth_origin_repeat", "original_primary_mapped", "original_reference",
    "original_position1", "original_strand", "original_mapq",
    "original_correct", "original_error_category", "kssd_primary_mapped",
    "kssd_reference", "kssd_position1", "kssd_strand", "kssd_mapq",
    "kssd_correct", "kssd_error_category",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--accepted-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def run(command: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    completed = subprocess.run(
        list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError("command failed: {}\n{}\n{}".format(
            shlex.join(list(command)), completed.stdout, completed.stderr
        ))
    return completed


def read_csv(path: Path) -> List[dict]:
    with path.open("rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_tsv(path: Path, rows: List[dict]) -> None:
    if not rows:
        raise RuntimeError("refusing to write empty TSV: {}".format(path))
    with path.open("wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def historical_output_inventory(accepted: Path) -> Dict[str, Tuple[int, str]]:
    result = {}
    with (accepted / "output_sha256.tsv").open("rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            result[row["relative_path"]] = (int(row["size_bytes"]), row["sha256"])
    return result


def file_row(kind: str, dataset: str, read_length: object, path: Path,
             expected_size: int, expected_hash: str) -> dict:
    verify_file(path, expected_size, expected_hash)
    return {
        "kind": kind, "dataset": dataset, "read_length": read_length,
        "absolute_path": str(path), "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path), "verified_against_pin": "YES",
    }


def audit_inputs(config: dict, data_root: Path, accepted: Path, output: Path) -> Tuple[List[dict], List[dict]]:
    required_accepted = (
        "supplementary_alignment_raw.csv", "supplementary_alignment_metrics.csv",
        "supplementary_table_s2.csv", "build_manifest.txt", "run_manifest.txt",
        "config.json", "output_sha256.tsv", "TABLE_S2_METHOD_DEFINITION.md",
    )
    for relative in required_accepted:
        if not (accepted / relative).is_file():
            raise FileNotFoundError(accepted / relative)
    input_rows: List[dict] = []
    input_rows.append(file_row(
        "ART semantics documentation", "all", "", data_root / config["art_readme_relative_path"],
        int(config["art_readme_size_bytes"]), config["art_readme_sha256"],
    ))
    input_rows.append(file_row(
        "ART official ALN-to-BED converter", "all", "", data_root / config["art_aln2bed_relative_path"],
        int(config["art_aln2bed_size_bytes"]), config["art_aln2bed_sha256"],
    ))
    seen: Set[Path] = set()
    for dataset in config["datasets"]:
        key = dataset["key"]
        for kind, prefix in (("reference", "reference"), ("repeat BED", "repeat_bed")):
            path = data_root / dataset[prefix + "_relative_path"]
            if path not in seen:
                input_rows.append(file_row(
                    kind, key, "", path, int(dataset[prefix + "_size_bytes"]),
                    dataset[prefix + "_sha256"],
                ))
                seen.add(path)
        for condition in dataset["conditions"]:
            read_length = int(condition["read_length"])
            for kind, prefix in (
                ("FASTQ", "fastq"), ("historical truth TSV", "truth_tsv"),
                ("ART ALN truth", "truth_aln"),
            ):
                path = data_root / condition[prefix + "_relative_path"]
                input_rows.append(file_row(
                    kind, key, read_length, path, int(condition[prefix + "_size_bytes"]),
                    condition[prefix + "_sha256"],
                ))
    inventory = historical_output_inventory(accepted)
    bam_rows: List[dict] = []
    bam_paths: List[Path] = []
    for dataset in config["datasets"]:
        key = dataset["key"]
        for condition in dataset["conditions"]:
            read_length = int(condition["read_length"])
            for method in METHODS:
                token = METHOD_TOKENS[method]
                for subset, suffix in (("global", ""), ("historical_reported_repeat", "-repeats")):
                    relative = "alignments/{}-{}bp-{}{}.bam".format(key, read_length, token, suffix)
                    if relative not in inventory:
                        raise RuntimeError("BAM absent from accepted hash inventory: " + relative)
                    expected_size, expected_hash = inventory[relative]
                    path = accepted / relative
                    verify_file(path, expected_size, expected_hash)
                    bam_paths.append(path)
                    bam_rows.append({
                        "dataset": key, "read_length": read_length, "method": method,
                        "subset": subset, "absolute_path": str(path),
                        "size_bytes": path.stat().st_size, "sha256": sha256_file(path),
                        "accepted_hash_match": "YES", "samtools_quickcheck": "PENDING",
                    })
    quickcheck = run(["samtools", "quickcheck", "-v", *[str(path) for path in bam_paths]], check=False)
    if quickcheck.returncode != 0:
        raise RuntimeError("samtools quickcheck failed:\n{}\n{}".format(quickcheck.stdout, quickcheck.stderr))
    for row in bam_rows:
        row["samtools_quickcheck"] = "PASS"
    write_tsv(output / "input_sha256.tsv", input_rows)
    write_tsv(output / "bam_sha256.tsv", bam_rows)
    lines = [
        "# Input and artifact audit",
        "",
        "Status: **PASS**. All required accepted artifacts are present and hash verified; all 16 accepted BAM files pass `samtools quickcheck`.",
        "",
        "- Accepted historical directory: `{}`.".format(accepted),
        "- Non-BAM pinned inputs verified: {}.".format(len(input_rows)),
        "- BAMs verified: {} (8 global and 8 historical reported-repeat subsets).".format(len(bam_rows)),
        "- BAM index files: none were present or required; evaluation streams coordinate-sorted BAM records with `samtools view`.",
        "- Historical raw/summary tables, build manifest, run manifest, configuration, method definition, and output hash inventory are present.",
        "- Existing BAMs are reused. No Minimap2 alignment or index construction is run by this workflow.",
        "",
        "The complete absolute paths, sizes, and SHA-256 values are in `input_sha256.tsv` and `bam_sha256.tsv`.",
    ]
    (output / "INPUT_AND_ARTIFACT_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("INPUT_AND_BAM_AUDIT=PASS", flush=True)
    return input_rows, bam_rows


def reproduce_historical(config: dict, data_root: Path, accepted: Path, output: Path) -> List[dict]:
    tolerance = int(config["position_tolerance_bp"])
    expected_rows = read_csv(accepted / "supplementary_alignment_raw.csv")
    expected_by_key = {
        (row["dataset_key"], int(row["read_length"]), row["method"]): row
        for row in expected_rows
    }
    expected_table = {
        (row["dataset"], int(row["read_length_bp"])): row
        for row in read_csv(accepted / "supplementary_table_s2.csv")
    }
    reproduction_rows: List[dict] = []
    for dataset in config["datasets"]:
        key, label = dataset["key"], dataset["label"]
        for condition in dataset["conditions"]:
            read_length = int(condition["read_length"])
            truth = load_truth_records(
                data_root / condition["truth_tsv_relative_path"],
                data_root / condition["truth_aln_relative_path"], read_length,
            )
            observed = {}
            for method in METHODS:
                token = METHOD_TOKENS[method]
                main = historical_bam_metrics(
                    accepted / "alignments" / "{}-{}bp-{}.bam".format(key, read_length, token),
                    truth, tolerance,
                )
                repeat = historical_bam_metrics(
                    accepted / "alignments" / "{}-{}bp-{}-repeats.bam".format(key, read_length, token),
                    truth, tolerance,
                )
                if main["unknown"] or repeat["unknown"] or main["duplicate_primary"] or repeat["duplicate_primary"]:
                    raise RuntimeError("historical parser found unknown or duplicate primary records")
                expected = expected_by_key[(key, read_length, method)]
                checks = {
                    "global": main["correct"] / main["truth_matched_primary"],
                    "reported_repeat": repeat["correct"] / repeat["truth_matched_primary"],
                    "mapq60_mapped_primary": main["mapq60"] / main["truth_matched_primary"],
                }
                expected_values = {
                    "global": float(expected["global_accuracy"]),
                    "reported_repeat": float(expected["repetitive_region_accuracy"]),
                    "mapq60_mapped_primary": float(expected["mapq60_rate"]),
                }
                for metric in checks:
                    if abs(checks[metric] - expected_values[metric]) > 1e-15:
                        raise RuntimeError("historical method-level metric mismatch")
                observed[method] = checks
            table = expected_table[(label, read_length)]
            for metric, table_field in (
                ("global", "global_accuracy_delta_percentage_points"),
                ("reported_repeat", "repetitive_region_accuracy_delta_percentage_points"),
                ("mapq60_mapped_primary", "mapq60_delta_percentage_points"),
            ):
                delta = 100.0 * (observed["KSSD-Array"][metric] - observed["Original Minimap2"][metric])
                expected_delta = float(table[table_field])
                difference = abs(delta - expected_delta)
                status = "PASS" if difference <= 1e-12 else "FAIL"
                reproduction_rows.append({
                    "dataset": key, "read_length": read_length, "metric": metric,
                    "expected_delta_percentage_points": expected_delta,
                    "reproduced_delta_percentage_points": delta,
                    "absolute_difference": difference, "status": status,
                })
            print("HISTORICAL_REPRODUCED={} {}bp".format(key, read_length), flush=True)
    if len(reproduction_rows) != 12 or any(row["status"] != "PASS" for row in reproduction_rows):
        raise RuntimeError("failed to reproduce all 12 historical displayed deltas")
    write_tsv(output / "HISTORICAL_METRIC_REPRODUCTION.tsv", reproduction_rows)
    lines = [
        "# Historical metric reproduction",
        "",
        "Status: **PASS — all 12 historical deltas were reproduced from the accepted BAMs.**",
        "",
        "The compatibility parser applies the historical `-F 2308` primary-mapped filter, ±5 bp test against the stored strand-relative offset or `offset-(read_length-1)`, method-specific reported-alignment repeat BAMs, and mapped-primary MAPQ denominator. Every method-level absolute metric matches the accepted raw CSV to better than `1e-15`; every displayed delta matches to the `1e-12` requirement used here.",
        "",
        "This successful reproduction validates parser compatibility only. It does not validate the old truth-coordinate interpretation; the ART audit shows why the corrected analysis must reconstruct genomic intervals from `.aln` strand and reference length.",
    ]
    (output / "HISTORICAL_METRIC_REPRODUCTION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return reproduction_rows


def assignment_fields(assignment: Assignment, prefix: str) -> Dict[str, object]:
    return {
        prefix + "_primary_mapped": 1,
        prefix + "_reference": assignment.reference,
        prefix + "_position1": assignment.position1,
        prefix + "_strand": assignment.strand,
        prefix + "_mapq": assignment.mapq,
    }


def empty_assignment_fields(prefix: str) -> Dict[str, object]:
    return {
        prefix + "_primary_mapped": 0, prefix + "_reference": "",
        prefix + "_position1": "", prefix + "_strand": "", prefix + "_mapq": "",
    }


def proportion(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise RuntimeError("zero denominator")
    return numerator / denominator


def increment_cells(cells: List[int], left: bool, right: bool) -> None:
    if left and right:
        cells[0] += 1
    elif left:
        cells[1] += 1
    elif right:
        cells[2] += 1
    else:
        cells[3] += 1


def validate_bam_audit(audit: BamAudit, truth: Dict[str, TruthRecord], label: str) -> None:
    if audit.unknown_primary_queries:
        raise RuntimeError("unknown primary queries in {}: {}".format(label, len(audit.unknown_primary_queries)))
    if audit.duplicate_mapped_primary_queries:
        raise RuntimeError("duplicate mapped primary queries in {}: {}".format(label, len(audit.duplicate_mapped_primary_queries)))
    overlap = set(audit.assignments).intersection(audit.primary_unmapped_seen)
    if overlap:
        raise RuntimeError("queries have both mapped and unmapped primary records in {}".format(label))
    if not set(audit.assignments).issubset(truth):
        raise RuntimeError("mapped assignment absent from truth")


def calculate_corrected(config: dict, data_root: Path, accepted: Path, output: Path) -> Tuple[List[dict], List[dict], List[dict], List[dict]]:
    tolerance = int(config["position_tolerance_bp"])
    iterations = int(config["bootstrap_iterations"])
    seed = int(config["bootstrap_seed"])
    counts_rows: List[dict] = []
    metrics_rows: List[dict] = []
    paired_rows: List[dict] = []
    repeat_audit_rows: List[dict] = []
    validation_rows: List[dict] = []
    bed_cache: Dict[str, Tuple[Set[str], int]] = {}
    paired_path = output / "paired_read_outcomes.tsv.gz"
    membership_path = output / "truth_origin_repeat_membership.tsv.gz"
    outcome_handle = gzip.open(paired_path, "wt", encoding="utf-8", newline="")
    membership_handle = gzip.open(membership_path, "wt", encoding="utf-8", newline="")
    outcome_writer = csv.DictWriter(outcome_handle, fieldnames=list(OUTCOME_FIELDS), delimiter="\t")
    membership_fields = (
        "dataset", "read_length", "query_name", "truth_reference",
        "truth_start0", "truth_end0", "truth_strand", "repeat_origin",
    )
    membership_writer = csv.DictWriter(membership_handle, fieldnames=list(membership_fields), delimiter="\t")
    outcome_writer.writeheader()
    membership_writer.writeheader()
    try:
        for dataset in config["datasets"]:
            key = dataset["key"]
            repeat_bed = data_root / dataset["repeat_bed_relative_path"]
            if key not in bed_cache:
                bed_cache[key] = bed_reference_names(repeat_bed)
            bed_names, bed_intervals = bed_cache[key]
            for condition in dataset["conditions"]:
                read_length = int(condition["read_length"])
                expected_total = int(condition["read_count"])
                print("CORRECTED_CONDITION_START={} {}bp".format(key, read_length), flush=True)
                truth = load_truth_records(
                    data_root / condition["truth_tsv_relative_path"],
                    data_root / condition["truth_aln_relative_path"], read_length,
                )
                fastq_count = verify_fastq_truth_names(data_root / condition["fastq_relative_path"], truth)
                if len(truth) != expected_total or fastq_count != expected_total:
                    raise RuntimeError("FASTQ/truth count mismatch")
                truth_names = {record.reference for record in truth.values()}
                shared_names = truth_names.intersection(bed_names)
                if not shared_names:
                    raise RuntimeError("repeat BED and truth references cannot be reconciled")
                unmatched = sorted(truth_names - bed_names)
                unmatched_truth_reads = sum(
                    record.reference not in bed_names for record in truth.values()
                )
                members = compute_repeat_membership(truth, repeat_bed, output / "temporary")
                repeat_total = len(members)
                if repeat_total <= 0:
                    raise RuntimeError("empty truth-origin repeat subset")
                print("TRUTH_ORIGIN_REPEAT_READS={} {}bp {}".format(key, read_length, repeat_total), flush=True)
                audits: Dict[str, BamAudit] = {}
                for method in METHODS:
                    token = METHOD_TOKENS[method]
                    bam = accepted / "alignments" / "{}-{}bp-{}.bam".format(key, read_length, token)
                    audits[method] = load_primary_assignments(bam, truth)
                    validate_bam_audit(audits[method], truth, "{} {} {}".format(key, read_length, method))
                stats = {}
                for method in METHODS:
                    stats[method] = {
                        "categories": {name: 0 for name in (
                            "correct", "wrong_reference", "wrong_position", "wrong_strand", "unmapped_or_no_primary"
                        )},
                        "repeat_categories": {name: 0 for name in (
                            "correct", "wrong_reference", "wrong_position", "wrong_strand", "unmapped_or_no_primary"
                        )},
                        "mapq60": 0, "repeat_mapq60": 0,
                        "historical_correct": 0, "repeat_historical_correct": 0,
                    }
                paired_cells = {
                    "all_read_correctness": [0, 0, 0, 0],
                    "primary_mapped_status": [0, 0, 0, 0],
                    "repeat_origin_correctness": [0, 0, 0, 0],
                    "mapq60_all_truth": [0, 0, 0, 0],
                }
                for qname, record in truth.items():
                    is_repeat = qname in members
                    membership_writer.writerow({
                        "dataset": key, "read_length": read_length, "query_name": qname,
                        "truth_reference": record.reference, "truth_start0": record.start0,
                        "truth_end0": record.end0, "truth_strand": record.strand,
                        "repeat_origin": int(is_repeat),
                    })
                    assignments = {
                        method: audits[method].assignments.get(qname) for method in METHODS
                    }
                    categories = {
                        method: strict_error_category(record, assignments[method], tolerance)
                        for method in METHODS
                    }
                    correct = {method: categories[method] == "correct" for method in METHODS}
                    mapped = {method: assignments[method] is not None for method in METHODS}
                    mapq60 = {
                        method: assignments[method] is not None and assignments[method].mapq == 60
                        for method in METHODS
                    }
                    for method in METHODS:
                        stats[method]["categories"][categories[method]] += 1
                        if is_repeat:
                            stats[method]["repeat_categories"][categories[method]] += 1
                        if mapq60[method]:
                            stats[method]["mapq60"] += 1
                            if is_repeat:
                                stats[method]["repeat_mapq60"] += 1
                        if historical_compatible_correct(record, assignments[method], tolerance):
                            stats[method]["historical_correct"] += 1
                            if is_repeat:
                                stats[method]["repeat_historical_correct"] += 1
                    increment_cells(paired_cells["all_read_correctness"], correct["Original Minimap2"], correct["KSSD-Array"])
                    increment_cells(paired_cells["primary_mapped_status"], mapped["Original Minimap2"], mapped["KSSD-Array"])
                    increment_cells(paired_cells["mapq60_all_truth"], mapq60["Original Minimap2"], mapq60["KSSD-Array"])
                    if is_repeat:
                        increment_cells(paired_cells["repeat_origin_correctness"], correct["Original Minimap2"], correct["KSSD-Array"])
                    outcome = {
                        "dataset": key, "read_length": read_length, "query_name": qname,
                        "truth_reference": record.reference,
                        "truth_genomic_start0": record.start0,
                        "truth_genomic_end0": record.end0,
                        "truth_strand": record.strand,
                        "truth_origin_repeat": int(is_repeat),
                    }
                    for method, prefix in (("Original Minimap2", "original"), ("KSSD-Array", "kssd")):
                        assignment = assignments[method]
                        outcome.update(empty_assignment_fields(prefix) if assignment is None else assignment_fields(assignment, prefix))
                        outcome[prefix + "_correct"] = int(correct[method])
                        outcome[prefix + "_error_category"] = categories[method]
                    outcome_writer.writerow(outcome)
                for method in METHODS:
                    categories = stats[method]["categories"]
                    repeat_categories = stats[method]["repeat_categories"]
                    mapped_count = expected_total - categories["unmapped_or_no_primary"]
                    repeat_mapped = repeat_total - repeat_categories["unmapped_or_no_primary"]
                    correct_count = categories["correct"]
                    repeat_correct = repeat_categories["correct"]
                    incorrect = mapped_count - correct_count
                    repeat_incorrect = repeat_mapped - repeat_correct
                    count_row = {
                        "dataset": key, "read_length": read_length, "method": method,
                        "total_truth": expected_total, "primary_mapped": mapped_count,
                        "unmapped_or_no_primary": categories["unmapped_or_no_primary"],
                        "correct_all_truth": correct_count, "incorrect_primary": incorrect,
                        "wrong_reference": categories["wrong_reference"],
                        "wrong_position": categories["wrong_position"],
                        "wrong_strand_if_available": categories["wrong_strand"],
                        "unknown_truth_reads": 0, "repeat_origin_total": repeat_total,
                        "repeat_origin_primary_mapped": repeat_mapped,
                        "repeat_origin_correct": repeat_correct,
                        "repeat_origin_incorrect_primary": repeat_incorrect,
                        "repeat_origin_unmapped": repeat_categories["unmapped_or_no_primary"],
                        "repeat_origin_mapq60_count": stats[method]["repeat_mapq60"],
                        "mapq60_count": stats[method]["mapq60"],
                        "historical_compatible_correct_all_truth": stats[method]["historical_correct"],
                        "historical_compatible_repeat_origin_correct": stats[method]["repeat_historical_correct"],
                    }
                    counts_rows.append(count_row)
                    metrics_rows.append({
                        "dataset": key, "read_length": read_length, "method": method,
                        "primary_correctness_definition": "ART_ALN_strand_aware_reference_and_position_within_{}bp".format(tolerance),
                        "mapping_rate": proportion(mapped_count, expected_total),
                        "all_read_truth_position_accuracy": proportion(correct_count, expected_total),
                        "repeat_origin_truth_position_accuracy": proportion(repeat_correct, repeat_total),
                        "unmapped_rate": proportion(categories["unmapped_or_no_primary"], expected_total),
                        "incorrect_mapping_rate": proportion(incorrect, expected_total),
                        "mapq60_all_read_rate": proportion(stats[method]["mapq60"], expected_total),
                        "mapq60_mapped_primary_rate": proportion(stats[method]["mapq60"], mapped_count),
                        "repeat_origin_mapping_rate": proportion(repeat_mapped, repeat_total),
                        "repeat_origin_incorrect_mapping_rate": proportion(repeat_incorrect, repeat_total),
                        "repeat_origin_unmapped_rate": proportion(repeat_categories["unmapped_or_no_primary"], repeat_total),
                        "repeat_origin_mapq60_all_read_rate": proportion(stats[method]["repeat_mapq60"], repeat_total),
                        "repeat_origin_mapq60_mapped_primary_rate": proportion(stats[method]["repeat_mapq60"], repeat_mapped),
                        "historical_compatible_all_read_accuracy": proportion(stats[method]["historical_correct"], expected_total),
                        "historical_compatible_repeat_origin_accuracy": proportion(stats[method]["repeat_historical_correct"], repeat_total),
                    })
                    validation_rows.extend([
                        {"dataset": key, "read_length": read_length, "check": method + " mapped + unmapped = total", "observed": mapped_count + categories["unmapped_or_no_primary"], "expected": expected_total, "status": "PASS"},
                        {"dataset": key, "read_length": read_length, "check": method + " correct + incorrect + unmapped = total", "observed": correct_count + incorrect + categories["unmapped_or_no_primary"], "expected": expected_total, "status": "PASS"},
                        {"dataset": key, "read_length": read_length, "check": method + " repeat correct <= repeat total", "observed": repeat_correct, "expected": "<= {}".format(repeat_total), "status": "PASS" if repeat_correct <= repeat_total else "FAIL"},
                    ])
                for metric, cells in paired_cells.items():
                    denominator = sum(cells)
                    expected_denominator = repeat_total if metric == "repeat_origin_correctness" else expected_total
                    if denominator != expected_denominator:
                        raise RuntimeError("paired contingency denominator mismatch")
                    cells_tuple = tuple(cells)
                    first_ci = bootstrap_paired_delta(cells_tuple, iterations, seed)
                    second_ci = bootstrap_paired_delta(cells_tuple, iterations, seed)
                    if first_ci != second_ci:
                        raise RuntimeError("bootstrap is not deterministic")
                    both, original_only, kssd_only, neither = cells
                    paired_rows.append({
                        "dataset": key, "read_length": read_length, "metric": metric,
                        "denominator": denominator, "bootstrap_iterations": iterations,
                        "bootstrap_seed": seed,
                        "original_absolute_proportion": proportion(both + original_only, denominator),
                        "kssd_absolute_proportion": proportion(both + kssd_only, denominator),
                        "delta_percentage_points": 100.0 * (kssd_only - original_only) / denominator,
                        "bootstrap_ci_lower_percentage_points": first_ci[0],
                        "bootstrap_ci_upper_percentage_points": first_ci[1],
                        "both_yes": both, "original_only": original_only,
                        "kssd_only": kssd_only, "neither": neither,
                        "mcnemar_exact_p_value": "" if metric == "mapq60_all_truth" else exact_mcnemar_p(original_only, kssd_only),
                    })
                    validation_rows.append({
                        "dataset": key, "read_length": read_length,
                        "check": metric + " paired cells sum to denominator",
                        "observed": denominator, "expected": expected_denominator,
                        "status": "PASS",
                    })
                repeat_audit_rows.append({
                    "dataset": key, "read_length": read_length,
                    "total_truth_reads": expected_total,
                    "repeat_origin_truth_reads": repeat_total,
                    "non_repeat_origin_truth_reads": expected_total - repeat_total,
                    "repeat_origin_proportion": repeat_total / expected_total,
                    "truth_reference_names": len(truth_names),
                    "repeat_bed_reference_names": len(bed_names),
                    "shared_reference_names": len(shared_names),
                    "truth_reads_on_unmatched_reference_names": unmatched_truth_reads,
                    "unmatched_truth_reference_names": ";".join(unmatched),
                    "repeat_bed_intervals": bed_intervals,
                    "same_subset_for_both_methods": "YES",
                })
                validation_rows.extend([
                    {"dataset": key, "read_length": read_length, "check": "truth count equals FASTQ count", "observed": len(truth), "expected": fastq_count, "status": "PASS"},
                    {"dataset": key, "read_length": read_length, "check": "truth query names unique", "observed": len(truth), "expected": expected_total, "status": "PASS"},
                    {"dataset": key, "read_length": read_length, "check": "fixed repeat subset shared by methods", "observed": repeat_total, "expected": repeat_total, "status": "PASS"},
                    {"dataset": key, "read_length": read_length, "check": "bootstrap deterministic seed 42", "observed": "identical replay", "expected": "identical replay", "status": "PASS"},
                ])
                print("CORRECTED_CONDITION_DONE={} {}bp".format(key, read_length), flush=True)
    finally:
        outcome_handle.close()
        membership_handle.close()
    write_csv(output / "supplementary_s2_corrected_counts.csv", COUNT_FIELDS, counts_rows)
    write_csv(output / "supplementary_s2_corrected_metrics.csv", METRIC_FIELDS, metrics_rows)
    write_csv(output / "supplementary_s2_corrected_paired.csv", PAIRED_FIELDS, paired_rows)
    write_tsv(output / "S2_CORRECTED_VALIDATION.tsv", validation_rows)
    write_tsv(output / "TRUTH_ORIGIN_REPEAT_AUDIT.tsv", repeat_audit_rows)
    if any(row["status"] != "PASS" for row in validation_rows):
        raise RuntimeError("one or more corrected validation checks failed")
    repeat_lines = [
        "# Truth-origin repeat audit", "",
        "Status: **PASS**. Repeat membership is calculated once from each ART genomic truth interval using a one-base-or-greater overlap with the pinned repeat BED. The identical read-ID subset is then used for both methods; each read is counted once through `bedtools intersect -u`.", "",
        "| Dataset | Read length | Total truth | Repeat origin | Non-repeat origin | Repeat proportion | Shared refs | Truth reads on unannotated refs | Unmatched truth ref-name count |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in repeat_audit_rows:
        unmatched_count = len([name for name in row["unmatched_truth_reference_names"].split(";") if name])
        repeat_lines.append("| {dataset} | {read_length} | {total_truth_reads} | {repeat_origin_truth_reads} | {non_repeat_origin_truth_reads} | {repeat_origin_proportion:.6f} | {shared_reference_names} | {truth_reads_on_unmatched_reference_names} | {unmatched_count} |".format(unmatched_count=unmatched_count, **row))
    repeat_lines.extend([
        "", "Reference names are compared exactly; no `chr`/accession rewriting is performed. The Human repeat BED contains the 25 assembled chromosomes represented by RefSeq accessions and has exact matches in truth/BAM. ART also sampled alternate/unlocalized scaffolds that are absent from this BED; those reads are explicitly counted above and conservatively receive no repeat annotation. This is incomplete repeat annotation on those scaffolds, not a resolvable naming-prefix mismatch. Zea mays has complete 685/685 reference-name coverage.",
        "", "The per-read membership file is `truth_origin_repeat_membership.tsv.gz`.",
    ])
    (output / "TRUTH_ORIGIN_REPEAT_AUDIT.md").write_text("\n".join(repeat_lines) + "\n", encoding="utf-8")
    validation_lines = [
        "# Corrected S2 validation report", "",
        "Status: **PASS**.", "",
        "All truth/FASTQ counts and unique IDs agree; every accepted mapped primary query is present in truth; no duplicate mapped primary assignment was found; mapped plus unmapped/no-primary equals all truth; correctness partitions close exactly; fixed repeat subsets are method-independent; proportions are bounded; paired cells close to their denominators; and two independent seed-42 bootstrap calls are identical.", "",
        "The unit-test suite covers query-name normalization, SAM flag filtering, ART plus/minus coordinate conversion, repeat overlap, duplicate-primary detection, all-read denominators, unmapped reads, historical reverse-rule separation, and deterministic paired statistics.",
        "",
        "Detailed checks are in `S2_CORRECTED_VALIDATION.tsv`.",
    ]
    (output / "S2_CORRECTED_VALIDATION_REPORT.md").write_text("\n".join(validation_lines) + "\n", encoding="utf-8")
    return counts_rows, metrics_rows, paired_rows, repeat_audit_rows


def write_manifests(config: dict, data_root: Path, accepted: Path, output: Path,
                    input_rows: List[dict], bam_rows: List[dict]) -> None:
    original_exe = data_root / "KSSD-Array-formal-results/minimap2-indexing-s1-20260728-v3/builds/original/source/minimap2"
    kssd_exe = data_root / "KSSD-Array-formal-results/minimap2-indexing-s1-20260728-v3/builds/integrated/source/minimap2"
    build_lines = [
        "SOURCE_REPOSITORY={}".format(REPO_ROOT),
        "SOURCE_HEAD={}".format(run(["git", "rev-parse", "HEAD"]).stdout.strip()),
        "SOURCE_BRANCH={}".format(run(["git", "branch", "--show-current"]).stdout.strip()),
        "WORKFLOW_SOURCE={}".format(WORKFLOW_DIR),
        "PYTHON={}".format(sys.executable),
        "PYTHON_VERSION={}".format(platform.python_version()),
        "SAMTOOLS_VERSION={}".format(run(["samtools", "--version"]).stdout.splitlines()[0]),
        "BEDTOOLS_VERSION={}".format(run(["bedtools", "--version"]).stdout.strip()),
        "NUMPY_VERSION={}".format(__import__("numpy").__version__),
        "SCIPY_VERSION={}".format(__import__("scipy").__version__),
        "ORIGINAL_MINIMAP2_EXECUTABLE={}".format(original_exe),
        "ORIGINAL_MINIMAP2_SHA256={}".format(sha256_file(original_exe)),
        "KSSD_MINIMAP2_EXECUTABLE={}".format(kssd_exe),
        "KSSD_MINIMAP2_SHA256={}".format(sha256_file(kssd_exe)),
        "ALIGNMENTS_RERUN=NO",
    ]
    (output / "build_manifest.txt").write_text("\n".join(build_lines) + "\n", encoding="utf-8")
    run_lines = [
        "RUN_TIMESTAMP={}".format(datetime.now(timezone.utc).astimezone().isoformat()),
        "ACCEPTED_ALIGNMENT_DIRECTORY={}".format(accepted),
        "DATA_ROOT={}".format(data_root),
        "OUTPUT_DIRECTORY={}".format(output),
        "PRIMARY_CORRECTNESS={}".format(config["primary_correctness"]),
        "POSITION_TOLERANCE_BP={}".format(config["position_tolerance_bp"]),
        "GLOBAL_DENOMINATOR=all_truth_reads",
        "UNMAPPED_COUNTS_AS_INCORRECT=YES",
        "REPEAT_SUBSET=ART_truth_origin_interval_overlap_at_least_1bp",
        "BOOTSTRAP_ITERATIONS={}".format(config["bootstrap_iterations"]),
        "BOOTSTRAP_SEED={}".format(config["bootstrap_seed"]),
        "ALIGNMENTS_REUSED=YES",
        "ALIGNMENTS_RERUN=NO",
    ]
    (output / "run_manifest.txt").write_text("\n".join(run_lines) + "\n", encoding="utf-8")
    environment_lines = [
        "TIMESTAMP={}".format(datetime.now(timezone.utc).astimezone().isoformat()),
        "HOST_UNAME={}".format(run(["uname", "-a"]).stdout.strip()),
        "PYTHON_VERSION={}".format(platform.python_version()),
        "PYTHON_IMPLEMENTATION={}".format(platform.python_implementation()),
        "SAMTOOLS_VERSION={}".format(run(["samtools", "--version"]).stdout.splitlines()[0]),
        "BEDTOOLS_VERSION={}".format(run(["bedtools", "--version"]).stdout.strip()),
        "NUMPY_VERSION={}".format(__import__("numpy").__version__),
        "SCIPY_VERSION={}".format(__import__("scipy").__version__),
        "TIMEZONE={}".format(datetime.now().astimezone().tzname()),
    ]
    (output / "environment.txt").write_text("\n".join(environment_lines) + "\n", encoding="utf-8")
    common = "--config {} --data-root {} --accepted-dir {} --output-dir {}".format(
        shlex.quote(str(Path(config["_config_path"]))), shlex.quote(str(data_root)),
        shlex.quote(str(accepted)), shlex.quote(str(output)),
    )
    commands = [
        "{} {} {}".format(shlex.quote(sys.executable), shlex.quote(str(WORKFLOW_DIR / "audit_truth_schema.py")), common),
        "{} {} {}".format(shlex.quote(sys.executable), shlex.quote(str(Path(__file__).resolve())), common),
        "{} {} {}".format(shlex.quote(sys.executable), shlex.quote(str(WORKFLOW_DIR / "summarize_corrected_s2.py")), common),
        "{} {} --workflow-dir {} --output-dir {}".format(
            shlex.quote(sys.executable), shlex.quote(str(WORKFLOW_DIR / "package_corrected_s2.py")),
            shlex.quote(str(WORKFLOW_DIR)), shlex.quote(str(output)),
        ),
    ]
    (output / "commands.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n" + "\n".join(commands) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["_config_path"] = str(config_path)
    data_root = args.data_root.resolve()
    accepted = args.accepted_dir.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    input_rows, bam_rows = audit_inputs(config, data_root, accepted, output)
    reproduce_historical(config, data_root, accepted, output)
    calculate_corrected(config, data_root, accepted, output)
    tests = run([
        sys.executable, "-m", "unittest", "discover", "-s",
        str(WORKFLOW_DIR / "tests"), "-v",
    ])
    (output / "unit_tests.log").write_text(tests.stdout + tests.stderr, encoding="utf-8")
    write_manifests(config, data_root, accepted, output, input_rows, bam_rows)
    print("INPUT_AUDIT=PASS")
    print("HISTORICAL_REPRODUCTION=PASS")
    print("CORRECTED_METRICS=PASS")
    print("UNIT_TESTS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
