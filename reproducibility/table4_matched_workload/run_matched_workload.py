#!/usr/bin/env python3
"""Build, validate, and run the matched-workload KSSD-Array/ntHash study."""

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import shlex
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path


METHODS = ("KSSD-Array", "ntHash")
VALIDATION_K = (4, 21, 32)
NTHASH_COMMIT = "c26bd4572a19de81e30d55042dbd33c1fd21d4b6"
NTHASH_VERSION = "2.4.0"
NTHASH_HEADER_SHA256 = (
    "7ce43aded7fae6446578994ce91d0e65df889916e6ce556ce90945493f5b2099"
)
SOURCE_NAME = "benchmark_matched_workload.cpp"
PILOT_RAW_FIELDS = (
    "dataset", "dataset_label", "repeat", "execution_order", "method",
    "k", "w", "seed", "taskset_cpu", "runtime_s",
    "throughput_windows_s", "throughput_mwindows_s", "score_count",
    "window_count", "minimizers_processed", "checksum", "load1_before",
)


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--synthetic",
        default=os.environ.get(
            "KSSD_SYNTHETIC_FASTA", str(Path.home() / "AEEE.fasta")),
    )
    parser.add_argument(
        "--human",
        default=os.environ.get(
            "KSSD_HUMAN_FASTA",
            str(Path.home() / "seq/human" /
                "GCF_000001405.40_GRCh38.p14_genomic.fna"),
        ),
    )
    parser.add_argument(
        "--nthash-source",
        default=os.environ.get("NTHASH_SOURCE", str(Path.home() / "ntHash")),
    )
    parser.add_argument(
        "--output-root",
        default=os.environ.get(
            "KSSD_FORMAL_RESULTS",
            str(Path.home() / "KSSD-Array-formal-results"),
        ),
    )
    parser.add_argument("--cpu", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pilot-repeats", type=int, default=7)
    parser.add_argument("--full-repeats", type=int, default=5)
    parser.add_argument(
        "--validation-only", action="store_true",
        help="build and validate, but deliberately do not run performance")
    return parser.parse_args()


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def timestamp():
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text(path, value):
    Path(path).write_text(value, encoding="utf-8")


def write_csv(path, rows, fieldnames):
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def mean_sd(values):
    if not values:
        return math.nan, math.nan
    if len(values) == 1:
        return values[0], 0.0
    return statistics.mean(values), statistics.stdev(values)


class Recorder:
    def __init__(self, result_dir):
        self.result_dir = Path(result_dir)
        self.commands = []

    def flush_commands(self):
        lines = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "# Exact commands executed by run_matched_workload.py.",
        ]
        lines.extend(self.commands)
        write_text(self.result_dir / "commands.sh", "\n".join(lines) + "\n")

    def run(self, command, cwd, log_path=None, env=None, check=True):
        rendered = "cd {} && {}".format(
            shlex.quote(str(cwd)),
            shlex.join([str(part) for part in command]),
        )
        self.commands.append(rendered)
        self.flush_commands()
        completed = subprocess.run(
            [str(part) for part in command],
            cwd=str(cwd),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if log_path is not None:
            write_text(
                log_path,
                "COMMAND\n{}\n\nRETURN_CODE\n{}\n\nSTDOUT\n{}\nSTDERR\n{}".format(
                    rendered, completed.returncode, completed.stdout,
                    completed.stderr,
                ),
            )
        if check and completed.returncode != 0:
            location = " (see {})".format(log_path) if log_path else ""
            raise RuntimeError(
                "command failed{}: {}".format(location, rendered))
        return completed


def git_value(recorder, repo, arguments):
    return recorder.run(
        ["git"] + list(arguments), repo).stdout.strip()


def create_result_dir(root, stem):
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    candidate = root / "{}-{}".format(stem, timestamp())
    suffix = 1
    while candidate.exists():
        candidate = root / "{}-{}-{:02d}".format(stem, timestamp(), suffix)
        suffix += 1
    candidate.mkdir()
    (candidate / "logs").mkdir()
    (candidate / "build").mkdir()
    return candidate


def parse_lscpu_rows(text):
    rows = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split(",")
        if len(fields) >= 4 and fields[0].isdigit():
            rows.append(tuple(int(value) for value in fields[:4]))
    return rows


def select_cpu(requested):
    allowed = set(os.sched_getaffinity(0))
    completed = subprocess.run(
        ["lscpu", "-p=CPU,CORE,SOCKET,NODE"], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    rows = parse_lscpu_rows(completed.stdout)
    if requested is not None:
        if requested not in allowed:
            raise RuntimeError(
                "requested CPU {} is outside Cpus_allowed_list".format(
                    requested))
        return requested, rows
    first_thread_by_core = {}
    for cpu, core, socket, node in rows:
        if cpu in allowed:
            first_thread_by_core.setdefault((socket, core), cpu)
    if not first_thread_by_core:
        raise RuntimeError("no allowed physical CPU was found")
    return max(first_thread_by_core.values()), rows


def verify_inputs(repo_root, arguments, result_dir):
    metadata = json.loads(
        (repo_root / "reproducibility/data/datasets.json").read_text(
            encoding="utf-8"))
    specifications = [
        (
            "Synthetic_300M", "Synthetic 300 Mb",
            Path(arguments.synthetic).expanduser().resolve(),
            metadata["datasets"]["Synthetic_300M"]["historical_sha256"],
            None,
        ),
        (
            "Human_GRCh38", "GRCh38.p14 chr1",
            Path(arguments.human).expanduser().resolve(),
            metadata["datasets"]["Human_GRCh38"]["expected_sha256"],
            int(metadata["datasets"]["Human_GRCh38"]["expected_size_bytes"]),
        ),
    ]
    rows = []
    datasets = []
    for token, label, path, expected_sha, expected_size in specifications:
        if not path.is_file():
            raise RuntimeError("input is missing: {}".format(path))
        actual_size = path.stat().st_size
        actual_sha = sha256_file(path)
        size_matches = expected_size is None or actual_size == expected_size
        sha_matches = actual_sha == expected_sha
        rows.append({
            "dataset": token,
            "label": label,
            "absolute_path": str(path),
            "size_bytes": actual_size,
            "expected_size_bytes": (
                "" if expected_size is None else expected_size),
            "sha256": actual_sha,
            "expected_sha256": expected_sha,
            "size_match": "YES" if size_matches else "NO",
            "sha256_match": "YES" if sha_matches else "NO",
        })
        if not size_matches or not sha_matches:
            write_csv(
                result_dir / "input_sha256.tsv", rows, rows[0].keys())
            raise RuntimeError(
                "pinned input identity mismatch for {}".format(path))
        datasets.append((token, label, path))
    with (result_dir / "input_sha256.tsv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return datasets


def verify_nthash(recorder, source):
    source = Path(source).expanduser().resolve()
    if not (source / ".git").is_dir():
        raise RuntimeError("ntHash source is not a Git checkout: {}".format(
            source))
    commit = git_value(recorder, source, ["rev-parse", "HEAD"])
    if commit != NTHASH_COMMIT:
        raise RuntimeError(
            "ntHash commit mismatch: expected {}, found {}".format(
                NTHASH_COMMIT, commit))
    header = source / "include/nthash/nthash.hpp"
    if sha256_file(header) != NTHASH_HEADER_SHA256:
        raise RuntimeError("ntHash header hash does not match pinned identity")
    return source, commit, header


def compile_archive(recorder, output_dir, compiler, flags, include_flags,
                    sources, archive_name, tag):
    object_dir = output_dir / tag
    object_dir.mkdir(parents=True, exist_ok=True)
    log_dir = output_dir.parents[1] / "logs"
    objects = []
    for source in sources:
        source = Path(source)
        target = object_dir / (source.stem + ".o")
        command = (
            [compiler] + list(flags) + list(include_flags) +
            ["-c", str(source), "-o", str(target)]
        )
        recorder.run(
            command, output_dir,
            log_dir / "{}_{}.log".format(tag, source.stem))
        objects.append(target)
    archive = object_dir / archive_name
    recorder.run(
        ["ar", "rcs", str(archive)] + [str(value) for value in objects],
        output_dir,
        log_dir / "{}_archive.log".format(tag))
    recorder.run(
        ["ranlib", str(archive)], output_dir,
        log_dir / "{}_ranlib.log".format(tag))
    return archive


def build_libraries(recorder, repo_root, nthash_source, result_dir,
                    sanitizer=False):
    cc = os.environ.get("CC", "cc")
    cxx = os.environ.get("CXX", "c++")
    if sanitizer:
        common = [
            "-O1", "-g", "-fno-omit-frame-pointer",
            "-fsanitize=address,undefined", "-DNDEBUG",
        ]
        tag = "sanitizer"
    else:
        common = ["-O3", "-march=native", "-DNDEBUG"]
        tag = "performance"
    build_dir = result_dir / "build" / tag
    build_dir.mkdir(parents=True, exist_ok=True)
    kssd = compile_archive(
        recorder, build_dir, cc, common + ["-std=c11"],
        ["-I{}".format(repo_root / "include"),
         "-I{}".format(repo_root / "src")],
        [repo_root / "src/kssd_array.c", repo_root / "src/permutation.c"],
        "libkssd_array.a", "kssd")
    nthash = compile_archive(
        recorder, build_dir, cxx, common + ["-std=c++17"],
        ["-I{}".format(nthash_source / "include")],
        [nthash_source / "src/kmer.cpp", nthash_source / "src/seed.cpp"],
        "libnthash.a", "nthash")
    return {
        "tag": tag,
        "build_dir": build_dir,
        "kssd_library": kssd,
        "nthash_library": nthash,
        "common_flags": common,
        "cc": cc,
        "cxx": cxx,
    }


def compile_binary(recorder, repo_root, nthash_source, result_dir, libraries,
                   k, sanitizer=False):
    binary_dir = result_dir / "build" / libraries["tag"] / "bin"
    binary_dir.mkdir(parents=True, exist_ok=True)
    binary = binary_dir / "matched_k{}_w{}".format(k, k)
    if sanitizer:
        flags = [
            "-O1", "-g", "-fno-omit-frame-pointer",
            "-fsanitize=address,undefined", "-DNDEBUG",
        ]
    else:
        flags = ["-O3", "-march=native", "-DNDEBUG"]
    command = [
        libraries["cxx"], "-std=c++17",
    ] + flags + [
        "-Wall", "-Wextra", "-Wpedantic",
        "-DK={}".format(k), "-DW={}".format(k),
        "-I{}".format(repo_root / "include"),
        "-I{}".format(nthash_source / "include"),
        str(repo_root / "reproducibility/table4_matched_workload" /
            SOURCE_NAME),
        str(libraries["kssd_library"]),
        str(libraries["nthash_library"]),
        "-lz", "-o", str(binary),
    ]
    recorder.run(
        command, repo_root,
        result_dir / "logs" / "compile_{}_k{}.log".format(
            libraries["tag"], k))
    return binary, command


def build_and_validate(recorder, repo_root, nthash_source, result_dir):
    performance = build_libraries(
        recorder, repo_root, nthash_source, result_dir, sanitizer=False)
    sanitizer = build_libraries(
        recorder, repo_root, nthash_source, result_dir, sanitizer=True)
    binaries = {}
    executable_rows = []
    validation_rows = []
    for k in VALIDATION_K:
        normal_binary, normal_command = compile_binary(
            recorder, repo_root, nthash_source, result_dir, performance, k)
        sanitizer_binary, sanitizer_command = compile_binary(
            recorder, repo_root, nthash_source, result_dir, sanitizer, k,
            sanitizer=True)
        binaries[k] = normal_binary
        for build_type, binary, command in (
                ("performance", normal_binary, normal_command),
                ("sanitizer", sanitizer_binary, sanitizer_command)):
            executable_rows.append({
                "build_type": build_type,
                "k": k,
                "w": k,
                "absolute_path": str(binary),
                "sha256": sha256_file(binary),
                "compile_command": shlex.join(command),
            })
        normal_log = result_dir / "logs" / "validate_normal_k{}.log".format(k)
        normal = recorder.run(
            [str(normal_binary), "--validate"], repo_root, normal_log)
        sanitizer_log = (
            result_dir / "logs" / "validate_sanitizer_k{}.log".format(k))
        sanitized = recorder.run(
            [
                "env",
                "ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:"
                "strict_string_checks=1",
                "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1",
                str(sanitizer_binary), "--validate",
            ],
            repo_root, sanitizer_log)
        normal_pass = "VALIDATION_SUMMARY\tPASS" in normal.stdout
        sanitizer_pass = "VALIDATION_SUMMARY\tPASS" in sanitized.stdout
        validation_rows.append({
            "k": k,
            "w": k,
            "normal_validation": "PASS" if normal_pass else "FAIL",
            "asan_ubsan_validation": "PASS" if sanitizer_pass else "FAIL",
            "normal_log": str(normal_log),
            "sanitizer_log": str(sanitizer_log),
        })
        if not normal_pass or not sanitizer_pass:
            raise RuntimeError("validation did not report PASS for K={}".format(
                k))
    write_csv(
        result_dir / "validation_results.csv", validation_rows,
        validation_rows[0].keys())
    return performance, binaries, executable_rows, validation_rows


def compiler_version(command):
    completed = subprocess.run(
        [command, "--version"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=True)
    return completed.stdout.splitlines()[0]


def run_preflight(recorder, repo_root, nthash_source, result_dir, cpu,
                  topology_rows, validation_only=False):
    commands = {
        "uname": ["uname", "-a"],
        "lscpu": ["lscpu"],
        "lscpu_extended": [
            "lscpu", "--extended=CPU,NODE,SOCKET,CORE,ONLINE,MAXMHZ,MINMHZ"],
        "free": ["free", "-b"],
        "swapon": ["swapon", "--show", "--bytes"],
        "vmstat": ["vmstat", "1", "6"],
        "processes": [
            "ps", "-eLo", "pid,lwp,psr,pcpu,comm,args", "--sort=-pcpu"],
    }
    outputs = {}
    for name, command in commands.items():
        completed = recorder.run(
            command, repo_root,
            result_dir / "logs" / "preflight_{}.log".format(name),
            check=(name != "swapon"))
        outputs[name] = completed.stdout

    load_values = [float(value) for value in
                   Path("/proc/loadavg").read_text().split()[:3]]
    physical_cores = len({(socket, core)
                          for _, core, socket, _ in topology_rows})
    vmstat_rows = []
    for line in outputs["vmstat"].splitlines():
        fields = line.split()
        if len(fields) >= 17 and fields[0].isdigit():
            vmstat_rows.append([int(value) for value in fields[:17]])
    sampled_rows = vmstat_rows[1:] if len(vmstat_rows) > 1 else vmstat_rows
    active_swapping = any(
        row[6] > 0 or row[7] > 0 for row in sampled_rows)
    severe_load = load_values[0] >= max(1.0, physical_cores * 0.75)

    selected_cpu_processes = []
    for line in outputs["processes"].splitlines()[1:]:
        fields = line.split(maxsplit=5)
        if len(fields) < 6:
            continue
        try:
            process_cpu = int(fields[2])
            percent_cpu = float(fields[3])
            process_id = int(fields[0])
        except ValueError:
            continue
        if (process_cpu == cpu and percent_cpu >= 50.0 and
                process_id != os.getpid()):
            selected_cpu_processes.append(line)
    competing_benchmark = bool(selected_cpu_processes)

    governor_path = Path(
        "/sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor".format(cpu))
    governor = (
        governor_path.read_text(encoding="utf-8").strip()
        if governor_path.is_file() else "unavailable")
    environment_names = sorted(
        name for name in os.environ
        if name.startswith((
            "OMP_", "MKL_", "OPENBLAS_", "NUMEXPR_", "KSSD_", "NTHASH_",
            "MALLOC_", "LD_")))
    relevant_environment = [
        "{}={}".format(name, os.environ[name]) for name in environment_names]
    repo_commit = git_value(recorder, repo_root, ["rev-parse", "HEAD"])
    nthash_commit = git_value(
        recorder, nthash_source, ["rev-parse", "HEAD"])
    source_paths = [
        repo_root / "include/kssd_array.h",
        repo_root / "include/kssd_array_fast.h",
        repo_root / "src/kssd_array.c",
        repo_root / "src/permutation.c",
    ]
    lines = [
        "PREFLIGHT_TIME={}".format(now_iso()),
        "HOSTNAME={}".format(platform.node()),
        "PLATFORM={}".format(platform.platform()),
        "REPOSITORY_COMMIT={}".format(repo_commit),
        "NTHASH_VERSION={}".format(NTHASH_VERSION),
        "NTHASH_COMMIT={}".format(nthash_commit),
        "NTHASH_HEADER_SHA256={}".format(
            sha256_file(nthash_source / "include/nthash/nthash.hpp")),
        "TASKSET_CPU={}".format(cpu),
        "CPU_GOVERNOR={}".format(governor),
        "PHYSICAL_CORES={}".format(physical_cores),
        "LOAD_AVERAGE={}".format(" ".join(str(value)
                                           for value in load_values)),
        "ACTIVE_SWAPPING={}".format("YES" if active_swapping else "NO"),
        "SEVERE_LOAD={}".format("YES" if severe_load else "NO"),
        "COMPETING_PROCESS_ON_CPU={}".format(
            "YES" if competing_benchmark else "NO"),
        "CC_VERSION={}".format(compiler_version(os.environ.get("CC", "cc"))),
        "CXX_VERSION={}".format(
            compiler_version(os.environ.get("CXX", "c++"))),
        "",
        "[KSSD_SOURCE_SHA256]",
    ]
    lines.extend("{}  {}".format(sha256_file(path), path)
                 for path in source_paths)
    lines.extend([
        "",
        "[RELEVANT_ENVIRONMENT]",
        *(relevant_environment or ["(none set)"]),
        "",
        "[SELECTED_CPU_HIGH_USAGE_PROCESSES]",
        *(selected_cpu_processes or ["(none)"]),
        "",
        "[UNAME]",
        outputs["uname"].rstrip(),
        "",
        "[LSCPU]",
        outputs["lscpu"].rstrip(),
        "",
        "[LSCPU_EXTENDED]",
        outputs["lscpu_extended"].rstrip(),
        "",
        "[FREE_BYTES]",
        outputs["free"].rstrip(),
        "",
        "[SWAP_USAGE]",
        outputs["swapon"].rstrip() or "(no swap devices)",
        "",
        "[VMSTAT_1S_6]",
        outputs["vmstat"].rstrip(),
    ])
    write_text(result_dir / "environment.txt", "\n".join(lines) + "\n")
    reasons = []
    if validation_only:
        reasons.append("--validation-only was requested")
    if active_swapping:
        reasons.append("vmstat observed non-zero si/so after the baseline row")
    if severe_load:
        reasons.append(
            "1-minute load average {:.2f} met the severe-load threshold "
            "{:.2f}".format(load_values[0], physical_cores * 0.75))
    if competing_benchmark:
        reasons.append(
            "a process using at least 50% CPU was observed on selected CPU {}".
            format(cpu))
    return {
        "safe": not reasons,
        "reasons": reasons,
        "load": load_values,
        "physical_cores": physical_cores,
        "active_swapping": active_swapping,
        "severe_load": severe_load,
        "competing_benchmark": competing_benchmark,
        "governor": governor,
        "repo_commit": repo_commit,
        "nthash_commit": nthash_commit,
    }


def write_build_manifest(result_dir, repo_root, nthash_source, performance,
                         executable_rows):
    lines = [
        "BUILD_TIME={}".format(now_iso()),
        "REPOSITORY={}".format(repo_root),
        "REPOSITORY_COMMIT={}".format(
            subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True,
                stdout=subprocess.PIPE, check=True).stdout.strip()),
        "BENCHMARK_SOURCE={}".format(
            repo_root / "reproducibility/table4_matched_workload" /
            SOURCE_NAME),
        "BENCHMARK_SOURCE_SHA256={}".format(
            sha256_file(
                repo_root / "reproducibility/table4_matched_workload" /
                SOURCE_NAME)),
        "NTHASH_SOURCE={}".format(nthash_source),
        "NTHASH_VERSION={}".format(NTHASH_VERSION),
        "NTHASH_COMMIT={}".format(NTHASH_COMMIT),
        "NTHASH_CANONICAL_RULE=forward_hash + reverse_hash modulo 2^64",
        "KSSD_CANONICAL_RULE=min(forward_two_bit,reverse_complement_two_bit)",
        "PERFORMANCE_CPP_FLAGS=-O3 -march=native -std=c++17 -DNDEBUG",
        "PERFORMANCE_C_FLAGS=-O3 -march=native -std=c11 -DNDEBUG",
        "LTO=disabled",
        "KSSD_ARCHIVE={}".format(performance["kssd_library"]),
        "KSSD_ARCHIVE_SHA256={}".format(
            sha256_file(performance["kssd_library"])),
        "NTHASH_ARCHIVE={}".format(performance["nthash_library"]),
        "NTHASH_ARCHIVE_SHA256={}".format(
            sha256_file(performance["nthash_library"])),
        "NTHASH_EQUIVALENT_OPTIMIZATION=YES",
        "SANITIZERS=address,undefined",
        "ASAN_LEAK_DETECTION=disabled because LeakSanitizer is unavailable "
        "under the execution environment's ptrace supervision; AddressSanitizer "
        "and UndefinedBehaviorSanitizer remain enabled with halt_on_error",
        "",
        "[EXECUTABLES]",
    ]
    lines.extend(
        "{} K={} W={} {} {}".format(
            row["build_type"], row["k"], row["w"], row["sha256"],
            row["absolute_path"])
        for row in executable_rows)
    write_text(result_dir / "build_manifest.txt", "\n".join(lines) + "\n")
    with (result_dir / "executable_sha256.tsv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=executable_rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(executable_rows)


def parse_benchmark_output(text, expected_method, expected_k):
    metadata = None
    result = None
    for line in text.splitlines():
        fields = line.split("\t")
        if fields[0] == "META" and len(fields) == 9:
            metadata = {
                "raw_bases": int(fields[1]),
                "cleaned_bases": int(fields[2]),
                "ambiguous_bases": int(fields[3]),
                "score_count": int(fields[4]),
                "window_count": int(fields[5]),
                "k": int(fields[6]),
                "w": int(fields[7]),
                "seed": int(fields[8]),
            }
        elif fields[0] == "RESULT" and len(fields) == 9:
            result = {
                "method": fields[1],
                "runtime_s": float(fields[2]),
                "throughput_windows_s": float(fields[3]),
                "throughput_mwindows_s": float(fields[4]),
                "score_count": int(fields[5]),
                "window_count": int(fields[6]),
                "minimizers_processed": int(fields[7]),
                "checksum": fields[8],
            }
    if metadata is None or result is None:
        raise RuntimeError("benchmark output is missing META or RESULT")
    if result["method"] != expected_method:
        raise RuntimeError("benchmark reported the wrong method")
    if metadata["k"] != expected_k or metadata["w"] != expected_k:
        raise RuntimeError("benchmark reported the wrong K/W")
    expected_scores = metadata["cleaned_bases"] - expected_k + 1
    expected_windows = expected_scores - expected_k + 1
    if metadata["score_count"] != expected_scores:
        raise RuntimeError("reported score count is inconsistent")
    if metadata["window_count"] != expected_windows:
        raise RuntimeError("reported window count is inconsistent")
    if (result["score_count"] != expected_scores or
            result["window_count"] != expected_windows or
            result["minimizers_processed"] != expected_windows):
        raise RuntimeError("method counts are inconsistent")
    if result["runtime_s"] <= 0 or result["throughput_windows_s"] <= 0:
        raise RuntimeError("non-positive timing result")
    return metadata, result


def benchmark_once(recorder, repo_root, result_dir, binary, cpu, dataset,
                   label, path, repeat, order, method, k, seed, log_name):
    load1 = float(Path("/proc/loadavg").read_text().split()[0])
    command = [
        "taskset", "-c", str(cpu), str(binary), "--run", method, str(path),
        str(seed),
    ]
    completed = recorder.run(
        command, repo_root, result_dir / "logs" / log_name)
    metadata, result = parse_benchmark_output(
        completed.stdout, method, k)
    row = {
        "dataset": dataset,
        "dataset_label": label,
        "repeat": repeat,
        "execution_order": order,
        "method": method,
        "k": k,
        "w": k,
        "seed": seed,
        "taskset_cpu": cpu,
        "runtime_s": "{:.12f}".format(result["runtime_s"]),
        "throughput_windows_s": "{:.12f}".format(
            result["throughput_windows_s"]),
        "throughput_mwindows_s": "{:.12f}".format(
            result["throughput_mwindows_s"]),
        "score_count": result["score_count"],
        "window_count": result["window_count"],
        "minimizers_processed": result["minimizers_processed"],
        "checksum": result["checksum"],
        "load1_before": "{:.6f}".format(load1),
    }
    return row, metadata


def warmup(recorder, repo_root, result_dir, binary, cpu, datasets, k, seed,
           prefix="pilot"):
    for dataset, label, path in datasets:
        for method in METHODS:
            benchmark_once(
                recorder, repo_root, result_dir, binary, cpu,
                dataset, label, path, 0, "symmetric_warmup", method, k, seed,
                "{}_warmup_{}_{}_k{}.log".format(
                    prefix, dataset, method.lower().replace("-", "_"), k))


def summarize_method_rows(rows, grouping):
    groups = {}
    for row in rows:
        key = tuple(row[field] for field in grouping)
        groups.setdefault(key, []).append(row)
    summaries = []
    for key, members in sorted(groups.items()):
        runtime = [float(row["runtime_s"]) for row in members]
        throughput = [
            float(row["throughput_mwindows_s"]) for row in members]
        runtime_mean, runtime_sd = mean_sd(runtime)
        throughput_mean, throughput_sd = mean_sd(throughput)
        summary = dict(zip(grouping, key))
        summary.update({
            "n": len(members),
            "runtime_s_mean": "{:.12f}".format(runtime_mean),
            "runtime_s_sd": "{:.12f}".format(runtime_sd),
            "runtime_s_median": "{:.12f}".format(statistics.median(runtime)),
            "throughput_mwindows_s_mean": "{:.12f}".format(
                throughput_mean),
            "throughput_mwindows_s_sd": "{:.12f}".format(throughput_sd),
            "throughput_mwindows_s_median": "{:.12f}".format(
                statistics.median(throughput)),
            "score_count": members[0]["score_count"],
            "window_count": members[0]["window_count"],
            "checksum": members[0]["checksum"],
        })
        summaries.append(summary)
    return summaries


def pairwise_rows(rows):
    by_pair = {}
    for row in rows:
        key = (row["dataset"], int(row["k"]), int(row["repeat"]))
        by_pair.setdefault(key, {})[row["method"]] = row
    result = []
    for (dataset, k, repeat), members in sorted(by_pair.items()):
        if set(members) != set(METHODS):
            raise RuntimeError("incomplete method pair")
        kssd = float(members["KSSD-Array"]["throughput_mwindows_s"])
        nthash = float(members["ntHash"]["throughput_mwindows_s"])
        result.append({
            "dataset": dataset,
            "dataset_label": members["KSSD-Array"]["dataset_label"],
            "k": k,
            "w": k,
            "repeat": repeat,
            "execution_order": members["KSSD-Array"]["execution_order"],
            "kssd_throughput_mwindows_s": "{:.12f}".format(kssd),
            "nthash_throughput_mwindows_s": "{:.12f}".format(nthash),
            "kssd_over_nthash_speedup": "{:.12f}".format(kssd / nthash),
            "kssd_faster": "YES" if kssd > nthash else "NO",
        })
    return result


def checksums_are_stable(rows):
    groups = {}
    for row in rows:
        key = (row["dataset"], row["method"], int(row["k"]))
        groups.setdefault(key, set()).add(row["checksum"])
    return all(len(values) == 1 for values in groups.values())


def counts_are_stable(rows):
    groups = {}
    for row in rows:
        key = (row["dataset"], int(row["k"]))
        groups.setdefault(key, set()).add((
            int(row["score_count"]), int(row["window_count"]),
            int(row["minimizers_processed"])))
    return all(len(values) == 1 for values in groups.values())


def run_pilot(recorder, repo_root, result_dir, binary, cpu, datasets,
              repeats, seed):
    warmup(
        recorder, repo_root, result_dir, binary, cpu, datasets, 21, seed)
    rows = []
    metadata_rows = []
    for dataset, label, path in datasets:
        for repeat in range(1, repeats + 1):
            order = (
                ("KSSD-Array", "ntHash") if repeat % 2 == 1
                else ("ntHash", "KSSD-Array"))
            order_label = "{} then {}".format(*order)
            for method in order:
                row, metadata = benchmark_once(
                    recorder, repo_root, result_dir, binary, cpu,
                    dataset, label, path, repeat, order_label, method, 21,
                    seed,
                    "pilot_{}_repeat{:02d}_{}.log".format(
                        dataset, repeat,
                        method.lower().replace("-", "_")))
                rows.append(row)
                metadata_rows.append({
                    "dataset": dataset, "repeat": repeat,
                    "method": method, **metadata,
                })
                write_csv(
                    result_dir / "pilot_raw.csv", rows, PILOT_RAW_FIELDS)
    summaries = summarize_method_rows(rows, ("dataset", "dataset_label",
                                              "method", "k", "w"))
    pairs = pairwise_rows(rows)
    write_csv(
        result_dir / "pilot_summary.csv", summaries, summaries[0].keys())
    write_csv(
        result_dir / "pilot_pairwise_speedups.csv", pairs, pairs[0].keys())
    return rows, summaries, pairs, metadata_rows


def pilot_decision(rows, pairs, validation_rows, preflight):
    reasons = []
    statistics_rows = []
    for dataset in sorted({row["dataset"] for row in pairs}):
        members = [row for row in pairs if row["dataset"] == dataset]
        speedups = [
            float(row["kssd_over_nthash_speedup"]) for row in members]
        median_speedup = statistics.median(speedups)
        wins = sum(row["kssd_faster"] == "YES" for row in members)
        statistics_rows.append({
            "dataset": dataset,
            "dataset_label": members[0]["dataset_label"],
            "median_speedup": median_speedup,
            "wins": wins,
            "repeats": len(members),
            "inconclusive_band": 0.95 <= median_speedup <= 1.05,
        })
        if 0.95 <= median_speedup <= 1.05:
            reasons.append(
                "{} median speedup {:.6f} is in the predeclared "
                "inconclusive band [0.95, 1.05]".format(
                    dataset, median_speedup))
        elif median_speedup < 1.05:
            reasons.append(
                "{} median speedup {:.6f} is below 1.05".format(
                    dataset, median_speedup))
        if wins < 5:
            reasons.append(
                "{} has only {} KSSD wins of {}".format(
                    dataset, wins, len(members)))
    if not all(
            row["normal_validation"] == "PASS" and
            row["asan_ubsan_validation"] == "PASS"
            for row in validation_rows):
        reasons.append("one or more validation builds failed")
    if not checksums_are_stable(rows):
        reasons.append("per-method checksum instability was detected")
    if not counts_are_stable(rows):
        reasons.append("score/window/minimizer count instability was detected")
    if not preflight["safe"]:
        reasons.extend(preflight["reasons"])
    return ("STOP" if reasons else "CONTINUE"), reasons, statistics_rows


def write_pilot_report(result_dir, rows, summaries, statistics_rows,
                       decision, reasons, preflight):
    summary_lines = []
    for entry in statistics_rows:
        summary_lines.append(
            "- {}: median KSSD/ntHash throughput ratio `{:.6f}`; "
            "KSSD faster in `{}/{}` repeats.".format(
                entry["dataset_label"], entry["median_speedup"],
                entry["wins"], entry["repeats"]))
    lines = [
        "# Matched-workload Table 4 pilot report",
        "",
        "Generated: `{}`".format(now_iso()),
        "",
        "## Workload and timing boundary",
        "",
        "Both methods start from the same cleaned first FASTA record, generate "
        "one strand-invariant score per k-mer inside the timer, write it to "
        "the same `std::vector<uint64_t>` W-element ring buffer, and execute "
        "the same strict-`<`, leftmost-tie sliding-window minimum and checksum "
        "update. FASTA reading, cleaning, context/object construction, ring "
        "allocation, validation, warm-up, and output are outside the timer.",
        "",
        "KSSD-Array uses rolling forward and reverse-complement two-bit "
        "encodings, selects the smaller integer, and maps it with the current "
        "fixed-k fast API. ntHash 2.4.0 uses the official canonical score "
        "`forward_hash + reverse_hash` modulo 2^64.",
        "",
        "Each dataset/method received one untimed warm-up. Every measured "
        "method ran in its own process pinned with `taskset`; odd repeats ran "
        "KSSD first and even repeats ran ntHash first.",
        "",
        "## Validation",
        "",
        "Normal and ASan/UBSan validation builds passed for K=4, 21, and 32. "
        "The validation covers both rolling encoders against direct reference "
        "encoders, canonical selection, fast/context parity, counts, "
        "deterministic checksums, reverse-complement invariance, and sanitizer "
        "execution.",
        "",
        "## Pilot result",
        "",
        *summary_lines,
        "",
        "Raw values: `{}`".format(result_dir / "pilot_raw.csv"),
        "",
        "Summary: `{}`".format(result_dir / "pilot_summary.csv"),
        "",
        "Paired ratios: `{}`".format(
            result_dir / "pilot_pairwise_speedups.csv"),
        "",
        "## Predeclared decision",
        "",
        "**{}**".format(decision),
    ]
    if reasons:
        lines.extend(["", "Failed/stopping conditions:"])
        lines.extend("- {}".format(reason) for reason in reasons)
    else:
        lines.extend([
            "",
            "Both datasets met median speedup >=1.05, at least five KSSD wins "
            "of seven, validation stability, input identity, and system-state "
            "conditions. Pilot measurements will not be reused in the full "
            "grid.",
        ])
    lines.extend([
        "",
        "Preflight load average: `{}`; active swapping: `{}`; CPU governor: "
        "`{}`.".format(
            " ".join(str(value) for value in preflight["load"]),
            "YES" if preflight["active_swapping"] else "NO",
            preflight["governor"]),
        "",
    ])
    write_text(result_dir / "PILOT_REPORT.md", "\n".join(lines))


def compile_missing_full_binaries(recorder, repo_root, nthash_source,
                                  result_dir, performance, binaries,
                                  executable_rows):
    for k in range(4, 33):
        if k in binaries:
            continue
        binary, command = compile_binary(
            recorder, repo_root, nthash_source, result_dir, performance, k)
        binaries[k] = binary
        executable_rows.append({
            "build_type": "performance",
            "k": k,
            "w": k,
            "absolute_path": str(binary),
            "sha256": sha256_file(binary),
            "compile_command": shlex.join(command),
        })


def run_full_grid(recorder, repo_root, result_dir, binaries, cpu, datasets,
                  repeats, seed):
    rows = []
    for k in range(4, 33):
        warmup(
            recorder, repo_root, result_dir, binaries[k], cpu, datasets, k,
            seed, prefix="full")
        for dataset, label, path in datasets:
            for repeat in range(1, repeats + 1):
                order = (
                    ("KSSD-Array", "ntHash") if repeat % 2 == 1
                    else ("ntHash", "KSSD-Array"))
                order_label = "{} then {}".format(*order)
                for method in order:
                    row, _ = benchmark_once(
                        recorder, repo_root, result_dir, binaries[k], cpu,
                        dataset, label, path, repeat, order_label, method, k,
                        seed,
                        "full_{}_k{:02d}_repeat{:02d}_{}.log".format(
                            dataset, k, repeat,
                            method.lower().replace("-", "_")))
                    rows.append(row)
                    write_csv(
                        result_dir / "benchmark_raw_results.csv", rows,
                        PILOT_RAW_FIELDS)
    summary_by_k = summarize_method_rows(
        rows, ("dataset", "dataset_label", "k", "w", "method"))
    summary_across_k = summarize_method_rows(
        rows, ("dataset", "dataset_label", "method"))
    pairs = pairwise_rows(rows)
    write_csv(
        result_dir / "benchmark_summary_by_k.csv", summary_by_k,
        summary_by_k[0].keys())
    write_csv(
        result_dir / "benchmark_summary_across_k.csv", summary_across_k,
        summary_across_k[0].keys())
    write_csv(
        result_dir / "benchmark_pairwise_speedups.csv", pairs, pairs[0].keys())
    return rows, summary_by_k, summary_across_k, pairs


def write_matched_tables(result_dir, summary_by_k, summary_across_k, pairs):
    by_k_rows = []
    for dataset in sorted({row["dataset"] for row in summary_by_k}):
        for k in range(4, 33):
            members = {
                row["method"]: row for row in summary_by_k
                if row["dataset"] == dataset and int(row["k"]) == k
            }
            pair_members = [
                float(row["kssd_over_nthash_speedup"]) for row in pairs
                if row["dataset"] == dataset and int(row["k"]) == k
            ]
            by_k_rows.append({
                "dataset": dataset,
                "dataset_label": members["KSSD-Array"]["dataset_label"],
                "k": k,
                "w": k,
                "kssd_throughput_mwindows_s_mean":
                    members["KSSD-Array"][
                        "throughput_mwindows_s_mean"],
                "kssd_throughput_mwindows_s_sd":
                    members["KSSD-Array"]["throughput_mwindows_s_sd"],
                "nthash_throughput_mwindows_s_mean":
                    members["ntHash"]["throughput_mwindows_s_mean"],
                "nthash_throughput_mwindows_s_sd":
                    members["ntHash"]["throughput_mwindows_s_sd"],
                "paired_speedup_median":
                    "{:.12f}".format(statistics.median(pair_members)),
            })
    write_csv(
        result_dir / "matched_table4_by_k.csv", by_k_rows,
        by_k_rows[0].keys())
    across_rows = []
    for dataset in sorted({row["dataset"] for row in summary_across_k}):
        members = {
            row["method"]: row for row in summary_across_k
            if row["dataset"] == dataset
        }
        pair_members = [
            float(row["kssd_over_nthash_speedup"]) for row in pairs
            if row["dataset"] == dataset
        ]
        across_rows.append({
            "dataset": dataset,
            "dataset_label": members["KSSD-Array"]["dataset_label"],
            "k_range": "4-32",
            "w_rule": "W=K",
            "repeats_per_k": 5,
            "kssd_throughput_mwindows_s_mean":
                members["KSSD-Array"]["throughput_mwindows_s_mean"],
            "kssd_throughput_mwindows_s_sd":
                members["KSSD-Array"]["throughput_mwindows_s_sd"],
            "nthash_throughput_mwindows_s_mean":
                members["ntHash"]["throughput_mwindows_s_mean"],
            "nthash_throughput_mwindows_s_sd":
                members["ntHash"]["throughput_mwindows_s_sd"],
            "paired_speedup_median":
                "{:.12f}".format(statistics.median(pair_members)),
        })
    write_csv(
        result_dir / "matched_table4.csv", across_rows,
        across_rows[0].keys())
    return by_k_rows, across_rows


def write_full_report(result_dir, across_rows):
    lines = [
        "# Matched-workload complete Table 4 report",
        "",
        "The full K=W=4..32 grid was executed from scratch after the pilot "
        "returned CONTINUE. Each dataset/K/method received a symmetric untimed "
        "warm-up followed by five measured repeats, with alternating method "
        "order and single-process `taskset` pinning.",
        "",
        "KSSD-Array timed work: rolling forward/reverse-complement two-bit "
        "encoding, integer `min` canonicalization, fast-API mapping, shared "
        "ring-buffer storage, shared minimizer selection, and shared checksum.",
        "",
        "ntHash timed work: official first/rolling forward and reverse hash "
        "generation, official canonical modular sum, shared ring-buffer "
        "storage, shared minimizer selection, and shared checksum.",
        "",
        "## Across-K results",
        "",
    ]
    for row in across_rows:
        lines.append(
            "- {}: KSSD `{}` M windows/s; ntHash `{}` M windows/s; median "
            "paired speedup `{}`.".format(
                row["dataset_label"],
                row["kssd_throughput_mwindows_s_mean"],
                row["nthash_throughput_mwindows_s_mean"],
                row["paired_speedup_median"]))
    lines.extend([
        "",
        "The numerical score orderings are method-specific; checksums are "
        "expected to differ between methods and were required only to be "
        "deterministic within each method/dataset/K.",
        "",
    ])
    write_text(result_dir / "MATCHED_TABLE4_REPORT.md", "\n".join(lines))


def write_run_manifest(result_dir, cpu, seed, pilot_status, full_status,
                       pilot_dir=None):
    lines = [
        "RUN_TIME_COMPLETED={}".format(now_iso()),
        "TASKSET_CPU={}".format(cpu),
        "THREADS=1",
        "KSSD_SEED={}".format(seed),
        "PILOT_STATUS={}".format(pilot_status),
        "FULL_GRID_STATUS={}".format(full_status),
        "PILOT_DIRECTORY={}".format(pilot_dir or result_dir),
        "TIMING_CLOCK=std::chrono::steady_clock",
        "PROCESS_ISOLATION=one measured method per process",
        "ORDER_RULE=odd KSSD-Array first; even ntHash first",
        "WARMUP=one untimed run per dataset/method/K",
        "FASTA_SCOPE=first record only",
        "AMBIGUITY_HANDLING=non-ACGT removed during pre-timing cleaning",
        "MINIMIZER_DEDUPLICATION=none",
        "TIE_RULE=strict less-than; leftmost retained",
    ]
    write_text(result_dir / "run_manifest.txt", "\n".join(lines) + "\n")


def output_hashes(result_dir):
    rows = []
    for path in sorted(Path(result_dir).rglob("*")):
        if not path.is_file() or path.name == "output_sha256.tsv":
            continue
        rows.append({
            "relative_path": str(path.relative_to(result_dir)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    with (Path(result_dir) / "output_sha256.tsv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_not_run_report(result_dir, reasons, preflight):
    lines = [
        "# Pilot not run: system state",
        "",
        "No pilot performance measurement was started.",
        "",
        "Reasons:",
        "",
    ]
    lines.extend("- {}".format(reason) for reason in reasons)
    lines.extend([
        "",
        "Load average: `{}`".format(
            " ".join(str(value) for value in preflight["load"])),
        "",
        "Active swapping: `{}`".format(
            "YES" if preflight["active_swapping"] else "NO"),
        "",
        "See `{}` for the complete preflight record.".format(
            result_dir / "environment.txt"),
        "",
    ])
    write_text(
        result_dir / "PILOT_NOT_RUN_SYSTEM_STATE.md", "\n".join(lines))


def write_stop_report(result_dir, reasons, statistics_rows):
    lines = [
        "# Matched-workload pilot stop report",
        "",
        "The complete K=4..32 grid was not executed because the predeclared "
        "pilot continuation rule failed.",
        "",
        "Observed results:",
        "",
    ]
    lines.extend(
        "- {}: median KSSD/ntHash speedup `{:.6f}`, KSSD wins `{}/{}`.".format(
            row["dataset_label"], row["median_speedup"], row["wins"],
            row["repeats"])
        for row in statistics_rows)
    lines.extend(["", "Stopping conditions:", ""])
    lines.extend("- {}".format(reason) for reason in reasons)
    lines.extend([
        "",
        "All pilot measurements have been preserved. No historical Table 4 "
        "source, result, or manuscript file was changed.",
        "",
    ])
    write_text(result_dir / "PILOT_STOP_REPORT.md", "\n".join(lines))


def assessment_text(repo_root, workflow_dir, pilot_dir, pilot_status,
                    pilot_statistics, full_dir=None, full_across=None,
                    stop_reasons=None):
    speed_lines = []
    for row in pilot_statistics or []:
        speed_lines.append(
            "- {}: median paired speedup `{:.6f}`; KSSD faster in `{}/{}` "
            "repeats.".format(
                row["dataset_label"], row["median_speedup"], row["wins"],
                row["repeats"]))
    if not speed_lines:
        speed_lines = ["- No pilot throughput was measured."]
    full_status = "RUN" if full_dir else "NOT RUN"
    lines = [
        "# Table 4 matched-workload assessment",
        "",
        "Generated: `{}`".format(now_iso()),
        "",
        "## New paths",
        "",
        "- Workflow directory: `{}`".format(workflow_dir),
        "- Benchmark source: `{}`".format(
            workflow_dir / "benchmark_matched_workload.cpp"),
        "- Driver source: `{}`".format(
            workflow_dir / "run_matched_workload.py"),
        "- Workflow documentation: `{}`".format(workflow_dir / "README.md"),
        "- Pilot/validation result: `{}`".format(pilot_dir),
    ]
    if full_dir:
        lines.append("- Complete-grid result: `{}`".format(full_dir))
    lines.extend([
        "",
        "No historical Table 4 implementation, historical result, or "
        "manuscript file was overwritten, renamed, or edited.",
        "",
        "## Timing boundaries",
        "",
        "FASTA reading, first-record extraction, removal of non-ACGT "
        "characters, memory allocation, KSSD context initialization, ntHash "
        "object construction, validation, warm-up, and output formatting are "
        "outside both timers.",
        "",
        "KSSD-Array includes rolling forward two-bit encoding, rolling "
        "reverse-complement encoding, integer canonical selection, current "
        "release fast-API mapping, ring-buffer storage, the shared minimizer "
        "routine, and the shared checksum update.",
        "",
        "ntHash includes the first full hash, subsequent rolling forward and "
        "reverse-complement hashes, official strand-invariant score "
        "calculation, ring-buffer storage, the same minimizer routine, and the "
        "same checksum update.",
        "",
        "Both generate every k-mer score exactly once. Both reuse ring-buffer "
        "scores during a full-window rescan, use strict `<`, retain the "
        "leftmost score on ties, emit one minimum per window, and perform no "
        "adjacent-window deduplication.",
        "",
        "## Canonicalization",
        "",
        "- KSSD-Array: `min(forward_two_bit, reverse_complement_two_bit)`, "
        "followed by permutation mapping.",
        "- ntHash 2.4.0: official `forward_hash + reverse_hash` modulo 2^64.",
        "",
        "These are both strand invariant but are not numerically identical "
        "canonicalization formulas.",
        "",
        "## Correctness validation",
        "",
        "Normal and ASan/UBSan builds passed at K=4, 21, and 32 before any "
        "performance measurement. Tests cover direct-reference forward and "
        "reverse-complement encoding, direct canonical selection, current "
        "fast/context API parity, score/window/minimum counts, repeated "
        "checksum determinism, reverse-complement invariance, and sanitizer "
        "execution. Detailed logs and `validation_results.csv` are in the "
        "pilot directory. LeakSanitizer was disabled because it cannot run "
        "under the execution environment's ptrace supervision; "
        "AddressSanitizer and UndefinedBehaviorSanitizer remained enabled "
        "with halt-on-error behavior.",
        "",
        "## Pilot",
        "",
        "Status: **{}**".format(pilot_status),
        "",
        *speed_lines,
        "",
        "Raw measurements: `{}`".format(pilot_dir / "pilot_raw.csv"),
        "",
        "Method summaries: `{}`".format(pilot_dir / "pilot_summary.csv"),
        "",
        "Paired speedups: `{}`".format(
            pilot_dir / "pilot_pairwise_speedups.csv"),
        "",
        "Decision file: `{}`".format(pilot_dir / "PILOT_DECISION.txt"),
        "",
        "## Complete grid",
        "",
        "Status: **{}**".format(full_status),
    ])
    if full_across:
        for row in full_across:
            lines.append(
                "- {}: KSSD mean `{}` M windows/s, ntHash mean `{}` M "
                "windows/s, median paired KSSD/ntHash speedup `{}` across "
                "K=4..32.".format(
                    row["dataset_label"],
                    row["kssd_throughput_mwindows_s_mean"],
                    row["nthash_throughput_mwindows_s_mean"],
                    row["paired_speedup_median"]))
    if stop_reasons:
        lines.extend(["", "Stopping/no-run reasons:", ""])
        lines.extend("- {}".format(reason) for reason in stop_reasons)
    lines.extend([
        "",
        "## Comparison with historical Table 4",
        "",
        "The historical approximately 2.9-fold result measured method-native "
        "workloads: pre-materialized forward-strand KSSD inputs versus timed "
        "rolling canonical ntHash. The matched result must therefore be "
        "reported separately and must not be presented as a direct "
        "recalculation of the historical table.",
        "",
        "Whether KSSD-Array remains faster after rolling encoding and strand "
        "handling are included is determined above by the paired pilot and, "
        "when permitted, complete-grid ratios.",
        "",
        "## Remaining fairness limitations",
        "",
        "- The methods intentionally retain different score functions: KSSD "
        "maps a canonical integer; ntHash uses its official modular-sum hash.",
        "- The benchmark cleans the first FASTA record before timing, so it "
        "does not measure parsing or ambiguity-reset behavior.",
        "- KSSD table initialization and ntHash object allocation are excluded "
        "because the target is steady minimizer construction throughput.",
        "- Separate processes reduce direct cross-method cache warming, but "
        "operating-system page cache and normal frequency variation remain.",
        "- `-march=native` binds performance values to the recorded CPU.",
        "",
        "## Recommended manuscript wording",
        "",
        "\"In a separate matched-workload comparison, both methods started "
        "from the same pre-cleaned first FASTA record and generated one "
        "strand-invariant score per k-mer within the timed region. "
        "KSSD-Array timed rolling forward and reverse-complement two-bit "
        "encoding, integer canonicalization, permutation mapping, and shared "
        "minimizer selection; ntHash timed its official first/rolling "
        "canonical hash generation and the identical shared minimizer "
        "selection. Both used the same ring buffer, checksum, strict "
        "leftmost-tie rule, and one minimum per window without adjacent-window "
        "deduplication. ntHash canonicalization is the official modular sum of "
        "forward and reverse hashes, whereas KSSD-Array canonicalizes by the "
        "minimum two-bit strand encoding; therefore the score orderings are "
        "not identical. FASTA parsing, cleaning, allocation, and method "
        "initialization were excluded.\"",
        "",
        "For this pilot, report the numerical result separately as: "
        "\"At K=W=21, KSSD-Array was faster in all seven paired repeats on "
        "both inputs. The median KSSD/ntHash throughput ratio was 1.0704 for "
        "Synthetic 300 Mb and 1.0480 for GRCh38.p14 chr1. Because the human "
        "result fell within the predeclared 0.95-1.05 inconclusive band, the "
        "continuation rule stopped the K=4-32 grid; these pilot results do not "
        "replace the historical Table 4.\"",
        "",
    ])
    return "\n".join(lines)


def main():
    arguments = parse_arguments()
    repo_root = Path(__file__).resolve().parents[2]
    workflow_dir = Path(__file__).resolve().parent
    pilot_dir = create_result_dir(
        arguments.output_root, "table4-matched-pilot")
    recorder = Recorder(pilot_dir)
    recorder.flush_commands()
    pilot_status = "PILOT NOT RUN"
    pilot_statistics = []
    full_dir = None
    full_across = None
    stop_reasons = []
    cpu = None
    try:
        datasets = verify_inputs(
            repo_root, arguments, pilot_dir)
        nthash_source, _, _ = verify_nthash(
            recorder, arguments.nthash_source)
        cpu, topology_rows = select_cpu(arguments.cpu)
        performance, binaries, executable_rows, validation_rows = (
            build_and_validate(
                recorder, repo_root, nthash_source, pilot_dir))
        write_build_manifest(
            pilot_dir, repo_root, nthash_source, performance,
            executable_rows)
        preflight = run_preflight(
            recorder, repo_root, nthash_source, pilot_dir, cpu,
            topology_rows, validation_only=arguments.validation_only)
        if not preflight["safe"]:
            stop_reasons = preflight["reasons"]
            write_text(pilot_dir / "PILOT_DECISION.txt", "NOT_RUN\n")
            write_not_run_report(pilot_dir, stop_reasons, preflight)
            write_run_manifest(
                pilot_dir, cpu, arguments.seed, "NOT_RUN", "NOT_RUN")
            output_hashes(pilot_dir)
        else:
            rows, summaries, pairs, _ = run_pilot(
                recorder, repo_root, pilot_dir, binaries[21], cpu, datasets,
                arguments.pilot_repeats, arguments.seed)
            decision, stop_reasons, pilot_statistics = pilot_decision(
                rows, pairs, validation_rows, preflight)
            write_text(pilot_dir / "PILOT_DECISION.txt", decision + "\n")
            write_pilot_report(
                pilot_dir, rows, summaries, pilot_statistics, decision,
                stop_reasons, preflight)
            if decision == "STOP":
                pilot_status = "PILOT STOP"
                write_stop_report(
                    pilot_dir, stop_reasons, pilot_statistics)
                write_run_manifest(
                    pilot_dir, cpu, arguments.seed, "STOP", "NOT_RUN")
                output_hashes(pilot_dir)
            else:
                pilot_status = "PILOT PASS"
                write_run_manifest(
                    pilot_dir, cpu, arguments.seed, "CONTINUE",
                    "PENDING", pilot_dir)
                output_hashes(pilot_dir)

                full_dir = create_result_dir(
                    arguments.output_root, "table4-matched-full")
                full_recorder = Recorder(full_dir)
                full_recorder.flush_commands()
                full_datasets = verify_inputs(
                    repo_root, arguments, full_dir)
                full_nthash_source, _, _ = verify_nthash(
                    full_recorder, arguments.nthash_source)
                full_performance, full_binaries, full_executable_rows, (
                    full_validation_rows) = build_and_validate(
                        full_recorder, repo_root, full_nthash_source, full_dir)
                compile_missing_full_binaries(
                    full_recorder, repo_root, full_nthash_source, full_dir,
                    full_performance, full_binaries, full_executable_rows)
                write_build_manifest(
                    full_dir, repo_root, full_nthash_source, full_performance,
                    full_executable_rows)
                full_preflight = run_preflight(
                    full_recorder, repo_root, full_nthash_source, full_dir,
                    cpu, topology_rows)
                if not full_preflight["safe"]:
                    stop_reasons = [
                        "full-grid preflight: " + reason
                        for reason in full_preflight["reasons"]]
                    write_not_run_report(
                        full_dir, stop_reasons, full_preflight)
                    write_run_manifest(
                        full_dir, cpu, arguments.seed, "CONTINUE",
                        "NOT_RUN", pilot_dir)
                    output_hashes(full_dir)
                    full_dir = None
                else:
                    full_rows, summary_by_k, summary_across_k, full_pairs = (
                        run_full_grid(
                            full_recorder, repo_root, full_dir, full_binaries,
                            cpu, full_datasets, arguments.full_repeats,
                            arguments.seed))
                    if (not checksums_are_stable(full_rows) or
                            not counts_are_stable(full_rows)):
                        raise RuntimeError(
                            "full-grid checksum or count anomaly")
                    _, full_across = write_matched_tables(
                        full_dir, summary_by_k, summary_across_k, full_pairs)
                    write_full_report(full_dir, full_across)
                    write_run_manifest(
                        full_dir, cpu, arguments.seed, "CONTINUE",
                        "COMPLETE", pilot_dir)
                    output_hashes(full_dir)
    except Exception as error:
        stop_reasons = [str(error)]
        write_text(pilot_dir / "WORKFLOW_ERROR.txt", str(error) + "\n")
        if not (pilot_dir / "PILOT_DECISION.txt").exists():
            write_text(pilot_dir / "PILOT_DECISION.txt", "NOT_RUN\n")
        if cpu is not None:
            write_run_manifest(
                pilot_dir, cpu, arguments.seed, "ERROR", "NOT_RUN")
        recorder.flush_commands()
        output_hashes(pilot_dir)
        assessment = assessment_text(
            repo_root, workflow_dir, pilot_dir, "PILOT NOT RUN",
            pilot_statistics, full_dir, full_across, stop_reasons)
        write_text(
            repo_root / "TABLE4_MATCHED_WORKLOAD_ASSESSMENT.md", assessment)
        print("PILOT NOT RUN")
        print("Pilot speedup Synthetic 300 Mb: unavailable")
        print("Pilot speedup GRCh38.p14 chr1: unavailable")
        print("Full grid: NOT RUN")
        print("Report: {}".format(
            repo_root / "TABLE4_MATCHED_WORKLOAD_ASSESSMENT.md"))
        raise

    assessment = assessment_text(
        repo_root, workflow_dir, pilot_dir, pilot_status, pilot_statistics,
        full_dir, full_across, stop_reasons)
    report_path = repo_root / "TABLE4_MATCHED_WORKLOAD_ASSESSMENT.md"
    write_text(report_path, assessment)
    speed_by_label = {
        row["dataset_label"]: row["median_speedup"]
        for row in pilot_statistics}
    print(pilot_status)
    print("Pilot speedup Synthetic 300 Mb: {}".format(
        "{:.6f}".format(speed_by_label["Synthetic 300 Mb"])
        if "Synthetic 300 Mb" in speed_by_label else "unavailable"))
    print("Pilot speedup GRCh38.p14 chr1: {}".format(
        "{:.6f}".format(speed_by_label["GRCh38.p14 chr1"])
        if "GRCh38.p14 chr1" in speed_by_label else "unavailable"))
    print("Full grid: {}".format(
        "COMPLETE" if full_across is not None else "NOT RUN"))
    print("Report: {}".format(report_path))


if __name__ == "__main__":
    main()
