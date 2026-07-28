#!/usr/bin/env python3
"""Build and run the formal single-thread Minimap2 indexing comparison."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
INTEGRATION_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG = REPO_ROOT / "reproducibility/minimap2/indexing/config.json"
FIXTURE = INTEGRATION_DIR / "fixtures/reference.fa"
BUILD_HELPER = INTEGRATION_DIR / "build_minimap2.sh"
SUMMARIZER = SCRIPT_DIR / "summarize_supplementary_indexing.py"
PLOTTER = REPO_ROOT / "reproducibility/minimap2/indexing/plot_supplementary_figure_s1.py"
METHODS = ("Original Minimap2", "KSSD-Array")
RAW_FIELDS = (
    "dataset_key", "dataset", "accession", "version", "reference_path",
    "reference_size_bytes", "reference_sha256", "sequence_count",
    "total_bases", "method", "repeat", "threads", "k", "w", "hpc",
    "command", "exit_status", "wall_time_s", "user_time_s",
    "system_time_s", "cpu_time_s", "peak_rss_kb", "peak_rss_gib",
    "distinct_minimizers", "singleton_percent", "average_occurrences",
    "average_spacing", "index_path", "index_size_bytes", "index_sha256",
    "index_magic_hex", "stdout_path", "stderr_path", "system_snapshot_path",
    "executable_path", "executable_sha256", "load_average_1m",
    "memory_available_bytes", "output_free_bytes",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--upstream-source", required=True)
    parser.add_argument("--kssd-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--dataset", action="append", default=[],
                        metavar="KEY=PATH")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args()


def run(command: list[str], cwd: Path | None = None,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command, cwd=None if cwd is None else str(cwd), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            "command failed: {}\n{}\n{}".format(
                shlex.join(command), completed.stdout, completed.stderr,
            )
        )
    return completed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fasta_statistics(path: Path, compressed: bool) -> tuple[int, int]:
    opener = gzip.open if compressed else open
    sequence_count = 0
    total_bases = 0
    with opener(path, "rb") as handle:
        for line in handle:
            if line.startswith(b">"):
                sequence_count += 1
            else:
                total_bases += len(line.strip())
    return sequence_count, total_bases


def parse_overrides(values: list[str]) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--dataset must use KEY=PATH")
        key, raw_path = value.split("=", 1)
        if not key or not raw_path or key in overrides:
            raise ValueError("invalid or duplicate dataset override: " + value)
        overrides[key] = Path(raw_path).expanduser().resolve()
    return overrides


def candidate_paths(dataset: dict[str, object], overrides: dict[str, Path],
                    data_root: str | None) -> list[Path]:
    key = str(dataset["key"])
    relative = Path(str(dataset["relative_path"]))
    filename = Path(str(dataset["filename"]))
    candidates: list[Path] = []
    if key in overrides:
        candidates.append(overrides[key])
    if data_root:
        root = Path(data_root).expanduser().resolve()
        candidates.extend((root / relative, root / filename))
    external = REPO_ROOT / "reproducibility/data/external"
    candidates.extend((external / relative, external / filename))
    return candidates


def resolve_datasets(config: dict[str, object], overrides: dict[str, Path]) -> list[dict[str, object]]:
    configured = list(config["datasets"])
    known = {str(item["key"]) for item in configured}
    unknown = set(overrides) - known
    if unknown:
        raise ValueError("unknown dataset override keys: " + ", ".join(sorted(unknown)))
    resolved: list[dict[str, object]] = []
    for source in configured:
        dataset = dict(source)
        candidates = candidate_paths(dataset, overrides, os.environ.get("KSSD_DATA_DIR"))
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            raise FileNotFoundError(
                "unable to resolve {} from explicit path, KSSD_DATA_DIR, or reproducibility/data/external".format(
                    dataset["key"]
                )
            )
        size = path.stat().st_size
        checksum = sha256_file(path)
        compressed = str(dataset["compression"]) == "gzip"
        sequence_count, total_bases = fasta_statistics(path, compressed)
        observed = (size, checksum, sequence_count, total_bases)
        expected = (
            int(dataset["size_bytes"]), str(dataset["sha256"]),
            int(dataset["sequence_count"]), int(dataset["total_bases"]),
        )
        if observed != expected:
            raise RuntimeError(
                "dataset identity mismatch for {}: expected {}, observed {}".format(
                    dataset["key"], expected, observed
                )
            )
        dataset["resolved_path"] = str(path)
        resolved.append(dataset)
    return resolved


def build_executables(output: Path, upstream_source: str, kssd_root: Path,
                      jobs: int) -> tuple[dict[str, Path], dict[str, str]]:
    builds = output / "builds"
    builds.mkdir()
    executables: dict[str, Path] = {}
    build_logs: dict[str, str] = {}
    for method, mode in (("Original Minimap2", "original"),
                         ("KSSD-Array", "integrated")):
        target = builds / mode
        command = [str(BUILD_HELPER), mode, upstream_source, str(target)]
        if mode == "integrated":
            command.append(str(kssd_root))
        environment = os.environ.copy()
        environment["JOBS"] = str(jobs)
        completed = subprocess.run(
            command, cwd=str(REPO_ROOT), env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )
        log_path = output / "logs" / ("build-" + mode + ".log")
        log_path.write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError("build failed; see " + str(log_path))
        executable = target / "source/minimap2"
        if not executable.is_file():
            raise RuntimeError("missing built executable: " + str(executable))
        executables[method] = executable
        build_logs[method] = str(log_path)
    return executables, build_logs


def command_output(command: list[str]) -> str:
    return run(command).stdout.strip()


def write_build_manifest(path: Path, config: dict[str, object],
                         kssd_root: Path, executables: dict[str, Path],
                         build_logs: dict[str, str]) -> dict[str, str]:
    library = kssd_root / "build/libkssd_array.a"
    patch = kssd_root / str(config["patch"])
    repo_commit = command_output(["git", "-C", str(kssd_root), "rev-parse", "HEAD"])
    versions = {method: command_output([str(exe), "--version"])
                for method, exe in executables.items()}
    hashes = {method: sha256_file(exe) for method, exe in executables.items()}
    ldd = {method: command_output(["ldd", str(exe)])
           for method, exe in executables.items()}
    lines = [
        "UPSTREAM_VERSION=" + str(config["upstream_version"]),
        "UPSTREAM_COMMIT=" + str(config["upstream_commit"]),
        "KSSD_REPOSITORY_COMMIT=" + repo_commit,
        "PATCH_PATH=" + str(patch),
        "PATCH_SHA256=" + sha256_file(patch),
        "LIBKSSD_ARRAY_PATH=" + str(library),
        "LIBKSSD_ARRAY_SHA256=" + sha256_file(library),
        "COMPILER_VERSION=" + command_output(["cc", "--version"]).splitlines()[0],
        "BUILD_FLAGS=-g -Wall -O2 -Wc++-compat",
    ]
    for method in METHODS:
        token = "ORIGINAL" if method == "Original Minimap2" else "INTEGRATED"
        lines.extend((
            token + "_VERSION=" + versions[method],
            token + "_EXECUTABLE=" + str(executables[method]),
            token + "_EXECUTABLE_SHA256=" + hashes[method],
            token + "_BUILD_LOG=" + build_logs[method],
            token + "_LDD_BEGIN",
            ldd[method],
            token + "_LDD_END",
        ))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hashes


def memory_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return 0


def swap_counters() -> tuple[int, int]:
    values = {}
    for line in Path("/proc/vmstat").read_text(encoding="ascii").splitlines():
        key, value = line.split()
        if key in ("pswpin", "pswpout"):
            values[key] = int(value)
    return values.get("pswpin", 0), values.get("pswpout", 0)


def run_optional(command: list[str]) -> str:
    completed = run(command, check=False)
    return completed.stdout + completed.stderr


def system_preflight(path: Path, output: Path, inputs: list[Path],
                     config: dict[str, object], formal: bool) -> None:
    before_swap = swap_counters()
    time.sleep(1)
    after_swap = swap_counters()
    swap_delta = tuple(after - before for before, after in zip(before_swap, after_swap))
    memory = memory_available_bytes()
    disk = shutil.disk_usage(output).free
    process_text = run_optional([
        "ps", "-eo", "pid,pcpu,pmem,comm,args", "--sort=-pcpu",
    ])
    high_cpu_benchmark = False
    for line in process_text.splitlines()[1:]:
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        try:
            process_id = int(parts[0])
            process_cpu = float(parts[1])
        except ValueError:
            continue
        if process_id in (os.getpid(), os.getppid()):
            continue
        lowered = parts[4].lower()
        if process_cpu >= 50.0 and ("minimap2" in lowered or "benchmark" in lowered):
            high_cpu_benchmark = True
    governor_lines = []
    for governor in sorted(Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_governor")):
        try:
            governor_lines.append(str(governor) + "=" + governor.read_text().strip())
        except OSError:
            pass
    cpu_model = platform.processor() or "unknown"
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    reasons = []
    if swap_delta != (0, 0):
        reasons.append("active swap traffic")
    if formal and memory < int(config["minimum_available_memory_bytes"]):
        reasons.append("available memory below protocol-specific requirement")
    if formal and disk < int(config["minimum_output_free_bytes"]):
        reasons.append("free output space below protocol-specific requirement")
    if high_cpu_benchmark:
        reasons.append("another high-CPU benchmark process is active")
    decision = "PASS" if not reasons else "STOP: " + "; ".join(reasons)
    input_filesystems = []
    for input_path in inputs:
        input_filesystems.append(
            "PATH={}\n{}".format(
                input_path, run_optional(["findmnt", "-T", str(input_path)]).strip()
            )
        )
    sections = [
        "DECISION=" + decision,
        "CPU_MODEL=" + cpu_model,
        "LOADAVG=" + Path("/proc/loadavg").read_text().strip(),
        "MEMORY_AVAILABLE_BYTES=" + str(memory),
        "OUTPUT_FREE_BYTES=" + str(disk),
        "SWAP_COUNTER_DELTA=" + str(swap_delta),
        "UPTIME\n" + run_optional(["uptime"]),
        "FREE\n" + run_optional(["free", "-h"]),
        "DISK\n" + run_optional(["df", "-h", str(output)]),
        "FILESYSTEM\n" + run_optional(["findmnt", "-T", str(output)]),
        "INPUT_FILESYSTEMS\n" + "\n\n".join(input_filesystems),
        "CPU_GOVERNORS\n" + ("\n".join(governor_lines) or "unavailable"),
        "ACTIVE_PROCESSES\n" + "\n".join(process_text.splitlines()[:20]),
    ]
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    if reasons:
        raise RuntimeError("system preflight failed: " + "; ".join(reasons))


def parse_elapsed(value: str) -> float:
    parts = value.strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(value)


def parse_stderr(text: str) -> dict[str, float | int]:
    fields: dict[str, float | int] = {}
    for line in text.splitlines():
        if "User time (seconds):" in line:
            fields["user_time_s"] = float(line.rsplit(":", 1)[1])
        elif "System time (seconds):" in line:
            fields["system_time_s"] = float(line.rsplit(":", 1)[1])
        elif "Elapsed (wall clock) time" in line:
            fields["wall_time_s"] = parse_elapsed(line.split("):", 1)[1])
        elif "Maximum resident set size (kbytes):" in line:
            fields["peak_rss_kb"] = int(line.rsplit(":", 1)[1])
    stats_pattern = re.compile(
        r"distinct minimizers:\s+(\d+)\s+\(([0-9.]+)% are singletons\); "
        r"average occurrences:\s+([0-9.]+); average spacing:\s+([0-9.]+); "
        r"total length:\s+(\d+)"
    )
    index_pattern = re.compile(
        r"kmer size:\s+(\d+); skip:\s+(\d+); is_hpc:\s+(\d+); #seq:\s+(\d+)"
    )
    for line in text.splitlines():
        match = stats_pattern.search(line)
        if match:
            fields.update({
                "distinct_minimizers": int(match.group(1)),
                "singleton_percent": float(match.group(2)),
                "average_occurrences": float(match.group(3)),
                "average_spacing": float(match.group(4)),
                "reported_total_bases": int(match.group(5)),
            })
        match = index_pattern.search(line)
        if match:
            fields.update({
                "reported_k": int(match.group(1)),
                "reported_w": int(match.group(2)),
                "reported_hpc": int(match.group(3)),
                "reported_sequence_count": int(match.group(4)),
            })
    required = {
        "wall_time_s", "user_time_s", "system_time_s", "peak_rss_kb",
        "distinct_minimizers", "singleton_percent", "average_occurrences",
        "average_spacing", "reported_total_bases", "reported_k",
        "reported_w", "reported_hpc", "reported_sequence_count",
    }
    missing = required - set(fields)
    if missing:
        raise RuntimeError("missing parsed log fields: " + ", ".join(sorted(missing)))
    return fields


def snapshot(path: Path, output: Path) -> tuple[float, int, int]:
    load = float(Path("/proc/loadavg").read_text().split()[0])
    memory = memory_available_bytes()
    disk = shutil.disk_usage(output).free
    text = "\n".join((
        "LOADAVG=" + Path("/proc/loadavg").read_text().strip(),
        "MEMORY_AVAILABLE_BYTES=" + str(memory),
        "OUTPUT_FREE_BYTES=" + str(disk),
        run_optional(["free", "-h"]),
        run_optional(["df", "-h", str(output)]),
    ))
    path.write_text(text, encoding="utf-8")
    return load, memory, disk


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def measure(output: Path, dataset: dict[str, object], method: str, repeat: int,
            executable: Path, executable_hash: str, config: dict[str, object]) -> dict[str, object]:
    method_token = "original" if method == "Original Minimap2" else "kssd-array"
    stem = "{}-{}-rep{}".format(dataset["key"], method_token, repeat)
    index = output / "indexes" / (str(dataset["key"]) + ".mmi")
    stdout_path = output / "logs" / (stem + ".stdout")
    stderr_path = output / "logs" / (stem + ".stderr")
    snapshot_path = output / "logs" / (stem + ".system.txt")
    for target in (stdout_path, stderr_path, snapshot_path):
        if target.exists():
            raise FileExistsError("refusing to reuse output: " + str(target))
    load, memory, disk = snapshot(snapshot_path, output)
    command = [
        str(config["time_program"]), *[str(item) for item in config["time_arguments"]],
        str(executable), "-t", "1", "-d", str(index), str(dataset["resolved_path"]),
    ]
    print("RUN " + stem + ": " + shlex.join(command), flush=True)
    completed = subprocess.run(command, cwd=str(output), text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               check=False)
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError("indexing failed; see " + str(stderr_path))
    if not index.is_file() or index.stat().st_size == 0:
        raise RuntimeError("empty index: " + str(index))
    fields = parse_stderr(completed.stderr)
    expected_stats = (
        int(config["k"]), int(config["w"]), int(bool(config["hpc"])),
        int(dataset["sequence_count"]), int(dataset["total_bases"]),
    )
    observed_stats = (
        fields["reported_k"], fields["reported_w"], fields["reported_hpc"],
        fields["reported_sequence_count"], fields["reported_total_bases"],
    )
    if observed_stats != expected_stats:
        raise RuntimeError(
            "reported index parameters or dataset totals changed: expected {}, observed {}".format(
                expected_stats, observed_stats
            )
        )
    user_time = float(fields["user_time_s"])
    system_time = float(fields["system_time_s"])
    peak_kb = int(fields["peak_rss_kb"])
    with index.open("rb") as handle:
        magic = handle.read(4).hex()
    return {
        "dataset_key": dataset["key"],
        "dataset": dataset["manuscript_label"],
        "accession": dataset["accession"],
        "version": dataset["version"],
        "reference_path": dataset["resolved_path"],
        "reference_size_bytes": dataset["size_bytes"],
        "reference_sha256": dataset["sha256"],
        "sequence_count": dataset["sequence_count"],
        "total_bases": dataset["total_bases"],
        "method": method,
        "repeat": repeat,
        "threads": config["threads"],
        "k": config["k"],
        "w": config["w"],
        "hpc": int(bool(config["hpc"])),
        "command": shlex.join(command),
        "exit_status": completed.returncode,
        "wall_time_s": fields["wall_time_s"],
        "user_time_s": user_time,
        "system_time_s": system_time,
        "cpu_time_s": user_time + system_time,
        "peak_rss_kb": peak_kb,
        "peak_rss_gib": peak_kb / 1024 / 1024,
        "distinct_minimizers": fields["distinct_minimizers"],
        "singleton_percent": fields["singleton_percent"],
        "average_occurrences": fields["average_occurrences"],
        "average_spacing": fields["average_spacing"],
        "index_path": str(index),
        "index_size_bytes": index.stat().st_size,
        "index_sha256": sha256_file(index),
        "index_magic_hex": magic,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "system_snapshot_path": str(snapshot_path),
        "executable_path": str(executable),
        "executable_sha256": executable_hash,
        "load_average_1m": load,
        "memory_available_bytes": memory,
        "output_free_bytes": disk,
    }


def preflight_dataset() -> dict[str, object]:
    checksum = sha256_file(FIXTURE)
    count, bases = fasta_statistics(FIXTURE, False)
    return {
        "key": "Fixture",
        "manuscript_label": "Phase 5A fixture",
        "accession": "synthetic-fixture",
        "version": "phase5a",
        "resolved_path": str(FIXTURE),
        "size_bytes": FIXTURE.stat().st_size,
        "sha256": checksum,
        "sequence_count": count,
        "total_bases": bases,
    }


def write_run_manifest(path: Path, config: dict[str, object],
                       datasets: list[dict[str, object]], mode: str,
                       output: Path) -> None:
    lines = [
        "MODE=" + mode,
        "OUTPUT_DIRECTORY=" + str(output),
        "THREADS=" + str(config["threads"]),
        "REPEATS=" + ("1" if mode == "preflight" else str(config["repeats"])),
        "K=" + str(config["k"]),
        "W=" + str(config["w"]),
        "HPC=" + str(int(bool(config["hpc"]))),
        "COOLDOWN_SECONDS=" + ("0" if mode == "preflight" else str(config["cooldown_seconds"])),
        "CACHE_HANDLING=no_explicit_flush",
        "WARMUP=none",
    ]
    for dataset in datasets:
        token = str(dataset["key"]).upper()
        for key in ("resolved_path", "size_bytes", "sha256", "sequence_count",
                    "total_bases", "accession", "version"):
            lines.append(token + "_" + key.upper() + "=" + str(dataset[key]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.jobs < 1:
        raise ValueError("--jobs must be positive")
    output = args.output_dir.expanduser().resolve()
    if output.exists():
        raise FileExistsError("output directory already exists: " + str(output))
    output.mkdir(parents=True)
    (output / "logs").mkdir()
    (output / "indexes").mkdir()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if int(config["threads"]) != 1 or int(config["repeats"]) != 3:
        raise RuntimeError("the pinned protocol requires one thread and three repeats")
    kssd_root = args.kssd_root.expanduser().resolve()
    executables, build_logs = build_executables(
        output, args.upstream_source, kssd_root, args.jobs,
    )
    executable_hashes = write_build_manifest(
        output / "build_manifest.txt", config, kssd_root, executables, build_logs,
    )
    if args.preflight:
        datasets = [preflight_dataset()]
        mode = "preflight"
    else:
        datasets = resolve_datasets(config, parse_overrides(args.dataset))
        mode = "formal"
    write_run_manifest(output / "run_manifest.txt", config, datasets, mode, output)
    input_paths = [Path(str(dataset["resolved_path"])) for dataset in datasets]
    system_preflight(
        output / "system_preflight.txt", output, input_paths,
        config, not args.preflight,
    )
    raw_path = output / "supplementary_indexing_raw.csv"
    rows: list[dict[str, object]] = []
    if args.preflight:
        dataset = datasets[0]
        for method in METHODS:
            rows.append(measure(output, dataset, method, 1, executables[method],
                                executable_hashes[method], config))
            write_csv(raw_path, rows)
    else:
        repeats = int(config["repeats"])
        run_order = list(config["run_order"])
        for dataset in datasets:
            for repeat in range(1, repeats + 1):
                order = list(run_order[repeat - 1])
                if set(order) != set(METHODS):
                    raise RuntimeError("invalid configured method order")
                for method in order:
                    rows.append(measure(
                        output, dataset, method, repeat, executables[method],
                        executable_hashes[method], config,
                    ))
                    write_csv(raw_path, rows)
                    time.sleep(int(config["cooldown_seconds"]))
    summarize_command = [
        sys.executable, str(SUMMARIZER), "--raw", str(raw_path),
        "--output-dir", str(output),
    ]
    if args.preflight:
        summarize_command.append("--preflight")
    run(summarize_command, cwd=REPO_ROOT)
    plot_command = [
        sys.executable, str(PLOTTER), "--summary",
        str(output / "supplementary_indexing_summary.csv"),
        "--output-dir", str(output),
    ]
    if args.preflight:
        plot_command.append("--preflight")
    run(plot_command, cwd=REPO_ROOT)
    print("RAW=" + str(raw_path))
    print("ROWS=" + str(len(rows)))
    print("OUTPUT_DIRECTORY=" + str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
