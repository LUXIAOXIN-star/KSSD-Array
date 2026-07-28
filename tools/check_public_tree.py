#!/usr/bin/env python3
"""Reject non-public content and duplicate KSSD implementations."""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROHIBITED = [
    "KSSD-" + "Arrayhash",
    "kssd_" + "arrayhash",
    "KSSD_" + "ARRAYHASH",
    "Minimap2-" + "hash64",
    "minimap2_" + "hash64",
    "with_" + "minimap2_" + "hash64",
    "/home/" + "luxiaoxin",
    "/tmp/" + "kssd-",
]
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
GENERATED_SUFFIXES = {
    ".bam", ".bai", ".cram", ".crai", ".sam", ".paf", ".mmi",
    ".fastq", ".fq", ".o", ".a", ".so", ".dylib", ".dll",
}
GENERATED_PARTS = {"build", "build-cmake", "Testing", "results", "output"}


def tracked_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def is_text(data: bytes) -> bool:
    return b"\0" not in data[:8192]


def main() -> int:
    failures: list[str] = []
    root_real = ROOT.resolve()
    for path in tracked_paths():
        if not path.exists() and not path.is_symlink():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative == "aud" + "it" or relative.startswith("aud" + "it/"):
            failures.append(f"internal audit path: {relative}")
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            target = path.resolve(strict=False)
            try:
                target.relative_to(root_real)
            except ValueError:
                failures.append(f"external symbolic link: {relative}")
            continue
        if path.suffix.lower() in GENERATED_SUFFIXES or any(
            part in GENERATED_PARTS for part in Path(relative).parts
        ):
            failures.append(f"forbidden generated file: {relative}")
        data = path.read_bytes()
        if not is_text(data):
            continue
        text = data.decode("utf-8", errors="replace")
        for term in PROHIBITED:
            if term in text:
                failures.append(f"prohibited public-tree term in {relative}")
        if CJK.search(text):
            failures.append(f"CJK character in {relative}")

        if path.suffix.lower() in {".c", ".cc", ".cpp", ".h", ".hpp"}:
            allowed = (
                relative.startswith("src/")
                or relative.startswith("include/")
                or relative == "reproducibility/table2/test_exhaustive_9mer.c"
            )
            implementation_markers = (
                "build_master_permutation",
                "derive_rank_permutation",
                "padded_index_rank",
            )
            if not allowed and any(marker in text for marker in implementation_markers):
                failures.append(f"duplicate implementation marker in {relative}")

    if failures:
        for failure in sorted(set(failures)):
            print(f"ERROR: {failure}")
        return 1
    print("public-tree scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
