#!/usr/bin/env python3
"""Build and run the portable Figure 3 multithread benchmark workflow."""

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
from datetime import datetime, timezone
from pathlib import Path


METHODS = ("KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "wyhash")
RAW_NAME = "figure3_multithread_raw.csv"
SUMMARY_NAME = "figure3_multithread_summary.csv"
SOURCE_RELATIVE = Path(
    "reproducibility/figure3/benchmark_multithread_k21.c")
FIXTURE_GENERATOR = Path("tests/fixture_generators/generate_test_fixtures.sh")
FIGURE3_FIXTURE = Path("reproducibility/figure3/fixtures/figure3_smoke.fa")


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+")
    parser.add_argument("--dataset-names", nargs="+")
    parser.add_argument("--k", type=int)
    parser.add_argument("--w-values", nargs="+", type=int)
    parser.add_argument("--threads", nargs="+", type=int)
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir")
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def run_command(command, cwd, log_path=None, environment=None):
    completed = subprocess.run(
        command, cwd=str(cwd), env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if log_path is not None:
        environment_lines = []
        if environment is not None:
            for name in ("OMP_NUM_THREADS", "OMP_DYNAMIC", "OMP_PROC_BIND",
                         "OMP_PLACES", "OMP_SCHEDULE"):
                environment_lines.append(
                    "{}={}".format(name, environment.get(name, "<unset>")))
        log_path.write_text(
            "COMMAND\n{}\n\nENVIRONMENT\n{}\n\nSTDOUT\n{}\nSTDERR\n{}".format(
                shlex.join([str(part) for part in command]),
                "\n".join(environment_lines), completed.stdout,
                completed.stderr),
            encoding="utf-8")
    if completed.returncode != 0:
        detail = " (see {})".format(log_path) if log_path else ""
        raise RuntimeError("command failed{}: {}".format(
            detail, shlex.join([str(part) for part in command])))
    return completed


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cpu_description():
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(
                encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or platform.machine()


def fasta_record_count(path):
    opener = gzip.open if path.suffix == ".gz" else open
    count = 0
    with opener(path, "rt", encoding="ascii", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                count += 1
    return count


def resolve_datasets(arguments, repo_root, generated_root=None):
    if arguments.smoke:
        if arguments.datasets or arguments.dataset_names:
            raise ValueError("--smoke uses exactly the source-generated fixture")
        if generated_root is None:
            raise ValueError("generated fixture root is required for --smoke")
        return [generated_root / FIGURE3_FIXTURE], ["Figure3Smoke"]
    if arguments.datasets:
        paths = [Path(value).expanduser().resolve()
                 for value in arguments.datasets]
        if arguments.dataset_names is None or len(paths) != len(
                arguments.dataset_names):
            raise ValueError("--dataset-names must match --datasets")
        return paths, list(arguments.dataset_names)
    if arguments.dataset_names:
        raise ValueError("--dataset-names requires --datasets")
    metadata = json.loads((repo_root / "reproducibility/data/datasets.json").read_text(
        encoding="utf-8"))
    names = ["Synthetic_300M", "Human_GRCh38"]
    data_root = Path(os.environ.get(
        "KSSD_DATA_DIR", repo_root / "reproducibility/data/external")).expanduser()
    paths = [data_root / metadata["datasets"][name]["filename"]
             for name in names]
    return [path.resolve() for path in paths], names


def validate_request(arguments, repo_root, output_dir, generated_root=None):
    if arguments.smoke:
        if any(value is not None for value in (
                arguments.k, arguments.w_values, arguments.threads,
                arguments.repeats)):
            raise ValueError("--smoke cannot be combined with grid options")
        k, w_values, threads, repeats = 21, [20], [1, 2], 1
        result_status = "functional_smoke_not_formal_performance"
    else:
        k = 21 if arguments.k is None else arguments.k
        if arguments.w_values is None or arguments.threads is None or \
                arguments.repeats is None:
            raise ValueError(
                "formal runs require --w-values, --threads, and --repeats")
        w_values = list(arguments.w_values)
        threads = list(arguments.threads)
        repeats = arguments.repeats
        result_status = "formal_measurement"
    if not 1 <= k <= 32:
        raise ValueError("k must be within 1..32")
    if any(value < 1 for value in w_values):
        raise ValueError("w values must be positive")
    if any(value < 1 for value in threads) or len(set(threads)) != len(threads):
        raise ValueError("thread values must be positive and unique")
    if repeats < 1:
        raise ValueError("repeats must be positive")
    datasets, names = resolve_datasets(arguments, repo_root, generated_root)
    missing = [str(path) for path in datasets if not path.is_file()]
    if missing:
        raise ValueError(
            "required dataset file(s) are missing: {}. Supply --datasets, set "
            "KSSD_DATA_DIR, or populate reproducibility/data/external".format(", ".join(missing)))
    if output_dir == repo_root or repo_root in output_dir.parents:
        raise ValueError("generated output must be outside the repository")
    return (datasets, names, k, w_values, threads, repeats, result_status)


def compile_benchmark(repo_root, output_dir, compiler, k, w, logs):
    binary = output_dir / "bin/benchmark_k{}_w{}".format(k, w)
    flags = [
        "-O3", "-march=native", "-std=c11", "-Wall", "-Wextra",
        "-Wpedantic", "-fopenmp", "-DK={}".format(k),
        "-DW={}".format(w)]
    command = [compiler] + flags + [
        "-Iinclude", str(SOURCE_RELATIVE), "-Lbuild", "-Wl,-Bstatic",
        "-lkssd_array", "-Wl,-Bdynamic", "-lxxhash", "-lz", "-lm",
        "-fopenmp", "-o", str(binary)]
    run_command(command, repo_root,
                logs / "compile_k{}_w{}.log".format(k, w))
    return binary, command, flags


def parse_benchmark_output(text, expected_k, expected_w,
                           expected_repeat, expected_threads):
    metadata = None
    parity = None
    results = []
    for line in text.splitlines():
        fields = line.split("\t")
        if fields[0] == "META" and len(fields) == 12:
            metadata = {
                "valid_bases": int(fields[1]),
                "ambiguous_bases_skipped": int(fields[2]),
                "valid_kmers": int(fields[3]),
                "valid_windows": int(fields[4]),
                "k": int(fields[5]), "w": int(fields[6]),
                "repeat": int(fields[7]), "seed": int(fields[8]),
                "requested_threads": int(fields[9]),
                "observed_threads": int(fields[10]),
                "openmp_macro": int(fields[11]),
            }
        elif fields[0] == "PARITY" and len(fields) == 3:
            parity = {"status": fields[1], "samples": int(fields[2])}
        elif fields[0] == "RESULT" and len(fields) == 13:
            results.append({
                "method": fields[1], "runtime_s": float(fields[2]),
                "throughput_windows_s": float(fields[3]),
                "valid_kmers": int(fields[4]),
                "valid_windows": int(fields[5]),
                "minimizers": int(fields[6]), "checksum": fields[7],
                "coverage_checksum": fields[8],
                "requested_threads": int(fields[9]),
                "observed_threads": int(fields[10]),
                "nonempty_workers": int(fields[11]),
                "processed_windows": int(fields[12]),
            })
    if metadata is None or parity is None:
        raise RuntimeError("benchmark output lacks META or PARITY")
    if (metadata["k"], metadata["w"], metadata["repeat"]) != (
            expected_k, expected_w, expected_repeat):
        raise RuntimeError("benchmark reported unexpected k/w/repeat")
    if metadata["requested_threads"] != expected_threads or \
            metadata["observed_threads"] != expected_threads:
        raise RuntimeError("requested and observed OpenMP thread counts differ")
    if parity["status"] != "PASS" or parity["samples"] < 1:
        raise RuntimeError("KSSD fast/context parity failed")
    if len(results) != 5 or {row["method"] for row in results} != set(METHODS):
        raise RuntimeError("benchmark did not emit exactly the five methods")
    expected_kmers = metadata["valid_bases"] - expected_k + 1
    expected_windows = expected_kmers - expected_w + 1
    if metadata["valid_kmers"] != expected_kmers or \
            metadata["valid_windows"] != expected_windows:
        raise RuntimeError("metadata k-mer/window counts are inconsistent")
    for row in results:
        if row["valid_kmers"] != expected_kmers or \
                row["valid_windows"] != expected_windows:
            raise RuntimeError("method input counts are inconsistent")
        if row["minimizers"] != expected_windows or \
                row["processed_windows"] != expected_windows:
            raise RuntimeError("a window was lost or processed twice")
        if row["requested_threads"] != expected_threads or \
                row["observed_threads"] != expected_threads:
            raise RuntimeError("a method used an unexpected thread count")
        if row["nonempty_workers"] != min(expected_threads, expected_windows):
            raise RuntimeError("unexpected empty/non-empty worker count")
        if row["runtime_s"] <= 0 or row["throughput_windows_s"] <= 0:
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


def summarize(raw_rows, result_status):
    groups = {}
    for row in raw_rows:
        key = (row["dataset"], row["k"], row["w"],
               row["requested_threads"], row["method"])
        groups.setdefault(key, []).append(row)
    summary = []
    for key in sorted(groups):
        dataset, k, w, threads, method = key
        rows = groups[key]
        runtime_mean, runtime_sd = mean_sd(
            [float(row["runtime_s"]) for row in rows])
        throughput_mean, throughput_sd = mean_sd(
            [float(row["throughput_mwindows_s"]) for row in rows])
        first = rows[0]
        summary.append({
            "result_status": result_status, "dataset": dataset,
            "k": k, "w": w, "threads": threads, "method": method,
            "runtime_s_mean": "{:.12f}".format(runtime_mean),
            "runtime_s_sd": "{:.12f}".format(runtime_sd),
            "throughput_mwindows_s_mean": "{:.12f}".format(throughput_mean),
            "throughput_mwindows_s_sd": "{:.12f}".format(throughput_sd),
            "valid_kmers": first["valid_kmers"],
            "valid_windows": first["valid_windows"],
            "minimizers": first["minimizers"], "n": len(rows),
        })
    return summary


def verify_thread_consistency(raw_rows):
    groups = {}
    for row in raw_rows:
        key = (row["dataset"], row["k"], row["w"], row["method"])
        groups.setdefault(key, []).append(row)
    checks = []
    invariant_fields = (
        "dataset_sha256", "valid_bases", "ambiguous_bases_skipped",
        "valid_kmers", "valid_windows", "minimizers", "checksum",
        "coverage_checksum", "tie_handling", "adjacent_window_deduplication")
    for key, rows in sorted(groups.items()):
        baseline = min(rows, key=lambda row: int(row["requested_threads"]))
        for row in rows:
            if any(row[field] != baseline[field] for field in invariant_fields):
                raise RuntimeError(
                    "thread consistency failed for {}".format(key))
        checks.append({
            "dataset": key[0], "k": key[1], "w": key[2],
            "method": key[3],
            "thread_counts": sorted({int(row["requested_threads"])
                                     for row in rows}),
            "result": "PASS",
        })
    return checks


def parse_figure2_checksums(log_path):
    results = {}
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        fields = line.split("\t")
        if fields[0] == "RESULT" and len(fields) == 8:
            results[fields[1]] = {
                "valid_kmers": int(fields[4]),
                "valid_windows": int(fields[5]),
                "minimizers": int(fields[6]),
                "checksum": fields[7],
            }
    return results


def verify_figure2_equivalence(repo_root, output_dir, fixture, raw_rows, seed,
                               logs):
    figure2_output = output_dir / "figure2_equivalence"
    command = [
        sys.executable,
        str(repo_root / "reproducibility/figure2/run_figure2_single_thread.py"),
        "--datasets", str(fixture), "--dataset-names", "Figure3Smoke",
        "--k-values", "21", "--w-values", "20", "--repeats", "1",
        "--seed", str(seed), "--output-dir", str(figure2_output)]
    run_command(command, repo_root, logs / "figure2_equivalence.log")
    with (figure2_output / "figure2_single_thread_raw.csv").open(
            newline="", encoding="utf-8") as handle:
        figure2_rows = list(csv.DictReader(handle))
    if len(figure2_rows) != 5:
        raise RuntimeError("Figure 2 equivalence run did not emit five rows")
    checksums = parse_figure2_checksums(figure2_rows[0]["log_file"])
    figure3_rows = {
        row["method"]: row for row in raw_rows
        if int(row["requested_threads"]) == 1
    }
    details = []
    for figure2_row in figure2_rows:
        method = figure2_row["method"]
        figure3_row = figure3_rows[method]
        checksum_row = checksums[method]
        comparisons = {
            "valid_bases": (figure2_row["valid_bases"],
                            figure3_row["valid_bases"]),
            "ambiguous_bases_skipped": (
                figure2_row["ambiguous_bases_skipped"],
                figure3_row["ambiguous_bases_skipped"]),
            "valid_kmers": (figure2_row["valid_kmers"],
                            figure3_row["valid_kmers"]),
            "valid_windows": (figure2_row["valid_windows"],
                              figure3_row["valid_windows"]),
            "minimizers": (figure2_row["minimizers"],
                           figure3_row["minimizers"]),
            "checksum": (checksum_row["checksum"], figure3_row["checksum"]),
        }
        if any(str(left) != str(right)
               for left, right in comparisons.values()):
            raise RuntimeError(
                "Figure 2/Figure 3 mismatch for {}".format(method))
        details.append({"method": method, "result": "PASS",
                        "comparisons": comparisons})
    return command, details, figure2_output


def load_snapshot():
    try:
        load_average = list(os.getloadavg())
    except OSError:
        load_average = None
    load_text = None
    load_path = Path("/proc/loadavg")
    if load_path.is_file():
        load_text = load_path.read_text(
            encoding="ascii", errors="replace").strip()
    return {
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "logical_cpus": os.cpu_count(),
        "load_average_1_5_15": load_average,
        "proc_loadavg": load_text,
    }


def main():
    arguments = parse_arguments()
    repo_root = Path(__file__).resolve().parents[2]
    if arguments.output_dir:
        output_dir = Path(arguments.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(tempfile.mkdtemp(
            prefix="kssd-figure3-smoke-" if arguments.smoke
            else "kssd-figure3-run-"))
    reserved = [output_dir / name for name in (
        RAW_NAME, SUMMARY_NAME, "build_manifest.txt", "run_manifest.txt",
        "figure3_multithread_k21.png", "figure3_multithread_k21.pdf")]
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
            prefix="kssd-figure3-generated-fixtures-")
        generated_root = Path(fixture_workspace.name)
        run_command([
            str(repo_root / FIXTURE_GENERATOR),
            "--output-dir", str(generated_root), "--seed", "42",
        ], repo_root, logs / "generate_fixtures.log")
    (datasets, names, k, w_values, thread_values, repeats,
     result_status) = validate_request(
         arguments, repo_root, output_dir, generated_root)

    dataset_records = []
    for path, name in zip(datasets, names):
        dataset_records.append({
            "label": name, "path": str(path), "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "fasta_record_count": fasta_record_count(path)})
    run_command(["make", "build/libkssd_array.a"], repo_root,
                logs / "build_library.log")
    compiler = os.environ.get("CC", "cc")
    compiler_version = run_command(
        [compiler, "--version"], repo_root).stdout.splitlines()[0]
    commit = run_command(
        ["git", "rev-parse", "HEAD"], repo_root).stdout.strip()
    source_path = repo_root / SOURCE_RELATIVE
    library_path = repo_root / "build/libkssd_array.a"
    compile_records = []
    executed_commands = []
    raw_rows = []
    parity_samples = []
    openmp_macros = set()
    openmp_runtime = None

    for w in w_values:
        binary, compile_command, flags = compile_benchmark(
            repo_root, output_dir, compiler, k, w, logs)
        ldd_output = run_command(["ldd", str(binary)], repo_root).stdout
        if openmp_runtime is None:
            openmp_runtime = "\n".join(
                line.strip() for line in ldd_output.splitlines()
                if "gomp" in line.lower() or "omp" in line.lower()) or "not identified"
        compile_records.append({
            "k": k, "w": w, "binary": str(binary),
            "binary_sha256": sha256_file(binary), "flags": flags,
            "command": compile_command, "ldd": ldd_output})
        for dataset, dataset_record in zip(datasets, dataset_records):
            for threads in thread_values:
                for repeat in range(1, repeats + 1):
                    log_path = logs / (
                        "run_{}_k{}_w{}_threads{}_repeat{}.log".format(
                            dataset_record["label"], k, w, threads, repeat))
                    command = [str(binary), str(dataset), str(repeat),
                               str(arguments.seed), str(threads)]
                    environment = os.environ.copy()
                    environment["OMP_NUM_THREADS"] = str(threads)
                    environment["OMP_DYNAMIC"] = "FALSE"
                    completed = run_command(
                        command, repo_root, log_path, environment)
                    executed_commands.append({
                        "command": command,
                        "omp_environment": {
                            name: environment.get(name, "<unset>")
                            for name in ("OMP_NUM_THREADS", "OMP_DYNAMIC",
                                         "OMP_PROC_BIND", "OMP_PLACES",
                                         "OMP_SCHEDULE")}})
                    metadata, parity, results = parse_benchmark_output(
                        completed.stdout, k, w, repeat, threads)
                    parity_samples.append(parity["samples"])
                    openmp_macros.add(metadata["openmp_macro"])
                    for result in results:
                        raw_rows.append({
                            "result_status": result_status,
                            "dataset": dataset_record["label"],
                            "dataset_path": dataset_record["path"],
                            "dataset_size_bytes": dataset_record["size_bytes"],
                            "dataset_sha256": dataset_record["sha256"],
                            "fasta_record_count": dataset_record["fasta_record_count"],
                            "k": k, "w": w, "repeat": repeat,
                            "seed": arguments.seed, "method": result["method"],
                            "requested_threads": result["requested_threads"],
                            "observed_threads": result["observed_threads"],
                            "nonempty_workers": result["nonempty_workers"],
                            "runtime_s": "{:.12f}".format(result["runtime_s"]),
                            "throughput_windows_s": "{:.6f}".format(
                                result["throughput_windows_s"]),
                            "throughput_mwindows_s": "{:.12f}".format(
                                result["throughput_windows_s"] / 1000000.0),
                            "valid_bases": metadata["valid_bases"],
                            "ambiguous_bases_skipped": metadata[
                                "ambiguous_bases_skipped"],
                            "valid_kmers": result["valid_kmers"],
                            "valid_windows": result["valid_windows"],
                            "minimizers": result["minimizers"],
                            "processed_windows": result["processed_windows"],
                            "checksum": result["checksum"],
                            "coverage_checksum": result["coverage_checksum"],
                            "tie_handling": "strict_less_than_leftmost",
                            "adjacent_window_deduplication": "false",
                            "parity_samples": parity["samples"],
                            "log_file": str(log_path)})

    expected_raw = (len(datasets) * len(w_values) * len(thread_values) *
                    repeats * len(METHODS))
    if len(raw_rows) != expected_raw:
        raise RuntimeError("unexpected raw CSV row count")
    thread_checks = verify_thread_consistency(raw_rows)
    summary_rows = summarize(raw_rows, result_status)
    expected_summary = (len(datasets) * len(w_values) * len(thread_values) *
                        len(METHODS))
    if len(summary_rows) != expected_summary:
        raise RuntimeError("unexpected summary CSV row count")
    raw_path = output_dir / RAW_NAME
    summary_path = output_dir / SUMMARY_NAME
    write_csv(raw_path, raw_rows, list(raw_rows[0].keys()))
    write_csv(summary_path, summary_rows, list(summary_rows[0].keys()))

    equivalence_command = None
    equivalence_details = None
    equivalence_output = None
    if arguments.smoke:
        (equivalence_command, equivalence_details,
         equivalence_output) = verify_figure2_equivalence(
             repo_root, output_dir, datasets[0], raw_rows, arguments.seed, logs)

    plot_command = [
        "Rscript", "reproducibility/figure3/plot_figure3_multithread.R",
        "--summary", str(summary_path), "--output-dir", str(output_dir)]
    run_command(plot_command, repo_root, logs / "plot.log")
    png_path = output_dir / "figure3_multithread_k21.png"
    pdf_path = output_dir / "figure3_multithread_k21.pdf"
    if any(not path.is_file() or path.stat().st_size == 0
           for path in (png_path, pdf_path)):
        raise RuntimeError("plotting did not produce nonempty PNG and PDF files")

    build_manifest = {
        "repository_commit": commit,
        "source": str(SOURCE_RELATIVE),
        "source_sha256": sha256_file(source_path),
        "library": "build/libkssd_array.a",
        "library_sha256": sha256_file(library_path),
        "compiler": compiler_version,
        "openmp_macro_values": sorted(openmp_macros),
        "openmp_runtime": openmp_runtime,
        "compile_records": compile_records,
    }
    run_manifest = {
        "result_status": result_status,
        "os": platform.platform(), "cpu": cpu_description(),
        "system_load_snapshot": load_snapshot(),
        "datasets": dataset_records, "k": k, "w_values": w_values,
        "thread_values": thread_values, "repeats": repeats,
        "seed": arguments.seed, "methods": list(METHODS),
        "openmp": {
            "schedule": "manual static contiguous window partition",
            "OMP_NUM_THREADS": "set separately to each requested thread count",
            "OMP_DYNAMIC": "FALSE",
            "OMP_PROC_BIND": os.environ.get("OMP_PROC_BIND", "<unset>"),
            "OMP_PLACES": os.environ.get("OMP_PLACES", "<unset>"),
            "OMP_SCHEDULE": os.environ.get("OMP_SCHEDULE", "<unset>"),
        },
        "fasta_semantics": "first record; non-ACGT symbols skipped without reset",
        "tie_handling": "strict less-than retains the leftmost minimum",
        "adjacent_window_deduplication": False,
        "parity": {"result": "PASS", "minimum_samples": min(parity_samples)},
        "thread_consistency": {"result": "PASS", "checks": thread_checks},
        "figure2_figure3_equivalence": {
            "result": "PASS" if arguments.smoke else "not_run_for_formal_mode",
            "command": equivalence_command, "details": equivalence_details,
            "output_directory": str(equivalence_output)
            if equivalence_output is not None else None,
        },
        "executed_commands": executed_commands,
        "plot_command": plot_command,
        "outputs": {
            "raw_csv": str(raw_path), "summary_csv": str(summary_path),
            "logs": str(logs), "bin": str(bins),
            "review_png": str(png_path), "review_pdf": str(pdf_path)},
    }
    (output_dir / "build_manifest.txt").write_text(
        json.dumps(build_manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "run_manifest.txt").write_text(
        json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")

    print("OUTPUT_DIR={}".format(output_dir))
    print("FASTA={}".format(datasets[0] if arguments.smoke else "caller-supplied"))
    print("RAW_CSV={} ROWS={}".format(raw_path, len(raw_rows)))
    print("SUMMARY_CSV={} ROWS={}".format(summary_path, len(summary_rows)))
    print("BUILD_MANIFEST={}".format(output_dir / "build_manifest.txt"))
    print("RUN_MANIFEST={}".format(output_dir / "run_manifest.txt"))
    print("LOGS={}".format(logs))
    print("REVIEW_PNG={}".format(png_path))
    print("REVIEW_PDF={}".format(pdf_path))
    print("PARITY=PASS SAMPLES_MIN={}".format(min(parity_samples)))
    print("THREAD_CONSISTENCY=PASS")
    if arguments.smoke:
        print("FIGURE2_FIGURE3_EQUIVALENCE=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        raise SystemExit(1)
