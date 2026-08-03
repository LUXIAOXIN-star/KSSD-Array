#!/usr/bin/env python3
"""Build and run the portable Table 4 KSSD-Array versus ntHash workflow."""

import argparse
import csv
import gzip
import hashlib
import json
import os
import platform
import shlex
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path


METHODS = ("KSSD-Array", "ntHash")
RAW_NAME = "table4_nthash_raw.csv"
SUMMARY_NAME = "table4_nthash_summary.csv"
SOURCE_NAMES = (
    "benchmark_table4_nthash.cpp",
    "nthash_wrapper.cpp",
    "nthash_wrapper.h",
)
FIXTURE_GENERATOR = Path("tests/fixture_generators/generate_test_fixtures.sh")
TABLE4_FIXTURE = Path("reproducibility/table4/fixtures/table4_smoke.fa")


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+")
    parser.add_argument("--dataset-names", nargs="+")
    parser.add_argument("--k-start", type=int, default=4)
    parser.add_argument("--k-end", type=int, default=32)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--nthash-prefix")
    parser.add_argument("--output-dir")
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_command(command, cwd, log_path=None):
    completed = subprocess.run(
        command, cwd=str(cwd), text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False
    )
    if log_path is not None:
        log_path.write_text(
            "COMMAND\n{}\n\nSTDOUT\n{}\nSTDERR\n{}".format(
                shlex.join([str(part) for part in command]),
                completed.stdout, completed.stderr
            ),
            encoding="utf-8",
        )
    if completed.returncode != 0:
        detail = " (see {})".format(log_path) if log_path else ""
        raise RuntimeError("command failed{}: {}".format(
            detail, shlex.join([str(part) for part in command])
        ))
    return completed


def resolve_nthash_prefix(arguments, repo_root):
    if arguments.nthash_prefix:
        prefix = Path(arguments.nthash_prefix).expanduser()
        source = "--nthash-prefix"
    elif os.environ.get("NTHASH_ROOT"):
        prefix = Path(os.environ["NTHASH_ROOT"]).expanduser()
        source = "NTHASH_ROOT"
    else:
        prefix = repo_root / "third_party/ntHash/install"
        source = "repository-local installation"
    prefix = prefix.resolve()
    header = prefix / "include/nthash/nthash.hpp"
    candidates = (prefix / "lib/libnthash.a", prefix / "lib64/libnthash.a")
    library = next((path for path in candidates if path.is_file()), None)
    if not header.is_file() or library is None:
        raise RuntimeError(
            "ntHash not found under {}. Use --nthash-prefix, set NTHASH_ROOT, "
            "or run reproducibility/table4/prepare_nthash.sh".format(prefix)
        )
    return prefix, header, library, source


def resolve_datasets(arguments, repo_root, generated_root=None):
    if arguments.smoke:
        if arguments.datasets or arguments.dataset_names:
            raise RuntimeError("--smoke uses exactly the source-generated smoke fixture")
        if generated_root is None:
            raise RuntimeError("generated fixture root is required for --smoke")
        return [generated_root / TABLE4_FIXTURE], ["Table4_smoke"]
    if arguments.datasets:
        datasets = [Path(value).expanduser().resolve()
                    for value in arguments.datasets]
        names = arguments.dataset_names
        if names is None or len(names) != len(datasets):
            raise RuntimeError("--dataset-names must match --datasets")
        return datasets, names
    if arguments.dataset_names:
        raise RuntimeError("--dataset-names requires --datasets")

    metadata = json.loads((repo_root / "reproducibility/data/datasets.json").read_text(
        encoding="utf-8"))
    names = ["Synthetic_300M", "Human_GRCh38"]
    base = Path(os.environ.get("KSSD_DATA_DIR",
                               repo_root / "reproducibility/data/external")).expanduser()
    datasets = [base / metadata["datasets"][name]["filename"] for name in names]
    return [path.resolve() for path in datasets], names


