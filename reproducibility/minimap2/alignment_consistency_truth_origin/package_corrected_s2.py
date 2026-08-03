#!/usr/bin/env python3
"""Create the compact corrected S2 review packet and hash inventories."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
from pathlib import Path
import tarfile
from typing import List

from s2_core import sha256_file


PROVENANCE_TEMPLATE = Path("provenance/SOURCE_REPOSITORY_STATE.md")
PRIVATE_DEVELOPER_PATH = "/home/" + "luxiaoxin"
PROVENANCE_TITLE = "# Public corrected-S2 workflow source state\n"
FIXTURE_GENERATOR_SOURCES = (
    Path("tests/fixture_generators/fixture_generator.c"),
    Path("tests/fixture_generators/generate_test_fixtures.sh"),
    Path("tests/fixture_generators/expected_sha256.tsv"),
)

REVIEW_FILES = (
    "supplementary_table_s2_corrected.csv",
    "supplementary_table_s2_mapq_corrected.csv",
    "supplementary_s2_corrected_counts.csv",
    "supplementary_s2_corrected_metrics.csv",
    "supplementary_s2_corrected_paired.csv",
    "HISTORICAL_METRIC_REPRODUCTION.tsv",
    "HISTORICAL_METRIC_REPRODUCTION_REPORT.md",
    "HISTORICAL_VS_CORRECTED_S2_COMPARISON.tsv",
    "HISTORICAL_VS_CORRECTED_S2_COMPARISON.md",
    "INPUT_AND_ARTIFACT_AUDIT.md",
    "TRUTH_SCHEMA_AUDIT.md",
    "TRUTH_SCHEMA_MANUAL_CHECKS.tsv",
    "TRUTH_ORIGIN_REPEAT_AUDIT.tsv",
    "TRUTH_ORIGIN_REPEAT_AUDIT.md",
    "S2_CORRECTED_VALIDATION.tsv",
    "S2_CORRECTED_VALIDATION_REPORT.md",
    "TABLE_S2_CORRECTED_METHODS_TEXT.md",
    "TABLE_S2_CORRECTED_RESULTS_TEXT.md",
    "TABLE_S2_CORRECTED_CAPTION.md",
    "TABLE_S2_CORRECTED_NOTE.md",
    "S2_CORRECTED_FINAL_REPORT.md",
    "SOURCE_BINDING.md",
    "SOURCE_REPOSITORY_STATE.md",
    "source_sha256.tsv",
    "input_sha256.tsv",
    "bam_sha256.tsv",
    "build_manifest.txt",
    "run_manifest.txt",
    "commands.sh",
    "environment.txt",
    "unit_tests.log",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def validated_provenance_template(workflow: Path) -> bytes:
    template = workflow / PROVENANCE_TEMPLATE
    if not template.is_file():
        raise FileNotFoundError(
            "missing public corrected-S2 provenance template: {}".format(template))
    content = template.read_bytes()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError("public corrected-S2 provenance template is not UTF-8") from error
    if not text.startswith(PROVENANCE_TITLE):
        raise RuntimeError("public corrected-S2 provenance template has an unexpected title")
    required = (
        "Source identity: content-addressed by the generated `source_sha256.tsv`",
        "Commit identity: intentionally not embedded",
        "Private developer paths permitted in this record: `NO`",
    )
    if any(marker not in text for marker in required):
        raise RuntimeError("public corrected-S2 provenance template is incomplete")
    if PRIVATE_DEVELOPER_PATH in text:
        raise RuntimeError("public corrected-S2 provenance template contains a private path")
    return content


def materialize_repository_state(workflow: Path, output: Path) -> Path:
    content = validated_provenance_template(workflow)
    target = output / "SOURCE_REPOSITORY_STATE.md"
    if target.is_file():
        existing = target.read_bytes()
        if PRIVATE_DEVELOPER_PATH.encode("ascii") in existing:
            raise RuntimeError(
                "existing SOURCE_REPOSITORY_STATE.md contains a private path")
        if existing != content:
            raise RuntimeError(
                "existing SOURCE_REPOSITORY_STATE.md does not match the public template")
        return target
    if target.exists():
        raise RuntimeError("SOURCE_REPOSITORY_STATE.md exists but is not a regular file")
    temporary = output / ".SOURCE_REPOSITORY_STATE.md.tmp"
    if temporary.exists():
        raise RuntimeError("temporary provenance path already exists: {}".format(temporary))
    temporary.write_bytes(content)
    temporary.replace(target)
    return target


def write_source_inventory(workflow: Path, output: Path) -> None:
    rows: List[dict] = []
    for path in sorted(item for item in workflow.rglob("*") if item.is_file() and "__pycache__" not in item.parts):
        rows.append({
            "relative_path": str(path.relative_to(workflow)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    repository_root = workflow.parents[2]
    for relative in FIXTURE_GENERATOR_SOURCES:
        path = repository_root / relative
        if not path.is_file():
            raise FileNotFoundError(
                "missing corrected-S2 fixture-generator source: {}".format(path))
        rows.append({
            "relative_path": str(relative),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    rows.sort(key=lambda row: row["relative_path"])
    with (output / "source_sha256.tsv").open("wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def deterministic_archive(output: Path) -> Path:
    archive = output / "S2_CORRECTED_REVIEW_PACKET.tar.gz"
    for name in REVIEW_FILES:
        if not (output / name).is_file():
            raise FileNotFoundError(output / name)
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for name in REVIEW_FILES:
                    path = output / name
                    info = tar.gettarinfo(str(path), arcname=name)
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with path.open("rb") as handle:
                        tar.addfile(info, handle)
    return archive


def write_output_inventory(output: Path) -> None:
    rows = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        if path.name == "output_sha256.tsv" or "temporary" in path.relative_to(output).parts:
            continue
        rows.append({
            "relative_path": str(path.relative_to(output)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    with (output / "output_sha256.tsv").open("wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def package(workflow: Path, output: Path) -> Path:
    if not output.is_dir():
        raise FileNotFoundError("corrected-S2 output directory is missing: {}".format(output))
    materialize_repository_state(workflow, output)
    write_source_inventory(workflow, output)
    archive = deterministic_archive(output)
    write_output_inventory(output)
    return archive


def main() -> int:
    args = parse_args()
    workflow = args.workflow_dir.resolve()
    output = args.output_dir.resolve()
    archive = package(workflow, output)
    print("REVIEW_PACKET={}".format(archive))
    print("OUTPUT_HASH_INVENTORY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
