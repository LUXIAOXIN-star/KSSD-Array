#!/usr/bin/env python3
"""Run the deterministic Figure 4 bucket-balance experiment."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import scipy
from scipy.stats import chisquare


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "reproducibility/figure4/benchmark_bucket_balance.c"
LIBRARY = ROOT / "build/libkssd_array.a"
METHODS = ["KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "wyhash"]
RAW_COLUMNS = [
    "method", "k", "sequence_length", "bins", "repeat", "seed",
    "sequence_seed", "mapping_seed", "num_buckets", "mapped_value_count",
    "bucket_count_sum", "expected_per_bucket", "chi_square",
    "degrees_of_freedom", "p_value", "non_reject", "kssd_domain_max",
    "kssd_observed_max",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_text(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def outside_repository(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return True
    return False


def condition_seed(k: int, sequence_length: int, bins: int,
                   repeat: int, base_seed: int) -> int:
    return (base_seed + k * 1_000_000 + sequence_length // 100 +
            bins * 100 + repeat)


def parse_output(stdout: str, bins: int) -> tuple[dict[str, int], dict[str, np.ndarray]]:
    metadata: dict[str, int] = {}
    histograms: dict[str, np.ndarray] = {}
    for line in stdout.splitlines():
        fields = line.split("\t")
        if fields[0] == "META":
            for field in fields[1:]:
                key, value = field.split("=", 1)
                metadata[key] = int(value)
        elif fields[0] == "HIST" and len(fields) >= 3:
            histograms[fields[1]] = np.asarray(
                [int(value) for value in fields[2:]], dtype=np.int64)
    if list(histograms) != METHODS:
        raise RuntimeError(f"unexpected method set/order: {list(histograms)}")
    for method, counts in histograms.items():
        if len(counts) != bins:
            raise RuntimeError(
                f"{method} emitted {len(counts)} buckets instead of {bins}")
    required = {
        "K", "BINS", "SEQUENCE_LENGTH", "SEED", "SEQUENCE_SEED",
        "MAPPED_COUNT", "KSSD_DOMAIN_MAX", "KSSD_OBSERVED_MAX",
        "XXHASH_VERSION",
    }
    if set(metadata) != required:
        raise RuntimeError(f"unexpected metadata fields: {sorted(metadata)}")
    return metadata, histograms


def rows_from_output(stdout: str, *, k: int, sequence_length: int,
                     bins: int, repeat: int, seed: int,
                     alpha: float) -> list[dict[str, object]]:
    metadata, histograms = parse_output(stdout, bins)
    expected_metadata = {
        "K": k,
        "BINS": bins,
        "SEQUENCE_LENGTH": sequence_length,
        "SEED": seed,
        "SEQUENCE_SEED": seed + 1_000_003,
        "MAPPED_COUNT": sequence_length - k + 1,
    }
    for key, expected in expected_metadata.items():
        if metadata[key] != expected:
            raise RuntimeError(
                f"metadata mismatch for {key}: {metadata[key]} != {expected}")
    if metadata["KSSD_OBSERVED_MAX"] > metadata["KSSD_DOMAIN_MAX"]:
        raise RuntimeError("KSSD-Array emitted a value outside its 2k-bit domain")

    rows: list[dict[str, object]] = []
    for method in METHODS:
        counts = histograms[method]
        count_sum = int(counts.sum())
        if count_sum != metadata["MAPPED_COUNT"]:
            raise RuntimeError(
                f"bucket sum mismatch for {method}: {count_sum} != "
                f"{metadata['MAPPED_COUNT']}")
        statistic, p_value = chisquare(f_obs=counts)
        if not np.isfinite(statistic) or not np.isfinite(p_value):
            raise RuntimeError(f"non-finite statistic for {method}")
        rows.append({
            "method": method,
            "k": k,
            "sequence_length": sequence_length,
            "bins": bins,
            "repeat": repeat,
            "seed": seed,
            "sequence_seed": metadata["SEQUENCE_SEED"],
            "mapping_seed": seed,
            "num_buckets": bins,
            "mapped_value_count": metadata["MAPPED_COUNT"],
            "bucket_count_sum": count_sum,
            "expected_per_bucket": count_sum / bins,
            "chi_square": float(statistic),
            "degrees_of_freedom": bins - 1,
            "p_value": float(p_value),
            "non_reject": int(p_value > alpha),
            "kssd_domain_max": metadata["KSSD_DOMAIN_MAX"] if method == "KSSD-Array" else "",
            "kssd_observed_max": metadata["KSSD_OBSERVED_MAX"] if method == "KSSD-Array" else "",
        })
    return rows


def run_condition(binary: Path, log_dir: Path, condition: tuple[int, int, int, int, int],
                  alpha: float, timeout: float) -> tuple[tuple[int, int, int, int], list[dict[str, object]]]:
    k, sequence_length, bins, repeat, seed = condition
    command = [str(binary), str(k), str(bins), str(sequence_length), str(seed)]
    completed = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True,
        timeout=timeout, check=False,
    )
    log_path = log_dir / (
        f"k{k}_n{sequence_length}_b{bins}_r{repeat:03d}.log")
    log_path.write_text(
        f"COMMAND={command_text(command)}\n"
        f"RETURN_CODE={completed.returncode}\n"
        f"STDOUT_BEGIN\n{completed.stdout}STDOUT_END\n"
        f"STDERR_BEGIN\n{completed.stderr}STDERR_END\n",
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"condition failed ({k}, {sequence_length}, {bins}, {repeat}); "
            f"see {log_path}")
    rows = rows_from_output(
        completed.stdout, k=k, sequence_length=sequence_length,
        bins=bins, repeat=repeat, seed=seed, alpha=alpha,
    )
    return (k, sequence_length, bins, repeat), rows


def write_summary(raw: pd.DataFrame, path: Path) -> pd.DataFrame:
    summary = (
        raw.groupby(["sequence_length", "bins", "k", "method"], sort=True)
        .agg(
            repeats=("repeat", "count"),
            non_reject_count=("non_reject", "sum"),
            non_rejection_rate=("non_reject", "mean"),
            p_value_mean=("p_value", "mean"),
            p_value_std=("p_value", "std"),
            chi_square_mean=("chi_square", "mean"),
            chi_square_std=("chi_square", "std"),
        )
        .reset_index()
    )
    summary["non_rejection_rate_percent"] = (
        100.0 * summary["non_rejection_rate"])
    columns = [
        "sequence_length", "bins", "k", "method", "repeats",
        "non_reject_count", "non_rejection_rate",
        "non_rejection_rate_percent", "p_value_mean", "p_value_std",
        "chi_square_mean", "chi_square_std",
    ]
    summary = summary[columns]
    summary.to_csv(path, index=False)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k-values", nargs="+", type=int,
                        default=list(range(6, 15)))
    parser.add_argument("--sequence-lengths", nargs="+", type=int,
                        default=[4_000_000, 8_000_000])
    parser.add_argument("--bins", nargs="+", type=int,
                        default=[101, 199, 499])
    parser.add_argument("--repeats", type=int, default=100)
    parser.add_argument("--base-seed", type=int, default=20_260_708)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()

    if args.preflight:
        args.k_values = [9]
        args.sequence_lengths = [100_000]
        args.bins = [101]
        args.repeats = 1
    if args.repeats <= 0 or args.jobs <= 0 or not 0.0 < args.alpha < 1.0:
        parser.error("repeats and jobs must be positive and alpha must be in (0, 1)")
    if not all(1 <= value <= 32 for value in args.k_values):
        parser.error("all k values must be in 1..32")
    if not all(value > 0 for value in args.bins):
        parser.error("all bin counts must be positive")
    if not all(length >= max(args.k_values) for length in args.sequence_lengths):
        parser.error("each sequence length must be at least the largest k")

    output_dir = args.output_dir.resolve()
    if not outside_repository(output_dir):
        parser.error("generated output directory must be outside the repository")
    log_dir = output_dir / "logs"
    bin_dir = output_dir / "bin"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(exist_ok=True)
    bin_dir.mkdir(exist_ok=True)
    raw_path = output_dir / "figure4_bucket_balance_raw.csv"
    summary_path = output_dir / "figure4_bucket_balance_summary.csv"
    binary = bin_dir / "benchmark_bucket_balance"

    subprocess.run(["make", "build/libkssd_array.a"], cwd=ROOT, check=True)
    compile_command = [
        args.cc, "-Iinclude", "-O3", "-march=native", "-std=c11",
        "-Wall", "-Wextra", "-Wpedantic", str(SOURCE.relative_to(ROOT)),
        "-Lbuild", "-Wl,-Bstatic", "-lkssd_array", "-Wl,-Bdynamic",
        "-lxxhash", "-lm", "-o", str(binary),
    ]
    compile_result = subprocess.run(
        compile_command, cwd=ROOT, text=True, capture_output=True, check=False)
    if compile_result.returncode != 0:
        sys.stderr.write(compile_result.stdout + compile_result.stderr)
        return compile_result.returncode

    compiler_version = subprocess.run(
        [args.cc, "--version"], text=True, capture_output=True,
        check=True).stdout.splitlines()[0]
    build_manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            capture_output=True, check=True).stdout.strip(),
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": sha256(SOURCE),
        "library": "build/libkssd_array.a",
        "library_sha256": sha256(LIBRARY),
        "compiler": compiler_version,
        "compile_command": command_text(compile_command),
        "binary_sha256": sha256(binary),
    }
    (output_dir / "build_manifest.txt").write_text(
        json.dumps(build_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    conditions = []
    for k in args.k_values:
        for sequence_length in args.sequence_lengths:
            for bins in args.bins:
                for repeat in range(1, args.repeats + 1):
                    seed = condition_seed(
                        k, sequence_length, bins, repeat, args.base_seed)
                    conditions.append((k, sequence_length, bins, repeat, seed))
    commands = [command_text([
        str(binary), str(k), str(bins), str(sequence_length), str(seed)])
        for k, sequence_length, bins, repeat, seed in conditions]

    manifest = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "os": platform.platform(),
        "cpu": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
        "python": sys.version.splitlines()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "statistical_implementation": "scipy.stats.chisquare upper-tail p-value",
        "sequence_rng": "SplitMix64; low two bits per base",
        "base_seed": args.base_seed,
        "seed_formula": "base + k*1000000 + sequence_length//100 + bins*100 + repeat",
        "sequence_seed_offset": 1_000_003,
        "kssd_rng": "KSSD_ARRAY_RNG_SPLITMIX64",
        "kssd_seed": "condition seed",
        "xxh3_seed": "condition seed",
        "xxh64_seed": "condition seed",
        "murmurhash3_seed": "low 32 bits of condition seed",
        "wyhash_seed": "condition-seeded secret; input seed zero",
        "alpha": args.alpha,
        "k_values": args.k_values,
        "sequence_lengths": args.sequence_lengths,
        "bins": args.bins,
        "repeats": args.repeats,
        "methods": METHODS,
        "jobs": args.jobs,
        "condition_count": len(conditions),
        "expected_raw_rows": len(conditions) * len(METHODS),
        "expected_summary_rows": (
            len(args.k_values) * len(args.sequence_lengths) *
            len(args.bins) * len(METHODS)),
        "commands": commands,
    }
    manifest_path = output_dir / "run_manifest.txt"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    completed_keys: set[tuple[int, int, int, int]] = set()
    raw_exists = raw_path.exists() and raw_path.stat().st_size > 0
    if raw_exists:
        existing = pd.read_csv(raw_path)
        for key, group in existing.groupby(
                ["k", "sequence_length", "bins", "repeat"]):
            if set(group["method"]) == set(METHODS) and len(group) == len(METHODS):
                completed_keys.add(tuple(int(value) for value in key))
    pending = [condition for condition in conditions
               if condition[:4] not in completed_keys]
    print(f"conditions={len(conditions)} completed={len(completed_keys)} "
          f"pending={len(pending)} jobs={args.jobs}")

    started = time.monotonic()
    write_header = not raw_exists
    completed_now = 0
    with raw_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_COLUMNS)
        if write_header:
            writer.writeheader()
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = {
                executor.submit(
                    run_condition, binary, log_dir, condition,
                    args.alpha, args.timeout): condition
                for condition in pending
            }
            for future in as_completed(futures):
                _, rows = future.result()
                writer.writerows(rows)
                handle.flush()
                completed_now += 1
                if completed_now % 50 == 0 or completed_now == len(pending):
                    print(f"completed {completed_now}/{len(pending)} pending conditions")

    raw = pd.read_csv(raw_path)
    raw = raw.sort_values(
        ["k", "sequence_length", "bins", "repeat", "method"],
        kind="stable").reset_index(drop=True)
    duplicated = raw.duplicated(
        ["method", "k", "sequence_length", "bins", "repeat"]).sum()
    if duplicated:
        raise RuntimeError(f"raw output contains {duplicated} duplicate keys")
    expected_raw_rows = len(conditions) * len(METHODS)
    if len(raw) != expected_raw_rows:
        raise RuntimeError(f"raw rows {len(raw)} != {expected_raw_rows}")
    group_sizes = raw.groupby(
        ["k", "sequence_length", "bins", "repeat"]).size()
    if not (group_sizes == len(METHODS)).all():
        raise RuntimeError("one or more conditions do not contain five methods")
    raw.to_csv(raw_path, index=False)
    summary = write_summary(raw, summary_path)
    expected_summary_rows = (
        len(args.k_values) * len(args.sequence_lengths) *
        len(args.bins) * len(METHODS))
    if len(summary) != expected_summary_rows:
        raise RuntimeError(
            f"summary rows {len(summary)} != {expected_summary_rows}")
    if not (summary["repeats"] == args.repeats).all():
        raise RuntimeError("one or more summary groups have the wrong repeat count")

    manifest.update({
        "status": "complete",
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - started,
        "raw_rows": len(raw),
        "summary_rows": len(summary),
        "raw_sha256": sha256(raw_path),
        "summary_sha256": sha256(summary_path),
        "observed_methods": sorted(raw["method"].unique()),
    })
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"raw={raw_path} rows={len(raw)}")
    print(f"summary={summary_path} rows={len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