def fasta_record_count(path):
    opener = gzip.open if path.suffix == ".gz" else open
    count = 0
    with opener(path, "rt", encoding="ascii", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                count += 1
    return count


def validate_request(arguments, repo_root, output_dir, generated_root=None):
    if arguments.smoke:
        k_start = k_end = 21
        repeats = 1
        result_status = "functional_smoke_not_formal_performance"
    else:
        k_start, k_end = arguments.k_start, arguments.k_end
        repeats = arguments.repeats
        result_status = "formal_measurement"
    if not (1 <= k_start <= k_end <= 32):
        raise RuntimeError("k range must be within 1..32")
    if repeats < 1:
        raise RuntimeError("repeats must be positive")
    datasets, names = resolve_datasets(arguments, repo_root, generated_root)
    missing = [str(path) for path in datasets if not path.is_file()]
    if missing:
        raise RuntimeError(
            "required dataset file(s) are missing: {}. Supply --datasets, set "
            "KSSD_DATA_DIR, or populate reproducibility/data/external".format(", ".join(missing))
        )
    if output_dir == repo_root or repo_root in output_dir.parents:
        raise RuntimeError("generated benchmark output must be outside the repository")
    return datasets, names, k_start, k_end, repeats, result_status


def parse_output(text, expected_k, expected_repeat):
    metadata = None
    parity = None
    results = []
    for line in text.splitlines():
        fields = line.split("\t")
        if fields[0] == "META" and len(fields) == 10:
            metadata = {
                "raw_bases": int(fields[1]),
                "valid_bases": int(fields[2]),
                "ambiguous_bases_skipped": int(fields[3]),
                "valid_kmers": int(fields[4]),
                "valid_windows": int(fields[5]),
                "k": int(fields[6]),
                "w": int(fields[7]),
                "repeat": int(fields[8]),
                "seed": int(fields[9]),
            }
        elif fields[0] == "PARITY" and len(fields) == 3:
            parity = {"status": fields[1], "samples": int(fields[2])}
        elif fields[0] == "RESULT" and len(fields) == 8:
            results.append({
                "method": fields[1],
                "runtime_s": float(fields[2]),
                "throughput_windows_s": float(fields[3]),
                "valid_kmers": int(fields[4]),
                "valid_windows": int(fields[5]),
                "minimizers": int(fields[6]),
                "checksum": fields[7],
            })
    if metadata is None or parity is None:
        raise RuntimeError("benchmark output is missing META or PARITY")
    if metadata["k"] != expected_k or metadata["w"] != expected_k:
        raise RuntimeError("benchmark reported an unexpected k or w")
    if metadata["repeat"] != expected_repeat:
        raise RuntimeError("benchmark reported an unexpected repeat")
    if parity["status"] != "PASS" or parity["samples"] < 1:
        raise RuntimeError("KSSD fast/context parity failed")
    if len(results) != 2 or {row["method"] for row in results} != set(METHODS):
        raise RuntimeError("benchmark must emit exactly KSSD-Array and ntHash")
    expected_kmers = metadata["valid_bases"] - expected_k + 1
    expected_windows = expected_kmers - expected_k + 1
    if metadata["valid_kmers"] != expected_kmers:
        raise RuntimeError("valid k-mer count is inconsistent")
    if metadata["valid_windows"] != expected_windows:
        raise RuntimeError("valid window count is inconsistent")
    for result in results:
        if result["valid_kmers"] != expected_kmers:
            raise RuntimeError("method k-mer count is inconsistent")
        if result["valid_windows"] != expected_windows:
            raise RuntimeError("method window count is inconsistent")
        if result["minimizers"] != expected_windows:
            raise RuntimeError("no-dedup minimizer count is inconsistent")
        if result["runtime_s"] <= 0 or result["throughput_windows_s"] <= 0:
            raise RuntimeError("timing values must be positive")
    return metadata, parity, results


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def mean_sd(values):
    if len(values) == 1:
        return values[0], 0.0
    return statistics.mean(values), statistics.stdev(values)


def summarize(rows, k_start, k_end, repeats, result_status):
    grouped = {}
    for row in rows:
        grouped.setdefault((row["dataset"], row["method"]), []).append(row)
    summary = []
    for (dataset, method), members in sorted(grouped.items()):
        runtime_mean, runtime_sd = mean_sd(
            [float(row["runtime_s"]) for row in members])
        throughput_mean, throughput_sd = mean_sd(
            [float(row["throughput_mwindows_s"]) for row in members])
        summary.append({
            "result_status": result_status,
            "dataset": dataset,
            "k_start": k_start,
            "k_end": k_end,
            "w_rule": "w=k",
            "repeats_per_k": repeats,
            "method": method,
            "runtime_s_mean": "{:.12f}".format(runtime_mean),
            "runtime_s_sd": "{:.12f}".format(runtime_sd),
            "throughput_mwindows_s_mean": "{:.12f}".format(throughput_mean),
            "throughput_mwindows_s_sd": "{:.12f}".format(throughput_sd),
            "valid_kmers_min": min(int(row["valid_kmers"]) for row in members),
            "valid_kmers_max": max(int(row["valid_kmers"]) for row in members),
            "valid_windows_min": min(int(row["valid_windows"]) for row in members),
            "valid_windows_max": max(int(row["valid_windows"]) for row in members),
            "n": len(members),
        })
    return summary


def main():
    arguments = parse_arguments()
    repo_root = Path(__file__).resolve().parents[2]
    if arguments.output_dir:
        output_dir = Path(arguments.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(tempfile.mkdtemp(
            prefix="kssd-table4-smoke-" if arguments.smoke
            else "kssd-table4-run-"))
    reserved = [output_dir / name for name in (
        RAW_NAME, SUMMARY_NAME, "table4_nthash_formatted.csv",
        "table4_nthash_formatted.md", "build_manifest.txt", "run_manifest.txt"
    )]
    if any(path.exists() for path in reserved):
        raise RuntimeError("output directory contains reserved output files")
    logs = output_dir / "logs"
    bins = output_dir / "bin"
    logs.mkdir(parents=True, exist_ok=True)
    bins.mkdir(parents=True, exist_ok=True)

    fixture_workspace = None
    generated_root = None
    if arguments.smoke:
        fixture_workspace = tempfile.TemporaryDirectory(
            prefix="kssd-table4-generated-fixtures-")
        generated_root = Path(fixture_workspace.name)
        run_command([
            str(repo_root / FIXTURE_GENERATOR),
            "--output-dir", str(generated_root), "--seed", "42",
        ], repo_root, logs / "generate_fixtures.log")

    datasets, names, k_start, k_end, repeats, result_status = validate_request(
        arguments, repo_root, output_dir, generated_root)
    prefix, nthash_header, nthash_library, nthash_resolution = (
        resolve_nthash_prefix(arguments, repo_root))
    dataset_records = []
    for path, name in zip(datasets, names):
        dataset_records.append({
            "label": name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "fasta_record_count": fasta_record_count(path),
        })

    run_command(["make", "build/libkssd_array.a"], repo_root,
                logs / "build_library.log")
    compiler = os.environ.get("CXX", "c++")
    compiler_version = run_command([compiler, "--version"], repo_root).stdout.splitlines()[0]
    commit = run_command(["git", "rev-parse", "HEAD"], repo_root).stdout.strip()
    source_dir = repo_root / "reproducibility/table4"
    library = repo_root / "build/libkssd_array.a"
    raw_rows = []
    compile_records = []
    executed_commands = []
    parity_samples = []

    for k in range(k_start, k_end + 1):
        binary = bins / "benchmark_k{}_w{}".format(k, k)
        flags = [
            "-O3", "-march=native", "-std=c++17", "-Wall", "-Wextra",
            "-Wpedantic", "-DK={}".format(k), "-DW={}".format(k)
        ]
        command = [compiler] + flags + [
            "-Iinclude", "-I{}".format(prefix / "include"),
            str(source_dir / "benchmark_table4_nthash.cpp"),
            str(source_dir / "nthash_wrapper.cpp"),
            "-Lbuild", "-Wl,-Bstatic", "-lkssd_array", "-Wl,-Bdynamic",
            "-L{}".format(nthash_library.parent), "-lnthash", "-lz",
            "-o", str(binary),
        ]
        run_command(command, repo_root, logs / "compile_k{}_w{}.log".format(k, k))
        compile_records.append({
            "k": k, "w": k, "command": command, "flags": flags,
            "binary": str(binary), "binary_sha256": sha256_file(binary),
        })
        for dataset, dataset_record in zip(datasets, dataset_records):
            for repeat in range(1, repeats + 1):
                run_log = logs / "run_{}_k{}_w{}_repeat{}.log".format(
                    dataset_record["label"], k, k, repeat)
                run = [str(binary), str(dataset), str(repeat), str(arguments.seed)]
                completed = run_command(run, repo_root, run_log)
                executed_commands.append(run)
                metadata, parity, results = parse_output(
                    completed.stdout, k, repeat)
                parity_samples.append(parity["samples"])
                for result in results:
                    raw_rows.append({
                        "result_status": result_status,
                        "dataset": dataset_record["label"],
                        "dataset_path": dataset_record["path"],
                        "dataset_size_bytes": dataset_record["size_bytes"],
                        "dataset_sha256": dataset_record["sha256"],
                        "fasta_record_count": dataset_record["fasta_record_count"],
                        "k": k, "w": k, "repeat": repeat,
                        "seed": arguments.seed, "method": result["method"],
                        "runtime_s": "{:.12f}".format(result["runtime_s"]),
                        "throughput_windows_s": "{:.6f}".format(
                            result["throughput_windows_s"]),
                        "throughput_mwindows_s": "{:.12f}".format(
                            result["throughput_windows_s"] / 1000000.0),
                        "raw_bases": metadata["raw_bases"],
                        "valid_bases": metadata["valid_bases"],
                        "ambiguous_bases_skipped": metadata["ambiguous_bases_skipped"],
                        "valid_kmers": result["valid_kmers"],
                        "valid_windows": result["valid_windows"],
                        "minimizers": result["minimizers"],
                        "checksum": result["checksum"],
                        "parity_samples": parity["samples"],
                        "log_file": str(run_log),
                    })

    raw_fields = list(raw_rows[0].keys())
    summary_rows = summarize(raw_rows, k_start, k_end, repeats, result_status)
    summary_fields = list(summary_rows[0].keys())
    write_csv(output_dir / RAW_NAME, raw_rows, raw_fields)
    write_csv(output_dir / SUMMARY_NAME, summary_rows, summary_fields)

    header_text = nthash_header.read_text(encoding="utf-8", errors="replace")
    nthash_function = "ntHash_v2" if 'NTHASH_FN_NAME = "ntHash_v2"' in header_text else "unknown"
    build_manifest = {
        "repository_commit": commit,
        "compiler": compiler_version,
        "benchmark_sources": {
            name: sha256_file(source_dir / name) for name in SOURCE_NAMES
        },
        "libkssd_array_a": {"path": str(library), "sha256": sha256_file(library)},
        "nthash": {
            "pinned_version": "2.4.0",
            "pinned_commit": "c26bd4572a19de81e30d55042dbd33c1fd21d4b6",
            "function_name": nthash_function,
            "resolution": nthash_resolution,
            "prefix": str(prefix),
            "header": str(nthash_header),
            "header_sha256": sha256_file(nthash_header),
            "library": str(nthash_library),
            "library_sha256": sha256_file(nthash_library),
        },
        "compile_records": compile_records,
    }
    run_manifest = {
        "result_status": result_status,
        "os": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "datasets": dataset_records,
        "k_start": k_start, "k_end": k_end, "w_rule": "w=k",
        "repeats": repeats, "seed": arguments.seed,
        "kssd_rng": "KSSD_ARRAY_RNG_GLIBC_COMPAT",
        "methods": list(METHODS),
        "fasta_semantics": "first record; non-ACGT symbols are removed without reset",
        "timing_protocol": (
            "KSSD times mapping and minimizer selection from pre-encoded k-mers; "
            "ntHash times rolling hashing and minimizer selection; initialization is excluded"
        ),
        "parity": "PASS",
        "parity_samples_min": min(parity_samples),
        "executed_commands": executed_commands,
        "output_directory": str(output_dir),
    }
    (output_dir / "build_manifest.txt").write_text(
        json.dumps(build_manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "run_manifest.txt").write_text(
        json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    run_command([
        sys.executable, str(repo_root / "reproducibility/table4/format_table4_nthash.py"),
        "--summary", str(output_dir / SUMMARY_NAME),
        "--output-dir", str(output_dir),
    ], repo_root, logs / "format_table.log")

    if arguments.smoke:
        if len(raw_rows) != 2 or len(summary_rows) != 2:
            raise RuntimeError("smoke CSV row counts must both equal two")
        if {row["method"] for row in raw_rows} != set(METHODS):
            raise RuntimeError("smoke method set is incorrect")
    for name in (RAW_NAME, SUMMARY_NAME, "table4_nthash_formatted.csv",
                 "table4_nthash_formatted.md", "build_manifest.txt",
                 "run_manifest.txt"):
        print("OUTPUT\t{}\t{}".format(name, output_dir / name))
    print("OUTPUT\tlogs\t{}".format(logs))
    print("PARITY\tPASS\t{}".format(min(parity_samples)))
    print("ROWS\traw\t{}\tsummary\t{}".format(
        len(raw_rows), len(summary_rows)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        raise SystemExit(1)
