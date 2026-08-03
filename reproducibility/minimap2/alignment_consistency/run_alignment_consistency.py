#!/usr/bin/env python3
"""Run the formal Supplementary Table S2 alignment-consistency workflow."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
INTEGRATION_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG = REPO_ROOT / "reproducibility/minimap2/alignment_consistency/config.json"
SUMMARIZER = SCRIPT_DIR / "summarize_alignment_consistency.py"
FIXTURE_REFERENCE = INTEGRATION_DIR / "fixtures/reference.fa"
FIXTURE_QUERY = INTEGRATION_DIR / "fixtures/query.fa"
METHODS = ("Original Minimap2", "KSSD-Array")
SHA256_CACHE: dict[Path, str] = {}
RAW_FIELDS = (
    "dataset_key", "dataset", "accession", "version", "read_length",
    "method", "reference_path", "reference_sha256", "reads_path",
    "reads_sha256", "truth_path", "truth_sha256", "repeat_bed_path",
    "repeat_bed_sha256", "index_path", "index_size_bytes", "index_sha256",
    "index_magic_hex", "executable_path", "executable_sha256", "command",
    "sort_command", "repeat_command", "exit_status", "total_reads",
    "mapped_reads", "mapped_read_percentage", "primary_mapped_reads",
    "primary_alignment_percentage", "truth_matched_primary_alignments",
    "unknown_truth_alignments", "correct_alignments", "global_accuracy",
    "global_correct_over_total_truth", "repetitive_region_mapped_reads",
    "repetitive_region_correct_alignments", "repetitive_region_accuracy",
    "mapq60_alignments", "mapq60_rate", "supplementary_alignment_count",
    "secondary_alignment_count", "output_record_count", "identity_metric",
    "identity_value", "alignment_path", "alignment_size_bytes",
    "alignment_sha256", "repeat_alignment_path", "log_path",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase5b-output", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reference", action="append", default=[], metavar="KEY=PATH")
    parser.add_argument("--reads", action="append", default=[], metavar="KEY:LENGTH=PATH")
    parser.add_argument("--truth", action="append", default=[], metavar="KEY:LENGTH=PATH")
    parser.add_argument("--bed", action="append", default=[], metavar="KEY=PATH")
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args()


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            "command failed: {}\n{}\n{}".format(
                shlex.join(command), completed.stdout, completed.stderr
            )
        )
    return completed


def sha256_file(path: Path) -> str:
    path = path.resolve()
    if path in SHA256_CACHE:
        return SHA256_CACHE[path]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    value = digest.hexdigest()
    SHA256_CACHE[path] = value
    return value


def parse_overrides(values: list[str], with_length: bool) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("override must use KEY=PATH")
        key, raw_path = value.split("=", 1)
        if with_length and ":" not in key:
            raise ValueError("read/truth override must use KEY:LENGTH=PATH")
        if not key or not raw_path or key in result:
            raise ValueError("invalid or duplicate override: " + value)
        result[key] = Path(raw_path).expanduser().resolve()
    return result


def resolve_path(relative: str, override: Path | None) -> Path:
    candidates = []
    if override is not None:
        candidates.append(override)
    data_root = os.environ.get("KSSD_DATA_DIR")
    if data_root:
        candidates.append(Path(data_root).expanduser().resolve() / relative)
    candidates.append(REPO_ROOT / "reproducibility/data/external" / relative)
    candidates.append(REPO_ROOT / "reproducibility/data/external" / Path(relative).name)
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise FileNotFoundError("unable to resolve input: " + relative)
    return path.resolve()


def verify_file(path: Path, expected_size: int | None, expected_hash: str,
                label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(label + ": " + str(path))
    if expected_size is not None and path.stat().st_size != expected_size:
        raise RuntimeError("size mismatch for " + label)
    observed = sha256_file(path)
    if observed != expected_hash:
        raise RuntimeError(
            "SHA256 mismatch for {}: expected {}, observed {}".format(
                label, expected_hash, observed
            )
        )


def count_fastq(path: Path) -> int:
    lines = 0
    with path.open("rb") as handle:
        for _ in handle:
            lines += 1
    if lines % 4:
        raise RuntimeError("FASTQ line count is not divisible by four: " + str(path))
    return lines // 4


def count_fasta(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(line.startswith(b">") for line in handle)


def resolve_formal_inputs(config: dict[str, object], args: argparse.Namespace) -> list[dict[str, object]]:
    reference_overrides = parse_overrides(args.reference, False)
    read_overrides = parse_overrides(args.reads, True)
    truth_overrides = parse_overrides(args.truth, True)
    bed_overrides = parse_overrides(args.bed, False)
    resolved = []
    for raw_dataset in config["datasets"]:
        dataset = dict(raw_dataset)
        key = str(dataset["key"])
        reference = resolve_path(
            str(dataset["reference_relative_path"]), reference_overrides.get(key)
        )
        verify_file(
            reference, int(dataset["reference_size_bytes"]),
            str(dataset["reference_sha256"]), key + " reference",
        )
        bed = resolve_path(
            str(dataset["repeat_bed_relative_path"]), bed_overrides.get(key)
        )
        verify_file(bed, None, str(dataset["repeat_bed_sha256"]), key + " repeat BED")
        conditions = []
        for raw_reads in dataset["reads"]:
            reads = dict(raw_reads)
            condition_key = "{}:{}".format(key, reads["read_length"])
            reads_path = resolve_path(
                str(reads["relative_path"]), read_overrides.get(condition_key)
            )
            truth_path = resolve_path(
                str(reads["truth_relative_path"]), truth_overrides.get(condition_key)
            )
            verify_file(
                reads_path, int(reads["size_bytes"]), str(reads["sha256"]),
                condition_key + " reads",
            )
            verify_file(
                truth_path, None, str(reads["truth_sha256"]),
                condition_key + " truth",
            )
            observed_reads = count_fastq(reads_path)
            if observed_reads != int(reads["read_count"]):
                raise RuntimeError("read-count mismatch for " + condition_key)
            reads["resolved_path"] = str(reads_path)
            reads["truth_resolved_path"] = str(truth_path)
            conditions.append(reads)
        dataset["reference_resolved_path"] = str(reference)
        dataset["repeat_bed_resolved_path"] = str(bed)
        dataset["reads"] = conditions
        resolved.append(dataset)
    return resolved


def executable_paths(phase5b: Path, config: dict[str, object],
                     verify_pinned_hashes: bool) -> dict[str, Path]:
    paths = {
        "Original Minimap2": phase5b / "builds/original/source/minimap2",
        "KSSD-Array": phase5b / "builds/integrated/source/minimap2",
    }
    expected = {
        "Original Minimap2": str(config["original_executable_sha256"]),
        "KSSD-Array": str(config["integrated_executable_sha256"]),
    }
    for method, path in paths.items():
        if verify_pinned_hashes:
            verify_file(path, None, expected[method], method + " executable")
            continue
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError(method + " executable is missing or not executable")
        version = run([str(path), "--version"]).stdout.strip()
        expected_version = str(config["upstream_version"])
        if not version.startswith(expected_version):
            raise RuntimeError(
                method + " executable version mismatch: " + version
            )
    library = REPO_ROOT / "build/libkssd_array.a"
    if verify_pinned_hashes:
        verify_file(
            library, None, str(config["public_library_sha256"]),
            "public KSSD library"
        )
    elif not library.is_file():
        raise RuntimeError("public KSSD library is missing: " + str(library))
    return paths


def index_magic(path: Path) -> str:
    with path.open("rb") as handle:
        return handle.read(4).hex()


def prepare_formal_indexes(output: Path, phase5b: Path,
                           datasets: list[dict[str, object]],
                           executables: dict[str, Path]) -> dict[tuple[str, str], Path]:
    paths: dict[tuple[str, str], Path] = {}
    for dataset in datasets:
        key = str(dataset["key"])
        reference = Path(str(dataset["reference_resolved_path"]))
        original = output / "indexes" / (key + ".original.mmi")
        log = output / "logs" / (key + "-original-index.stderr")
        command = [str(executables["Original Minimap2"]), "-t", "1", "-d",
                   str(original), str(reference)]
        print("INDEX " + key + ": " + shlex.join(command), flush=True)
        completed = subprocess.run(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        log.write_text(completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError("original index build failed: " + str(log))
        verify_file(
            original, int(dataset["original_index_size_bytes"]),
            str(dataset["original_index_sha256"]), key + " original index",
        )
        integrated = phase5b / "indexes" / (key + ".mmi")
        verify_file(
            integrated, int(dataset["integrated_index_size_bytes"]),
            str(dataset["integrated_index_sha256"]), key + " integrated index",
        )
        if index_magic(original) != "4d4d4902":
            raise RuntimeError("unexpected original index magic: " + key)
        if index_magic(integrated) != "4b534101":
            raise RuntimeError("unexpected integrated index magic: " + key)
        paths[(key, "Original Minimap2")] = original
        paths[(key, "KSSD-Array")] = integrated
    return paths


def prepare_fixture_indexes(output: Path, executables: dict[str, Path]) -> dict[tuple[str, str], Path]:
    paths = {}
    for method in METHODS:
        token = "original" if method == "Original Minimap2" else "kssd-array"
        index = output / "indexes" / ("Fixture." + token + ".mmi")
        completed = run([
            str(executables[method]), "-t", "1", "-d", str(index),
            str(FIXTURE_REFERENCE),
        ])
        if completed.stderr:
            (output / "logs" / ("Fixture-" + token + "-index.stderr")).write_text(
                completed.stderr, encoding="utf-8"
            )
        if not index.is_file() or index.stat().st_size == 0:
            raise RuntimeError("empty fixture index")
        paths[("Fixture", method)] = index
    return paths


def parse_truth(path: Path) -> dict[str, tuple[str, int]]:
    truth = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            fields = line.rstrip().split("\t")
            if len(fields) >= 3:
                chrom, position = fields[1], int(fields[2])
            else:
                chrom, raw_position = fields[1].split(":", 1)
                position = int(raw_position)
            truth[fields[0]] = (chrom, position)
    return truth


def normalize_qname(qname: str, truth: dict[str, tuple[str, int]]) -> str:
    if qname in truth:
        return qname
    if qname.endswith("/1") or qname.endswith("/2"):
        trimmed = qname[:-2]
        if trimmed in truth:
            return trimmed
    return qname


def sam_records(path: Path):
    process = subprocess.Popen(
        ["samtools", "view", str(path)], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    for line in process.stdout:
        fields = line.rstrip().split("\t")
        if len(fields) >= 11:
            yield fields
    stderr = process.stderr.read() if process.stderr is not None else ""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError("samtools view failed: " + stderr)


def evaluate_bam(path: Path, truth: dict[str, tuple[str, int]] | None,
                 read_length: int, total_reads: int) -> dict[str, object]:
    mapped_names = set()
    assignments: dict[str, tuple[str, int, str, int, int]] = {}
    output_records = 0
    primary_mapped = 0
    truth_matched = 0
    unknown_truth = 0
    correct = 0
    mapq60 = 0
    secondary = 0
    supplementary = 0
    reverse_offset = read_length - 1
    for fields in sam_records(path):
        output_records += 1
        qname = fields[0]
        flag = int(fields[1])
        if flag & 0x100:
            secondary += 1
        if flag & 0x800:
            supplementary += 1
        if not flag & 0x4:
            mapped_names.add(qname)
        if flag & 0x904:
            continue
        primary_mapped += 1
        ref_name = fields[2]
        ref_pos = int(fields[3])
        mapq = int(fields[4])
        strand = "-" if flag & 0x10 else "+"
        is_correct = 0
        normalized = qname
        if truth is not None:
            normalized = normalize_qname(qname, truth)
            if normalized not in truth:
                unknown_truth += 1
            else:
                truth_matched += 1
                true_ref, true_pos = truth[normalized]
                if ref_name == true_ref and (
                    abs(ref_pos - true_pos) <= 5
                    or abs(ref_pos - (true_pos - reverse_offset)) <= 5
                ):
                    is_correct = 1
                    correct += 1
                if mapq == 60:
                    mapq60 += 1
        else:
            truth_matched += 1
            correct += 1
            is_correct = 1
            if mapq == 60:
                mapq60 += 1
        assignments[normalized] = (ref_name, ref_pos, strand, mapq, is_correct)
    denominator = truth_matched
    total_truth = len(truth) if truth is not None else total_reads
    return {
        "total_truth_reads": total_truth,
        "mapped_reads": len(mapped_names),
        "mapped_read_percentage": 100.0 * len(mapped_names) / total_reads,
        "primary_mapped_reads": primary_mapped,
        "primary_alignment_percentage": 100.0 * primary_mapped / total_reads,
        "truth_matched_primary_alignments": truth_matched,
        "unknown_truth_alignments": unknown_truth,
        "correct_alignments": correct,
        "accuracy": correct / denominator if denominator else 0.0,
        "correct_over_total_truth": correct / total_truth if total_truth else 0.0,
        "mapq60_alignments": mapq60,
        "mapq60_rate": mapq60 / denominator if denominator else 0.0,
        "secondary_alignment_count": secondary,
        "supplementary_alignment_count": supplementary,
        "output_record_count": output_records,
        "mapped_names": mapped_names,
        "assignments": assignments,
    }


def align(index: Path, executable: Path, reads: Path, bam: Path,
          log: Path, arguments: list[str]) -> tuple[str, str, int]:
    command = [str(executable), *arguments, str(index), str(reads)]
    temporary = bam.with_suffix(".tmp.bam")
    sort_command = ["samtools", "sort", "-o", str(temporary), "-"]
    print("ALIGN " + bam.stem + ": " + shlex.join(command), flush=True)
    with log.open("w", encoding="utf-8") as log_handle:
        first = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=log_handle, text=False,
        )
        assert first.stdout is not None
        second = subprocess.Popen(
            sort_command, stdin=first.stdout, stdout=subprocess.DEVNULL,
            stderr=log_handle, text=False,
        )
        first.stdout.close()
        sort_status = second.wait()
        align_status = first.wait()
    if align_status != 0 or sort_status != 0:
        raise RuntimeError("alignment failed; see " + str(log))
    os.replace(str(temporary), str(bam))
    return shlex.join(command), shlex.join(sort_command), align_status


def repeat_subset(bam: Path, bed: Path, output: Path, log: Path) -> str:
    command = ["bedtools", "intersect", "-a", str(bam), "-b", str(bed), "-u"]
    temporary = output.with_suffix(".tmp.bam")
    with temporary.open("wb") as handle:
        completed = subprocess.run(
            command, stdout=handle, stderr=subprocess.PIPE, check=False,
        )
    if completed.returncode != 0:
        with log.open("ab") as handle:
            handle.write(completed.stderr)
        raise RuntimeError("bedtools repeat selection failed: " + str(log))
    os.replace(str(temporary), str(output))
    return shlex.join(command)


def write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...] | None = None) -> None:
    if not rows:
        raise RuntimeError("refusing to write an empty CSV")
    fieldnames = list(fields or tuple(rows[0]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def diagnostic_rows(dataset: str, read_length: int,
                    results: dict[str, dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    original = results["Original Minimap2"]
    integrated = results["KSSD-Array"]
    original_names = original["mapped_names"]
    integrated_names = integrated["mapped_names"]
    mapped_rows = []
    for qname in sorted(original_names ^ integrated_names):
        mapped_rows.append({
            "dataset": dataset, "read_length": read_length, "query_name": qname,
            "mapped_original": int(qname in original_names),
            "mapped_kssd_array": int(qname in integrated_names),
        })
    original_assignments = original["assignments"]
    integrated_assignments = integrated["assignments"]
    assignment_rows = []
    for qname in sorted(set(original_assignments) | set(integrated_assignments)):
        left = original_assignments.get(qname)
        right = integrated_assignments.get(qname)
        if left == right:
            continue
        assignment_rows.append({
            "dataset": dataset, "read_length": read_length, "query_name": qname,
            "original_target": "" if left is None else left[0],
            "original_position": "" if left is None else left[1],
            "original_strand": "" if left is None else left[2],
            "original_mapq": "" if left is None else left[3],
            "original_correct": "" if left is None else left[4],
            "kssd_target": "" if right is None else right[0],
            "kssd_position": "" if right is None else right[1],
            "kssd_strand": "" if right is None else right[2],
            "kssd_mapq": "" if right is None else right[3],
            "kssd_correct": "" if right is None else right[4],
        })
    distribution_rows = []
    for method, result in results.items():
        distribution_rows.append({
            "dataset": dataset, "read_length": read_length, "method": method,
            "truth_matched_primary": result["truth_matched_primary_alignments"],
            "correct_primary": result["correct_alignments"],
            "incorrect_primary": int(result["truth_matched_primary_alignments"]) - int(result["correct_alignments"]),
            "truth_position_accuracy": result["accuracy"],
        })
    return mapped_rows, assignment_rows, distribution_rows


def build_manifest(output: Path, config: dict[str, object], phase5b: Path,
                   executables: dict[str, Path], indexes: dict[tuple[str, str], Path]) -> None:
    lines = [
        "UPSTREAM_VERSION=" + str(config["upstream_version"]),
        "UPSTREAM_COMMIT=" + str(config["upstream_commit"]),
        "PHASE5B_OUTPUT=" + str(phase5b),
        "ORIGINAL_EXECUTABLE=" + str(executables["Original Minimap2"]),
        "ORIGINAL_EXECUTABLE_SHA256=" + sha256_file(executables["Original Minimap2"]),
        "INTEGRATED_EXECUTABLE=" + str(executables["KSSD-Array"]),
        "INTEGRATED_EXECUTABLE_SHA256=" + sha256_file(executables["KSSD-Array"]),
        "PUBLIC_LIBRARY=" + str(REPO_ROOT / "build/libkssd_array.a"),
        "PUBLIC_LIBRARY_SHA256=" + sha256_file(REPO_ROOT / "build/libkssd_array.a"),
        "SAMTOOLS_VERSION=" + run(["samtools", "--version"]).stdout.splitlines()[0],
        "BEDTOOLS_VERSION=" + run(["bedtools", "--version"]).stdout.strip(),
    ]
    for (key, method), path in sorted(indexes.items()):
        token = (key + "_" + method).upper().replace(" ", "_").replace("-", "_")
        lines.extend((
            token + "_INDEX=" + str(path),
            token + "_INDEX_SIZE_BYTES=" + str(path.stat().st_size),
            token + "_INDEX_SHA256=" + sha256_file(path),
            token + "_INDEX_MAGIC_HEX=" + index_magic(path),
        ))
    (output / "build_manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_formal(output: Path, config: dict[str, object], datasets: list[dict[str, object]],
               executables: dict[str, Path], indexes: dict[tuple[str, str], Path]) -> None:
    raw_rows = []
    mapped_diagnostics = []
    assignment_diagnostics = []
    distribution_diagnostics = []
    for dataset in datasets:
        key = str(dataset["key"])
        bed = Path(str(dataset["repeat_bed_resolved_path"]))
        for reads in dataset["reads"]:
            read_length = int(reads["read_length"])
            reads_path = Path(str(reads["resolved_path"]))
            truth_path = Path(str(reads["truth_resolved_path"]))
            truth = parse_truth(truth_path)
            if len(truth) != int(reads["read_count"]):
                raise RuntimeError("truth/read count mismatch")
            condition_results = {}
            for method in METHODS:
                token = "original" if method == "Original Minimap2" else "kssd-array"
                stem = "{}-{}bp-{}".format(key, read_length, token)
                bam = output / "alignments" / (stem + ".bam")
                repeat_bam = output / "alignments" / (stem + "-repeats.bam")
                log = output / "logs" / (stem + ".stderr")
                command, sort_command, exit_status = align(
                    indexes[(key, method)], executables[method], reads_path,
                    bam, log, [str(item) for item in config["alignment_arguments"]],
                )
                repeat_command = repeat_subset(bam, bed, repeat_bam, log)
                metrics = evaluate_bam(
                    bam, truth, read_length, int(reads["read_count"])
                )
                repeat_metrics = evaluate_bam(
                    repeat_bam, truth, read_length, int(reads["read_count"])
                )
                condition_results[method] = metrics
                row = {
                    "dataset_key": key,
                    "dataset": dataset["manuscript_label"],
                    "accession": dataset["accession"],
                    "version": dataset["version"],
                    "read_length": read_length,
                    "method": method,
                    "reference_path": dataset["reference_resolved_path"],
                    "reference_sha256": dataset["reference_sha256"],
                    "reads_path": reads_path,
                    "reads_sha256": reads["sha256"],
                    "truth_path": truth_path,
                    "truth_sha256": reads["truth_sha256"],
                    "repeat_bed_path": bed,
                    "repeat_bed_sha256": dataset["repeat_bed_sha256"],
                    "index_path": indexes[(key, method)],
                    "index_size_bytes": indexes[(key, method)].stat().st_size,
                    "index_sha256": sha256_file(indexes[(key, method)]),
                    "index_magic_hex": index_magic(indexes[(key, method)]),
                    "executable_path": executables[method],
                    "executable_sha256": sha256_file(executables[method]),
                    "command": command,
                    "sort_command": sort_command,
                    "repeat_command": repeat_command,
                    "exit_status": exit_status,
                    "total_reads": reads["read_count"],
                    "mapped_reads": metrics["mapped_reads"],
                    "mapped_read_percentage": metrics["mapped_read_percentage"],
                    "primary_mapped_reads": metrics["primary_mapped_reads"],
                    "primary_alignment_percentage": metrics["primary_alignment_percentage"],
                    "truth_matched_primary_alignments": metrics["truth_matched_primary_alignments"],
                    "unknown_truth_alignments": metrics["unknown_truth_alignments"],
                    "correct_alignments": metrics["correct_alignments"],
                    "global_accuracy": metrics["accuracy"],
                    "global_correct_over_total_truth": metrics["correct_over_total_truth"],
                    "repetitive_region_mapped_reads": repeat_metrics["primary_mapped_reads"],
                    "repetitive_region_correct_alignments": repeat_metrics["correct_alignments"],
                    "repetitive_region_accuracy": repeat_metrics["accuracy"],
                    "mapq60_alignments": metrics["mapq60_alignments"],
                    "mapq60_rate": metrics["mapq60_rate"],
                    "supplementary_alignment_count": metrics["supplementary_alignment_count"],
                    "secondary_alignment_count": metrics["secondary_alignment_count"],
                    "output_record_count": metrics["output_record_count"],
                    "identity_metric": "truth_position_accuracy",
                    "identity_value": metrics["accuracy"],
                    "alignment_path": bam,
                    "alignment_size_bytes": bam.stat().st_size,
                    "alignment_sha256": sha256_file(bam),
                    "repeat_alignment_path": repeat_bam,
                    "log_path": log,
                }
                raw_rows.append(row)
                write_csv(output / "supplementary_alignment_raw.csv", raw_rows, RAW_FIELDS)
            mapped, assignments, distributions = diagnostic_rows(
                str(dataset["manuscript_label"]), read_length, condition_results
            )
            mapped_diagnostics.extend(mapped)
            assignment_diagnostics.extend(assignments)
            distribution_diagnostics.extend(distributions)
    if mapped_diagnostics:
        write_csv(output / "mapped_query_set_difference.csv", mapped_diagnostics)
    else:
        (output / "mapped_query_set_difference.csv").write_text(
            "dataset,read_length,query_name,mapped_original,mapped_kssd_array\n",
            encoding="utf-8",
        )
    if assignment_diagnostics:
        write_csv(output / "primary_assignment_difference.csv", assignment_diagnostics)
    else:
        (output / "primary_assignment_difference.csv").write_text(
            "dataset,read_length,query_name\n", encoding="utf-8"
        )
    write_csv(output / "identity_distribution_summary.csv", distribution_diagnostics)


def run_preflight(output: Path, config: dict[str, object], executables: dict[str, Path],
                  indexes: dict[tuple[str, str], Path]) -> None:
    raw_rows = []
    total_reads = count_fasta(FIXTURE_QUERY)
    for method in METHODS:
        token = "original" if method == "Original Minimap2" else "kssd-array"
        bam = output / "alignments" / ("Fixture-" + token + ".bam")
        log = output / "logs" / ("Fixture-" + token + ".stderr")
        command, sort_command, exit_status = align(
            indexes[("Fixture", method)], executables[method], FIXTURE_QUERY,
            bam, log, [str(item) for item in config["alignment_arguments"]],
        )
        metrics = evaluate_bam(bam, None, 100, total_reads)
        if not bam.is_file() or bam.stat().st_size == 0 or metrics["output_record_count"] == 0:
            raise RuntimeError("preflight alignment/parser produced no records")
        row = {field: "" for field in RAW_FIELDS}
        row.update({
            "dataset_key": "Fixture", "dataset": "Phase 5A fixture",
            "accession": "synthetic-fixture", "version": "phase5a",
            "read_length": 100, "method": method,
            "reference_path": FIXTURE_REFERENCE,
            "reference_sha256": sha256_file(FIXTURE_REFERENCE),
            "reads_path": FIXTURE_QUERY, "reads_sha256": sha256_file(FIXTURE_QUERY),
            "index_path": indexes[("Fixture", method)],
            "index_size_bytes": indexes[("Fixture", method)].stat().st_size,
            "index_sha256": sha256_file(indexes[("Fixture", method)]),
            "index_magic_hex": index_magic(indexes[("Fixture", method)]),
            "executable_path": executables[method],
            "executable_sha256": sha256_file(executables[method]),
            "command": command, "sort_command": sort_command,
            "exit_status": exit_status, "total_reads": total_reads,
            "mapped_reads": metrics["mapped_reads"],
            "mapped_read_percentage": metrics["mapped_read_percentage"],
            "primary_mapped_reads": metrics["primary_mapped_reads"],
            "primary_alignment_percentage": metrics["primary_alignment_percentage"],
            "truth_matched_primary_alignments": metrics["truth_matched_primary_alignments"],
            "unknown_truth_alignments": 0,
            "correct_alignments": metrics["correct_alignments"],
            "global_accuracy": metrics["accuracy"],
            "global_correct_over_total_truth": metrics["correct_over_total_truth"],
            "repetitive_region_mapped_reads": metrics["primary_mapped_reads"],
            "repetitive_region_correct_alignments": metrics["correct_alignments"],
            "repetitive_region_accuracy": metrics["accuracy"],
            "mapq60_alignments": metrics["mapq60_alignments"],
            "mapq60_rate": metrics["mapq60_rate"],
            "supplementary_alignment_count": metrics["supplementary_alignment_count"],
            "secondary_alignment_count": metrics["secondary_alignment_count"],
            "output_record_count": metrics["output_record_count"],
            "identity_metric": "preflight_parser_check",
            "identity_value": metrics["accuracy"],
            "alignment_path": bam, "alignment_size_bytes": bam.stat().st_size,
            "alignment_sha256": sha256_file(bam), "log_path": log,
        })
        raw_rows.append(row)
    write_csv(output / "supplementary_alignment_raw.csv", raw_rows, RAW_FIELDS)


def write_run_manifest(output: Path, mode: str, config: dict[str, object],
                       datasets: list[dict[str, object]]) -> None:
    lines = [
        "MODE=" + mode,
        "THREADS=" + str(config["threads"]),
        "ALIGNMENT_ARGUMENTS=" + shlex.join([str(item) for item in config["alignment_arguments"]]),
        "REPEAT_COUNT=1",
        "RUNTIME_USED_FOR_ACCEPTANCE=no",
        "SIMULATOR=" + str(config["simulator"]),
        "SIMULATOR_VERSION=" + str(config["simulator_version"]),
        "SIMULATION_SEED=" + str(config["simulation_seed"]),
        "PAIRED_OR_SINGLE=" + str(config["paired_or_single"]),
        "QUALITY_ERROR_MODEL=" + str(config["quality_error_model"]),
    ]
    for dataset in datasets:
        token = str(dataset["key"]).upper()
        if "reference_resolved_path" in dataset:
            lines.extend((
                token + "_REFERENCE=" + str(dataset["reference_resolved_path"]),
                token + "_REFERENCE_SHA256=" + str(dataset["reference_sha256"]),
                token + "_REPEAT_BED=" + str(dataset["repeat_bed_resolved_path"]),
                token + "_REPEAT_BED_SHA256=" + str(dataset["repeat_bed_sha256"]),
            ))
            for reads in dataset["reads"]:
                prefix = token + "_" + str(reads["read_length"]) + "BP"
                lines.extend((
                    prefix + "_READS=" + str(reads["resolved_path"]),
                    prefix + "_READS_SHA256=" + str(reads["sha256"]),
                    prefix + "_READ_COUNT=" + str(reads["read_count"]),
                    prefix + "_TRUTH=" + str(reads["truth_resolved_path"]),
                    prefix + "_TRUTH_SHA256=" + str(reads["truth_sha256"]),
                    prefix + "_SIMULATION_COMMAND=" + str(reads["simulation_command"]),
                ))
    (output / "run_manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output = args.output_dir.expanduser().resolve()
    if output.exists():
        raise FileExistsError("output directory already exists: " + str(output))
    for directory in (output, output / "logs", output / "alignments", output / "indexes"):
        directory.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if int(config["threads"]) != 1 or list(config["alignment_arguments"]) != ["-ax", "sr", "-t", "1"]:
        raise RuntimeError("the pinned protocol requires '-ax sr -t 1'")
    phase5b = args.phase5b_output.expanduser().resolve()
    executables = executable_paths(phase5b, config, not args.preflight)
    if args.preflight:
        datasets: list[dict[str, object]] = []
        indexes = prepare_fixture_indexes(output, executables)
        write_run_manifest(output, "preflight", config, datasets)
        build_manifest(output, config, phase5b, executables, indexes)
        run_preflight(output, config, executables, indexes)
    else:
        datasets = resolve_formal_inputs(config, args)
        indexes = prepare_formal_indexes(output, phase5b, datasets, executables)
        write_run_manifest(output, "formal", config, datasets)
        build_manifest(output, config, phase5b, executables, indexes)
        run_formal(output, config, datasets, executables, indexes)
    command = [
        sys.executable, str(SUMMARIZER), "--raw",
        str(output / "supplementary_alignment_raw.csv"),
        "--output-dir", str(output),
    ]
    if args.preflight:
        command.append("--preflight")
    run(command)
    print("OUTPUT_DIRECTORY=" + str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
