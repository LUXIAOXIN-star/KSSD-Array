#!/usr/bin/env python3
"""Build and run the portable Figure 2 single-thread benchmark workflow."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import statistics
import subprocess
import sys
import tempfile


METHODS = ("KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "wyhash")
RAW_NAME = "figure2_single_thread_raw.csv"
SUMMARY_NAME = "figure2_single_thread_summary.csv"
SOURCE_RELATIVE = Path(
    "reproducibility/figure2/benchmark_single_thread_realistic_kw.c"
)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+")
    parser.add_argument("--dataset-names", nargs="+")
    parser.add_argument("--k-values", nargs="+", type=int)
    parser.add_argument("--w-values", nargs="+", type=int)
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir")
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def run_command(command, cwd, log_path=None):
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if log_path is not None:
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write("COMMAND\n")
            handle.write(" ".join(shlex.quote(part) for part in command))
            handle.write("\n\nSTDOUT\n")
            handle.write(completed.stdout)
            handle.write("\nSTDERR\n")
            handle.write(completed.stderr)
    if completed.returncode != 0:
        location = "" if log_path is None else "; see {}".format(log_path)
        raise RuntimeError("command failed{}".format(location))
    return completed


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def cpu_description():
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def write_smoke_fixture(path):
    first = ("ACGT" * 50) + ("N" * 12) + ("TGCA" * 50)
    second = "GATTACA" * 20
    with path.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(">smoke_first_record\n")
        for start in range(0, len(first), 64):
            handle.write(first[start:start + 64] + "\n")
        handle.write(">ignored_second_record\n")
        handle.write(second + "\n")


def validate_request(arguments, output_dir):
    if arguments.smoke:
        forbidden = (
            arguments.datasets,
            arguments.dataset_names,
            arguments.k_values,
            arguments.w_values,
            arguments.repeats,
        )
        if any(value is not None for value in forbidden):
            raise ValueError("--smoke cannot be combined with formal grid options")
        fixture = output_dir / "smoke_fixture.fa"
        write_smoke_fixture(fixture)
        return [fixture], ["SmokeFixture"], [21], [20], 1, "functional_smoke"

    required = (
        arguments.datasets,
        arguments.dataset_names,
        arguments.k_values,
        arguments.w_values,
        arguments.repeats,
    )
    if any(value is None for value in required):
        raise ValueError("formal runs require datasets, names, k, w, and repeats")
    if len(arguments.datasets) != len(arguments.dataset_names):
        raise ValueError("dataset paths and names must have the same length")
    if arguments.repeats < 1:
        raise ValueError("repeats must be positive")
    if any(value < 1 or value > 32 for value in arguments.k_values):
        raise ValueError("every k must be in the range 1..32")
    if any(value < 1 for value in arguments.w_values):
        raise ValueError("every w must be positive")
    paths = [Path(value).expanduser().resolve() for value in arguments.datasets]
    for path in paths:
        if not path.is_file():
            raise ValueError("dataset does not exist: {}".format(path))
    return (
        paths,
        list(arguments.dataset_names),
        list(arguments.k_values),
        list(arguments.w_values),
        arguments.repeats,
        "migration_run",
    )


def compile_benchmark(repo_root, output_dir, compiler, k, w, logs):
    binary = output_dir / "bin" / "benchmark_k{}_w{}".format(k, w)
    flags = [
        "-O3",
        "-march=native",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-DK={}".format(k),
        "-DW={}".format(w),
    ]
    command = [compiler] + flags + [
        "-Iinclude",
        str(SOURCE_RELATIVE),
        "-Lbuild",
        "-Wl,-Bstatic",
        "-lkssd_array",
        "-Wl,-Bdynamic",
        "-lxxhash",
        "-lm",
        "-o",
        str(binary),
    ]
    run_command(
        command,
        repo_root,
        logs / "compile_k{}_w{}.log".format(k, w),
    )
    return binary, command, flags


def parse_benchmark_output(text, k, w):
    metadata = None
    parity = None
    results = []
    for line in text.splitlines():
        parts = line.split("\t")
        if parts[0] == "META" and len(parts) == 9:
            metadata = {
                "valid_bases": int(parts[1]),
                "ambiguous_bases_skipped": int(parts[2]),
                "valid_kmers": int(parts[3]),
                "valid_windows": int(parts[4]),
                "k": int(parts[5]),
                "w": int(parts[6]),
                "repeat": int(parts[7]),
                "xxhash_version": int(parts[8]),
            }
        elif parts[0] == "PARITY" and len(parts) == 3:
            parity = {"result": parts[1], "samples": int(parts[2])}
        elif parts[0] == "RESULT" and len(parts) == 8:
            results.append({
                "method": parts[1],
                "runtime_s": float(parts[2]),
                "throughput_windows_s": float(parts[3]),
                "valid_kmers": int(parts[4]),
                "valid_windows": int(parts[5]),
                "minimizers": int(parts[6]),
                "checksum": parts[7],
            })
    if metadata is None or parity is None:
        raise RuntimeError("benchmark output lacks metadata or parity result")
    if parity["result"] != "PASS" or parity["samples"] < 1:
        raise RuntimeError("fast/context parity did not pass")
    if metadata["k"] != k or metadata["w"] != w:
        raise RuntimeError("compiled and reported k/w values differ")
    if len(results) != len(METHODS) or {row["method"] for row in results} != set(METHODS):
        raise RuntimeError("benchmark did not emit exactly the five required methods")
    expected_kmers = metadata["valid_bases"] - k + 1
    expected_windows = expected_kmers - w + 1
    if expected_kmers < 0 or expected_windows < 0:
        raise RuntimeError("negative derived input count")
    if metadata["valid_kmers"] != expected_kmers:
        raise RuntimeError("valid k-mer count is inconsistent")
    if metadata["valid_windows"] != expected_windows:
        raise RuntimeError("valid window count is inconsistent")
    for row in results:
        if row["valid_kmers"] != expected_kmers:
            raise RuntimeError("method k-mer count is inconsistent")
        if row["valid_windows"] != expected_windows:
            raise RuntimeError("method window count is inconsistent")
        if row["minimizers"] != expected_windows:
            raise RuntimeError("historical no-dedup minimizer count is inconsistent")
        if row["runtime_s"] <= 0.0 or row["throughput_windows_s"] <= 0.0:
            raise RuntimeError("nonpositive timing result")
    return metadata, parity, results


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def mean_and_sd(values):
    if len(values) == 1:
        return values[0], 0.0
    return statistics.mean(values), statistics.stdev(values)


def summarize(raw_rows, result_status):
    groups = {}
    for row in raw_rows:
        key = (row["dataset"], row["k"], row["w"], row["method"])
        groups.setdefault(key, []).append(row)
    summary = []
    for key in sorted(groups):
        dataset, k, w, method = key
        rows = groups[key]
        runtime_mean, runtime_sd = mean_and_sd(
            [float(row["runtime_s"]) for row in rows]
        )
        throughput_mean, throughput_sd = mean_and_sd(
            [float(row["throughput_mwindows_s"]) for row in rows]
        )
        first = rows[0]
        summary.append({
            "result_status": result_status,
            "dataset": dataset,
            "k": k,
            "w": w,
            "method": method,
            "runtime_s_mean": "{:.9f}".format(runtime_mean),
            "runtime_s_sd": "{:.9f}".format(runtime_sd),
            "throughput_mwindows_s_mean": "{:.9f}".format(throughput_mean),
            "throughput_mwindows_s_sd": "{:.9f}".format(throughput_sd),
            "valid_kmers": first["valid_kmers"],
            "valid_windows": first["valid_windows"],
            "minimizers": first["minimizers"],
            "n": len(rows),
        })
    return summary


def main():
    arguments = parse_arguments()
    repo_root = Path(__file__).resolve().parents[2]
    if arguments.output_dir:
        output_dir = Path(arguments.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        prefix = "kssd-figure2-smoke-" if arguments.smoke else "kssd-figure2-run-"
        output_dir = Path(tempfile.mkdtemp(prefix=prefix))

    reserved = [
        output_dir / RAW_NAME,
        output_dir / SUMMARY_NAME,
        output_dir / "build_manifest.txt",
        output_dir / "run_manifest.txt",
    ]
    if any(path.exists() for path in reserved):
        raise RuntimeError("output directory contains reserved output files")
    logs = output_dir / "logs"
    binaries = output_dir / "bin"
    logs.mkdir(parents=True, exist_ok=True)
    binaries.mkdir(parents=True, exist_ok=True)

    datasets, names, k_values, w_values, repeats, result_status = (
        validate_request(arguments, output_dir)
    )
    compiler = os.environ.get("CC", "cc")
    make_log = logs / "build_library.log"
    run_command(["make", "build/libkssd_array.a"], repo_root, make_log)

    compiler_version = run_command([compiler, "--version"], repo_root).stdout.splitlines()[0]
    repository_commit = run_command(
        ["git", "rev-parse", "HEAD"], repo_root
    ).stdout.strip()
    source_path = repo_root / SOURCE_RELATIVE
    library_path = repo_root / "build/libkssd_array.a"
    dataset_records = []
    for path, name in zip(datasets, names):
        dataset_records.append({
            "name": name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    raw_rows = []
    compile_records = []
    executed_commands = []
    all_parity_samples = []
    for k in k_values:
        for w in w_values:
            binary, compile_command, flags = compile_benchmark(
                repo_root, output_dir, compiler, k, w, logs
            )
            compile_records.append({
                "k": k,
                "w": w,
                "binary": str(binary),
                "binary_sha256": sha256_file(binary),
                "flags": flags,
                "command": compile_command,
            })
            for dataset, dataset_name, dataset_record in zip(
                    datasets, names, dataset_records):
                for repeat in range(1, repeats + 1):
                    log_path = logs / "run_{}_k{}_w{}_repeat{}.log".format(
                        dataset_name, k, w, repeat
                    )
                    command = [
                        str(binary),
                        str(dataset),
                        str(repeat),
                        str(arguments.seed),
                    ]
                    completed = run_command(command, repo_root, log_path)
                    metadata, parity, results = parse_benchmark_output(
                        completed.stdout, k, w
                    )
                    all_parity_samples.append(parity["samples"])
                    executed_commands.append(command)
                    for result in results:
                        raw_rows.append({
                            "result_status": result_status,
                            "dataset": dataset_name,
                            "dataset_path": str(dataset),
                            "dataset_size_bytes": dataset_record["size_bytes"],
                            "dataset_sha256": dataset_record["sha256"],
                            "k": k,
                            "w": w,
                            "repeat": repeat,
                            "seed": arguments.seed,
                            "method": result["method"],
                            "runtime_s": "{:.9f}".format(result["runtime_s"]),
                            "throughput_windows_s": "{:.3f}".format(
                                result["throughput_windows_s"]
                            ),
                            "throughput_mwindows_s": "{:.9f}".format(
                                result["throughput_windows_s"] / 1000000.0
                            ),
                            "valid_bases": metadata["valid_bases"],
                            "ambiguous_bases_skipped": metadata[
                                "ambiguous_bases_skipped"
                            ],
                            "valid_kmers": result["valid_kmers"],
                            "valid_windows": result["valid_windows"],
                            "minimizers": result["minimizers"],
                            "parity_samples": parity["samples"],
                            "log_file": str(log_path),
                        })

    expected_raw_rows = len(datasets) * len(k_values) * len(w_values) * repeats * len(METHODS)
    if len(raw_rows) != expected_raw_rows:
        raise RuntimeError("unexpected raw CSV row count")
    if {row["method"] for row in raw_rows} != set(METHODS):
        raise RuntimeError("raw method set differs from the required five")
    summary_rows = summarize(raw_rows, result_status)
    expected_summary_rows = len(datasets) * len(k_values) * len(w_values) * len(METHODS)
    if len(summary_rows) != expected_summary_rows:
        raise RuntimeError("unexpected summary CSV row count")

    raw_fields = [
        "result_status", "dataset", "dataset_path", "dataset_size_bytes",
        "dataset_sha256", "k", "w", "repeat", "seed", "method",
        "runtime_s", "throughput_windows_s", "throughput_mwindows_s",
        "valid_bases", "ambiguous_bases_skipped", "valid_kmers",
        "valid_windows", "minimizers", "parity_samples", "log_file",
    ]
    summary_fields = [
        "result_status", "dataset", "k", "w", "method",
        "runtime_s_mean", "runtime_s_sd", "throughput_mwindows_s_mean",
        "throughput_mwindows_s_sd", "valid_kmers", "valid_windows",
        "minimizers", "n",
    ]
    raw_path = output_dir / RAW_NAME
    summary_path = output_dir / SUMMARY_NAME
    write_csv(raw_path, raw_rows, raw_fields)
    write_csv(summary_path, summary_rows, summary_fields)

    build_manifest = {
        "repository_commit": repository_commit,
        "source": str(SOURCE_RELATIVE),
        "source_sha256": sha256_file(source_path),
        "library": "build/libkssd_array.a",
        "library_sha256": sha256_file(library_path),
        "compiler": compiler_version,
        "compile_records": compile_records,
    }
    (output_dir / "build_manifest.txt").write_text(
        json.dumps(build_manifest, indent=2) + "\n", encoding="utf-8"
    )

    run_manifest = {
        "mode": result_status,
        "os": platform.platform(),
        "cpu": cpu_description(),
        "seed": arguments.seed,
        "datasets": dataset_records,
        "k_values": k_values,
        "w_values": w_values,
        "repeats": repeats,
        "methods": list(METHODS),
        "historical_fasta_semantics": "first record; non-ACGT symbols skipped without reset",
        "adjacent_window_deduplication": False,
        "parity": {
            "context_api": "kssd_array_map_unchecked",
            "fast_api": "kssd_array_fast_with_tables",
            "result": "PASS",
            "minimum_samples": min(all_parity_samples),
        },
        "executed_commands": executed_commands,
        "outputs": {
            "raw_csv": str(raw_path),
            "summary_csv": str(summary_path),
            "logs": str(logs),
        },
    }
    (output_dir / "run_manifest.txt").write_text(
        json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8"
    )

    plot_log = logs / "plot.log"
    plot_command = [
        "Rscript",
        "reproducibility/figure2/plot_figure2_single_thread.R",
        "--summary",
        str(summary_path),
        "--output-dir",
        str(output_dir),
    ]
    run_command(plot_command, repo_root, plot_log)
    plot_path = output_dir / "figure2_single_thread_realistic_kw.png"
    if not plot_path.is_file() or plot_path.stat().st_size == 0:
        raise RuntimeError("plotting did not produce a nonempty review PNG")

    print("OUTPUT_DIR={}".format(output_dir))
    print("FASTA={}".format(datasets[0] if arguments.smoke else "caller-supplied"))
    print("RAW_CSV={} ROWS={}".format(raw_path, len(raw_rows)))
    print("SUMMARY_CSV={} ROWS={}".format(summary_path, len(summary_rows)))
    print("BUILD_MANIFEST={}".format(output_dir / "build_manifest.txt"))
    print("RUN_MANIFEST={}".format(output_dir / "run_manifest.txt"))
    print("LOGS={}".format(logs))
    print("REVIEW_PLOT={}".format(plot_path))
    print("PARITY=PASS SAMPLES_MIN={}".format(min(all_parity_samples)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print("error: {}".format(error), file=sys.stderr)
        raise SystemExit(1)
