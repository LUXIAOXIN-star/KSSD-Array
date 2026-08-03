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
from datetime import datetime


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
    "total_bases", "method", "phase", "repeat", "order_position",
    "threads", "k", "w", "hpc", "command", "exit_status",
    "wall_time_s", "time_v_wall_time_s", "user_time_s",
    "system_time_s", "cpu_time_s", "peak_rss_kb", "peak_rss_gib",
    "distinct_minimizers", "singleton_percent", "average_occurrences",
    "average_spacing", "distinct_minimizer_density_per_base",
    "minimizer_occurrence_density_per_base", "index_path",
    "index_size_bytes", "index_sha256", "index_magic_hex",
    "index_removed_after_capture", "stdout_path", "stderr_path",
    "system_snapshot_path",
    "executable_path", "executable_sha256", "load_average_1m",
    "memory_available_bytes", "output_free_bytes", "swap_in_delta",
    "swap_out_delta", "selected_cpu",
)


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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
    parser.add_argument("--resume", action="store_true",
                        help="resume an interrupted controlled run in-place")
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


def load_executables(output: Path) -> tuple[dict[str, Path], dict[str, str]]:
    executables = {
        "Original Minimap2": output / "builds/original/source/minimap2",
        "KSSD-Array": output / "builds/integrated/source/minimap2",
    }
    with (output / "executable_sha256.tsv").open(
            encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    recorded = {row["method"]: row["sha256"] for row in rows}
    if set(recorded) != set(METHODS):
        raise RuntimeError("resume executable manifest is incomplete")
    for method, executable in executables.items():
        if (not executable.is_file() or
                sha256_file(executable) != recorded[method]):
            raise RuntimeError("resume executable identity mismatch: " + method)
    return executables, recorded


def command_output(command: list[str]) -> str:
    return run(command).stdout.strip()


def write_build_manifest(path: Path, config: dict[str, object],
                         kssd_root: Path, executables: dict[str, Path],
                         build_logs: dict[str, str]) -> dict[str, str]:
    library = kssd_root / "build/libkssd_array.a"
    patch = kssd_root / str(config["patch"])
    repo_commit = command_output(["git", "-C", str(kssd_root), "rev-parse", "HEAD"])
    repo_status = run([
        "git", "-C", str(kssd_root), "status", "--short",
    ]).stdout.rstrip()
    versions = {method: command_output([str(exe), "--version"])
                for method, exe in executables.items()}
    hashes = {method: sha256_file(exe) for method, exe in executables.items()}
    ldd = {method: command_output(["ldd", str(exe)])
           for method, exe in executables.items()}
    lines = [
        "UPSTREAM_VERSION=" + str(config["upstream_version"]),
        "UPSTREAM_COMMIT=" + str(config["upstream_commit"]),
        "KSSD_REPOSITORY_COMMIT=" + repo_commit,
        "KSSD_REPOSITORY_STATUS_BEGIN",
        repo_status,
        "KSSD_REPOSITORY_STATUS_END",
        "PATCH_PATH=" + str(patch),
        "PATCH_SHA256=" + sha256_file(patch),
        "LIBKSSD_ARRAY_PATH=" + str(library),
        "LIBKSSD_ARRAY_SHA256=" + sha256_file(library),
        "INLINE_HEADER_SHA256=" + sha256_file(
            kssd_root / "include/kssd_array_inline.h"),
        "KSSD_CORE_SHA256=" + sha256_file(kssd_root / "src/kssd_array.c"),
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
        if process_cpu >= 20.0 and (
                "minimap2" in lowered or "benchmark" in lowered or
                "nthash" in lowered):
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
    load_1m = float(Path("/proc/loadavg").read_text().split()[0])
    if formal and load_1m > float(config["maximum_load_average_1m"]):
        reasons.append("one-minute load exceeds configured threshold")
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
        "SELECTED_CPU=" + str(config["selected_cpu"]),
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
        "VMSTAT_10S\n" + run_optional(["vmstat", "1", "10"]),
        "CPU_TOPOLOGY\n" + run_optional([
            "lscpu", "-e=CPU,CORE,SOCKET,NODE,ONLINE",
        ]),
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


def parse_stderr(text: str, require_timing: bool = True) -> dict[str, float | int]:
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
        "distinct_minimizers", "singleton_percent", "average_occurrences",
        "average_spacing", "reported_total_bases", "reported_k",
        "reported_w", "reported_hpc", "reported_sequence_count",
    }
    if require_timing:
        required.update({
            "wall_time_s", "user_time_s", "system_time_s", "peak_rss_kb",
        })
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
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def atomic_text(path: Path, value: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def measure(output: Path, dataset: dict[str, object], method: str, repeat: int,
            order_position: int, executable: Path, executable_hash: str,
            config: dict[str, object], measured: bool,
            enforce_environment_gate: bool,
            attempt: int = 1) -> dict[str, object]:
    method_token = "original" if method == "Original Minimap2" else "kssd-array"
    phase = "rep{}".format(repeat) if measured else "warmup"
    stem_base = "{}-{}-{}".format(dataset["key"], method_token, phase)
    stem = stem_base if attempt == 1 else stem_base + "-retry{}".format(attempt)
    index = output / "indexes" / (stem + ".mmi")
    stdout_path = output / "logs" / (stem + ".stdout")
    stderr_path = output / "logs" / (stem + ".stderr")
    snapshot_path = output / "logs" / (stem + ".system.txt")
    if any(target.exists() for target in
           (index, stdout_path, stderr_path, snapshot_path)):
        return measure(output, dataset, method, repeat, order_position,
                       executable, executable_hash, config, measured,
                       enforce_environment_gate,
                       attempt + 1)
    swap_gate_before = swap_counters()
    time.sleep(1)
    swap_gate_after = swap_counters()
    load, memory, disk = snapshot(snapshot_path, output)
    gate_swap = tuple(after - before for before, after in
                      zip(swap_gate_before, swap_gate_after))
    gate_reasons = []
    if (enforce_environment_gate and
            load > float(config["maximum_load_average_1m"])):
        gate_reasons.append("one-minute load exceeds configured threshold")
    if enforce_environment_gate and gate_swap != (0, 0):
        gate_reasons.append("active swap traffic before run")
    if (enforce_environment_gate and
            memory < int(config["minimum_available_memory_bytes"])):
        gate_reasons.append("available memory below configured threshold")
    if (enforce_environment_gate and
            disk < int(config["minimum_output_free_bytes"])):
        gate_reasons.append("free output space below configured threshold")
    if gate_reasons:
        atomic_text(snapshot_path, snapshot_path.read_text(encoding="utf-8") +
                    "\nDECISION=STOP: " + "; ".join(gate_reasons) + "\n")
        if attempt >= int(config["maximum_environment_retries"]):
            raise RuntimeError("per-run low-load gate failed: " +
                               "; ".join(gate_reasons))
        print("RETRY {} gate rejected: {}".format(
            stem, "; ".join(gate_reasons)), flush=True)
        time.sleep(int(config["environment_retry_seconds"]))
        return measure(output, dataset, method, repeat, order_position,
                       executable, executable_hash, config, measured,
                       enforce_environment_gate,
                       attempt + 1)
    core = [
        "taskset", "-c", str(config["selected_cpu"]), str(executable),
        "-t", str(config["threads"]), "-k", str(config["k"]),
        "-w", str(config["w"]), "-d", str(index),
        str(dataset["resolved_path"]),
    ]
    command = ([str(config["time_program"]),
                *[str(item) for item in config["time_arguments"]], *core]
               if measured else core)
    print(("MEASURE " if measured else "WARMUP ") + stem + ": " +
          shlex.join(command), flush=True)
    swap_before = swap_counters()
    started_ns = time.monotonic_ns()
    completed = subprocess.run(command, cwd=str(output), text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               check=False)
    ended_ns = time.monotonic_ns()
    swap_after = swap_counters()
    atomic_text(stdout_path, completed.stdout)
    atomic_text(stderr_path, completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError("indexing failed; see " + str(stderr_path))
    if not index.is_file() or index.stat().st_size == 0:
        raise RuntimeError("empty index: " + str(index))
    fields = parse_stderr(completed.stderr, require_timing=measured)
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
    user_time = float(fields["user_time_s"]) if measured else ""
    system_time = float(fields["system_time_s"]) if measured else ""
    peak_kb = int(fields["peak_rss_kb"]) if measured else ""
    with index.open("rb") as handle:
        magic = handle.read(4).hex()
    index_size = index.stat().st_size
    index_hash = sha256_file(index)
    index.unlink()
    if index.exists():
        raise RuntimeError("temporary index removal failed: " + str(index))
    swap_delta = tuple(after - before for before, after in
                       zip(swap_before, swap_after))
    wall_monotonic = (ended_ns - started_ns) / 1_000_000_000
    row = {
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
        "phase": "measured" if measured else "warmup",
        "repeat": repeat if measured else 0,
        "order_position": order_position,
        "threads": config["threads"],
        "k": config["k"],
        "w": config["w"],
        "hpc": int(bool(config["hpc"])),
        "command": shlex.join(command),
        "exit_status": completed.returncode,
        "wall_time_s": "{:.9f}".format(wall_monotonic) if measured else "",
        "time_v_wall_time_s": fields["wall_time_s"] if measured else "",
        "user_time_s": user_time,
        "system_time_s": system_time,
        "cpu_time_s": (float(user_time) + float(system_time)
                       if measured else ""),
        "peak_rss_kb": peak_kb,
        "peak_rss_gib": (int(peak_kb) / 1024 / 1024 if measured else ""),
        "distinct_minimizers": fields["distinct_minimizers"],
        "singleton_percent": fields["singleton_percent"],
        "average_occurrences": fields["average_occurrences"],
        "average_spacing": fields["average_spacing"],
        "distinct_minimizer_density_per_base":
            int(fields["distinct_minimizers"]) / int(dataset["total_bases"]),
        "minimizer_occurrence_density_per_base":
            1.0 / float(fields["average_spacing"]),
        "index_path": str(index),
        "index_size_bytes": index_size,
        "index_sha256": index_hash,
        "index_magic_hex": magic,
        "index_removed_after_capture": "YES",
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "system_snapshot_path": str(snapshot_path),
        "executable_path": str(executable),
        "executable_sha256": executable_hash,
        "load_average_1m": load,
        "memory_available_bytes": memory,
        "output_free_bytes": disk,
        "swap_in_delta": swap_delta[0],
        "swap_out_delta": swap_delta[1],
        "selected_cpu": config["selected_cpu"],
    }
    if enforce_environment_gate and measured and swap_delta != (0, 0):
        invalid_path = output / "INVALID_MEASURED_ATTEMPTS.tsv"
        invalid_rows = []
        if invalid_path.is_file():
            with invalid_path.open(encoding="utf-8", newline="") as handle:
                invalid_rows = list(csv.DictReader(handle, delimiter="\t"))
        invalid_rows.append({
            "dataset_key": dataset["key"],
            "method": method,
            "repeat": repeat,
            "order_position": order_position,
            "stem": stem,
            "command": shlex.join(command),
            "exit_status": completed.returncode,
            "wall_time_s": "{:.9f}".format(wall_monotonic),
            "index_size_bytes": index_size,
            "index_sha256": index_hash,
            "index_magic_hex": magic,
            "swap_in_delta": swap_delta[0],
            "swap_out_delta": swap_delta[1],
            "stderr_path": str(stderr_path),
            "disposition": "REJECTED_INVALID_SYSTEM_STATE; output captured and temporary index removed",
        })
        write_table(invalid_path, invalid_rows, delimiter="\t")
        if attempt >= int(config["maximum_environment_retries"]):
            raise RuntimeError("active swapping persisted through retries for " +
                               stem_base)
        print("RETRY {} rejected for swap delta {}".format(
            stem, swap_delta), flush=True)
        time.sleep(int(config["environment_retry_seconds"]))
        return measure(output, dataset, method, repeat, order_position,
                       executable, executable_hash, config, measured,
                       enforce_environment_gate,
                       attempt + 1)
    print("DONE {} index={} sha256={} removed=YES".format(
        stem, index_size, index_hash), flush=True)
    return row


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
        "WARMUP_PER_METHOD_DATASET=" +
            ("0" if mode == "preflight" else str(config["warmups"])),
        "RUN_ORDER=odd_repeats_original_first;even_repeats_kssd_first",
        "EXECUTION=sequential",
        "SELECTED_CPU=" + str(config["selected_cpu"]),
        "KSSD_IMPLEMENTATION=public runtime inline plan; no generic external call in mm_sketch",
        "TEMPORARY_INDEX_POLICY=unique path; capture size/hash/magic; delete only after successful capture",
    ]
    for dataset in datasets:
        token = str(dataset["key"]).upper()
        for key in ("resolved_path", "size_bytes", "sha256", "sequence_count",
                    "total_bases", "accession", "version"):
            lines.append(token + "_" + key.upper() + "=" + str(dataset[key]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_table(path: Path, rows: list[dict[str, object]],
                delimiter: str = ",") -> None:
    if not rows:
        raise RuntimeError("refusing to write empty table: " + str(path))
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]),
                                delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_identity_tables(output: Path, datasets: list[dict[str, object]],
                          executables: dict[str, Path],
                          executable_hashes: dict[str, str]) -> None:
    input_rows = [{
        "dataset_key": item["key"],
        "dataset": item["manuscript_label"],
        "absolute_path": item["resolved_path"],
        "size_bytes": item["size_bytes"],
        "sha256": item["sha256"],
        "sequence_count": item["sequence_count"],
        "total_bases": item["total_bases"],
    } for item in datasets]
    executable_rows = [{
        "method": method,
        "absolute_path": str(executables[method]),
        "size_bytes": executables[method].stat().st_size,
        "sha256": executable_hashes[method],
        "version": command_output([str(executables[method]), "--version"]),
    } for method in METHODS]
    write_table(output / "input_sha256.tsv", input_rows, delimiter="\t")
    write_table(output / "executable_sha256.tsv", executable_rows,
                delimiter="\t")


def write_environment(output: Path, config: dict[str, object]) -> None:
    sections = [
        "captured=" + now(),
        "repository=" + str(REPO_ROOT),
        "head=" + command_output(["git", "-C", str(REPO_ROOT),
                                   "rev-parse", "HEAD"]),
        "selected_cpu=" + str(config["selected_cpu"]),
        "protocol=warm-cache; one warmup per method/dataset; five paired repeats",
    ]
    for name, command in (
            ("uname", ["uname", "-a"]),
            ("lscpu", ["lscpu"]),
            ("free", ["free", "-h"]),
            ("disk", ["df", "-h", str(output)]),
            ("cc", ["cc", "--version"]),
            ("time", ["/usr/bin/time", "--version"])):
        sections.append("\n[{}]\n{}".format(name, run_optional(command)))
    atomic_text(output / "environment.txt", "\n".join(sections) + "\n")


def write_commands(output: Path, warmups: list[dict[str, object]],
                   measured: list[dict[str, object]]) -> None:
    lines = [
        "#!/bin/sh",
        "# Exact command ledger; warm-up timing is discarded.",
        "# Indexes were deleted only after successful metadata capture.",
        "",
    ]
    lines.extend(str(row["command"]) for row in [*warmups, *measured])
    atomic_text(output / "commands.sh", "\n".join(lines) + "\n")


def write_final_report(output: Path) -> None:
    with (output / "supplementary_indexing_summary.csv").open(
            encoding="utf-8", newline="") as handle:
        summary = list(csv.DictReader(handle))
    with (output / "supplementary_indexing_pairwise_ratios.csv").open(
            encoding="utf-8", newline="") as handle:
        pairs = list(csv.DictReader(handle))
    with (output / "supplementary_indexing_raw.csv").open(
            encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle))
    by_summary = {(row["dataset"], row["method"]): row for row in summary}
    lines = [
        "# Supplementary Figure S1 public-inline final report",
        "",
        "Generated: `{}`".format(now()),
        "",
        "This is the completed three-dataset comparison of Original Minimap2 "
        "and the optimized public runtime-inline KSSD-Array path. The former "
        "generic external-call results are not included.",
        "",
        "Protocol: one discarded warm-up per method/dataset; five sequential "
        "paired repeats; Original first on odd repeats and KSSD first on even "
        "repeats; one thread pinned to the configured CPU; warm cache; no "
        "performance-based early stopping.",
        "",
    ]
    invalid_path = output / "INVALID_MEASURED_ATTEMPTS.tsv"
    invalid_count = 0
    if invalid_path.is_file():
        with invalid_path.open(encoding="utf-8", newline="") as handle:
            invalid_count = len(list(csv.DictReader(handle, delimiter="\t")))
    lines.extend([
        "Environment-filtered attempts preserved outside the accepted raw "
        "table: `{}`.".format(invalid_count),
        "",
    ])
    for dataset in ("Arabidopsis thaliana", "Human GRCh38", "Zea mays"):
        original = by_summary[(dataset, "Original Minimap2")]
        kssd = by_summary[(dataset, "KSSD-Array")]
        dataset_pairs = [row for row in pairs if row["dataset"] == dataset]
        ratios = [float(row["kssd_over_original_wall_ratio"])
                  for row in dataset_pairs]
        faster = sum(value < 1.0 for value in ratios)
        slower = sum(value > 1.0 for value in ratios)
        classification = dataset_pairs[0]["classification"]
        dataset_raw = [row for row in raw if row["dataset"] == dataset]
        maximum_rss = max(float(row["peak_rss_gib"]) for row in dataset_raw)
        original_maximum_rss = max(
            float(row["peak_rss_gib"]) for row in dataset_raw
            if row["method"] == "Original Minimap2")
        kssd_maximum_rss = max(
            float(row["peak_rss_gib"]) for row in dataset_raw
            if row["method"] == "KSSD-Array")
        original_first_mean = sum(ratios[0::2]) / len(ratios[0::2])
        kssd_first_mean = sum(ratios[1::2]) / len(ratios[1::2])
        deterministic = all(
            row[field + "_repeat_consistent"] == "1"
            for row in (original, kssd)
            for field in ("index_size_bytes", "distinct_minimizers",
                          "average_spacing", "index_sha256"))
        lines.extend([
            "## " + dataset,
            "",
            "- Original wall time: `{:.6f} +/- {:.6f} s` (mean +/- sample SD).".
                format(float(original["wall_time_s_mean"]),
                       float(original["wall_time_s_sd"])),
            "- Public-inline KSSD wall time: `{:.6f} +/- {:.6f} s` "
            "(mean +/- sample SD).".format(
                float(kssd["wall_time_s_mean"]),
                float(kssd["wall_time_s_sd"])),
            "- Paired KSSD/Original ratios: `" + ", ".join(
                "{:.6f}".format(value) for value in ratios) + "`.",
            "- Median paired ratio: `{}`; direction: KSSD faster `{}/5`, "
            "slower `{}/5`; classification: **{}**.".format(
                dataset_pairs[0]["median_paired_ratio"], faster, slower,
                classification),
            "- Maximum RSS (Original/KSSD/all): `{:.6f}` / `{:.6f}` / "
            "`{:.6f} GiB`.".format(original_maximum_rss,
                                    kssd_maximum_rss, maximum_rss),
            "- Order-position check: Original-first mean ratio `{:.6f}`; "
            "KSSD-first mean ratio `{:.6f}`.".format(
                original_first_mean, kssd_first_mean),
            "- Original/KSSD index sizes: `{:.0f}` / `{:.0f}` bytes; "
            "distinct minimizers: `{:.0f}` / `{:.0f}`; mean spacing: "
            "`{:.3f}` / `{:.3f}`.".format(
                float(original["index_size_bytes_mean"]),
                float(kssd["index_size_bytes_mean"]),
                float(original["distinct_minimizers_mean"]),
                float(kssd["distinct_minimizers_mean"]),
                float(original["average_spacing_mean"]),
                float(kssd["average_spacing_mean"])),
            "- Distinct-minimizer density per base (Original/KSSD): "
            "`{:.9f}` / `{:.9f}`.".format(
                float(original["distinct_minimizer_density_per_base_mean"]),
                float(kssd["distinct_minimizer_density_per_base_mean"])),
            "- Output equivalence across repeats within each method: **{}**.".
                format("PASS" if deterministic else "FAIL"),
            "",
        ])
    atomic_text(output / "S1_INLINE_FINAL_REPORT.md", "\n".join(lines))


def write_output_hashes(output: Path) -> None:
    rows = []
    for path in sorted(output.rglob("*")):
        if (path.is_file() and path.name != "output_sha256.tsv" and
                not path.name.endswith(".tmp")):
            rows.append({
                "relative_path": str(path.relative_to(output)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    write_table(output / "output_sha256.tsv", rows, delimiter="\t")


def finalize_run_manifest(output: Path, rows: list[dict[str, object]]) -> None:
    path = output / "run_manifest.txt"
    existing = path.read_text(encoding="utf-8")
    completion = "\n".join((
        "RESULT_STATUS=COMPLETE",
        "COMPLETED_AT=" + now(),
        "ACCEPTED_MEASURED_ROWS=" + str(len(rows)),
        "ACCEPTED_PAIRED_COMPARISONS=" + str(len(rows) // 2),
        "ALL_THREE_DATASETS_COMPLETE=" +
            ("YES" if len(rows) == 30 else "NO"),
        "INDEX_DIRECTORY_EMPTY=" +
            ("YES" if not any((output / "indexes").iterdir()) else "NO"),
    )) + "\n"
    if "RESULT_STATUS=COMPLETE" not in existing:
        atomic_text(path, existing + completion)


def main() -> int:
    args = parse_args()
    if args.jobs < 1:
        raise ValueError("--jobs must be positive")
    output = args.output_dir.expanduser().resolve()
    if output.exists() and not args.resume:
        raise FileExistsError("output directory already exists: " + str(output))
    if args.resume:
        if not output.is_dir():
            raise FileNotFoundError("resume output directory is missing")
        if not (output / "logs").is_dir() or not (output / "indexes").is_dir():
            raise RuntimeError("resume output directory is incomplete")
    else:
        output.mkdir(parents=True)
        (output / "logs").mkdir()
        (output / "indexes").mkdir()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if (int(config["threads"]), int(config["repeats"]),
            int(config["warmups"])) != (1, 5, 1):
        raise RuntimeError(
            "the pinned inline-final protocol requires one thread, one "
            "warm-up, and five repeats")
    kssd_root = args.kssd_root.expanduser().resolve()
    patch_path = kssd_root / str(config["patch"])
    if sha256_file(patch_path) != str(config["patch_sha256"]):
        raise RuntimeError("integration patch SHA-256 does not match config")
    if args.resume:
        executables, executable_hashes = load_executables(output)
    else:
        executables, build_logs = build_executables(
            output, args.upstream_source, kssd_root, args.jobs,
        )
        executable_hashes = write_build_manifest(
            output / "build_manifest.txt", config, kssd_root,
            executables, build_logs,
        )
    if args.preflight:
        datasets = [preflight_dataset()]
        mode = "preflight"
    else:
        datasets = resolve_datasets(config, parse_overrides(args.dataset))
        mode = "formal"
    if not args.resume:
        write_identity_tables(output, datasets, executables, executable_hashes)
        write_run_manifest(output / "run_manifest.txt", config, datasets,
                           mode, output)
        write_environment(output, config)
    input_paths = [Path(str(dataset["resolved_path"])) for dataset in datasets]
    initial_preflight = (output / "system_preflight.txt" if not args.resume
                         else output / "system_preflight-resume.txt")
    system_preflight(
        initial_preflight, output, input_paths,
        config, not args.preflight,
    )
    raw_path = output / "supplementary_indexing_raw.csv"
    if args.resume and raw_path.is_file():
        with raw_path.open(encoding="utf-8", newline="") as handle:
            rows: list[dict[str, object]] = list(csv.DictReader(handle))
    else:
        rows = []
    completed_keys = {
        (str(row["dataset_key"]), int(row["repeat"]), str(row["method"]))
        for row in rows
    }
    warmups: list[dict[str, object]] = []
    if args.preflight:
        dataset = datasets[0]
        for position, method in enumerate(METHODS, start=1):
            rows.append(measure(
                output, dataset, method, 1, position, executables[method],
                executable_hashes[method], config, True, False))
            write_csv(raw_path, rows)
    else:
        repeats = int(config["repeats"])
        run_order = list(config["run_order"])
        for dataset in datasets:
            dataset_key = str(dataset["key"])
            system_preflight(
                output / "logs" /
                ("preflight-" + dataset_key +
                 ("-resume.txt" if args.resume else ".txt")),
                output, [Path(str(dataset["resolved_path"]))], config, True)
            for position, method in enumerate(METHODS, start=1):
                method_token = ("original" if method == METHODS[0]
                                else "kssd-array")
                existing_warmup = (output / "logs" /
                    (dataset_key + "-" + method_token +
                     "-warmup.stderr"))
                if args.resume and existing_warmup.is_file():
                    warmup_index = output / "indexes" / (
                        dataset_key + "-" + method_token + "-warmup.mmi")
                    warmups.append({"command": shlex.join([
                        "taskset", "-c", str(config["selected_cpu"]),
                        str(executables[method]), "-t", str(config["threads"]),
                        "-k", str(config["k"]), "-w", str(config["w"]),
                        "-d", str(warmup_index),
                        str(dataset["resolved_path"]),
                    ])})
                else:
                    warmups.append(measure(
                        output, dataset, method, 0, position,
                        executables[method], executable_hashes[method], config,
                        False, True))
            for repeat in range(1, repeats + 1):
                order = list(run_order[repeat - 1])
                if set(order) != set(METHODS):
                    raise RuntimeError("invalid configured method order")
                for position, method in enumerate(order, start=1):
                    key = (dataset_key, repeat, method)
                    if key in completed_keys:
                        continue
                    rows.append(measure(
                        output, dataset, method, repeat, position,
                        executables[method], executable_hashes[method],
                        config, True, True,
                    ))
                    completed_keys.add(key)
                    write_csv(raw_path, rows)
                    time.sleep(int(config["cooldown_seconds"]))
        if len(warmups) != 6 or len(rows) != 30:
            raise RuntimeError("inline-final run grid is incomplete")
        write_commands(output, warmups, rows)
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
    if not args.preflight:
        write_final_report(output)
    if any((output / "indexes").iterdir()):
        raise RuntimeError("temporary index directory is not empty")
    if not args.preflight:
        finalize_run_manifest(output, rows)
    write_output_hashes(output)
    print("RAW=" + str(raw_path))
    print("ROWS=" + str(len(rows)))
    print("OUTPUT_DIRECTORY=" + str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
