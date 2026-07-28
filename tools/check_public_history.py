#!/usr/bin/env python3
"""Scan every reachable public Git path and blob without printing contents."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
WARNING_SIZE = 10 * 1024 * 1024
HARD_SIZE = 50 * 1024 * 1024
PROHIBITED = {
    "historical project name": [
        "KSSD-" + "Arrayhash",
        "kssd_" + "arrayhash",
        "KSSD_" + "ARRAYHASH",
        "Minimap2-" + "hash64",
        "minimap2_" + "hash64",
        "with_" + "minimap2_" + "hash64",
    ],
    "developer absolute path": ["/home/" + "luxiaoxin"],
    "private temporary path": ["/tmp/" + "kssd-"],
    "internal audit path": [
        "aud" + "it/",
        "KSSD-Array-" + "internal-audit",
        "KSSD-" + "rescue-audit",
    ],
}
SECRET_PATTERNS = {
    "private key header": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "API key": re.compile(r"(?:sk-|api[_-]?key[=:])[A-Za-z0-9_-]{20,}", re.I),
    "credential in URL": re.compile(r"https?://[^\s/:]+:[^\s/@]+@"),
}
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def git(*args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True
    )
    return completed.stdout if binary else completed.stdout.decode("utf-8")


def main() -> int:
    counts = {category: 0 for category in PROHIBITED}
    secret_count = 0
    cjk_count = 0
    over_warning = 0
    over_hard = 0
    external_symlinks = 0

    object_lines = git("rev-list", "--objects", "--all").splitlines()
    object_ids = {line.split(" ", 1)[0] for line in object_lines}
    for object_id in sorted(object_ids):
        object_type = git("cat-file", "-t", object_id).strip()
        if object_type != "blob":
            continue
        size = int(git("cat-file", "-s", object_id).strip())
        over_warning += size > WARNING_SIZE
        over_hard += size > HARD_SIZE
        data = git("cat-file", "blob", object_id, binary=True)
        if b"\0" in data[:8192]:
            continue
        text = data.decode("utf-8", errors="replace")
        for category, terms in PROHIBITED.items():
            counts[category] += any(term in text for term in terms)
        secret_count += any(pattern.search(text) for pattern in SECRET_PATTERNS.values())
        cjk_count += bool(CJK.search(text))

    for line in object_lines:
        fields = line.split(" ", 1)
        if len(fields) != 2:
            continue
        path = fields[1]
        for category, terms in PROHIBITED.items():
            counts[category] += any(term in path for term in terms)

    commits = git("rev-list", "--all").splitlines()
    for commit in commits:
        entries = git("ls-tree", "-r", "-z", commit, binary=True).split(b"\0")
        for entry in entries:
            if not entry:
                continue
            metadata, raw_path = entry.split(b"\t", 1)
            mode, _, object_id = metadata.decode().split()
            if mode != "120000":
                continue
            target = git("cat-file", "blob", object_id).strip()
            parent = PurePosixPath(raw_path.decode()).parent
            normalized = os.path.normpath(str(parent / target))
            if target.startswith("/") or normalized == ".." or normalized.startswith("../"):
                external_symlinks += 1

    results = {
        "historical project names": counts["historical project name"],
        "developer absolute paths": counts["developer absolute path"],
        "internal audit paths": counts["internal audit path"],
        "private temporary paths": counts["private temporary path"],
        "secret-pattern findings": secret_count,
        "blobs larger than 10 MiB": over_warning,
        "blobs larger than 50 MiB": over_hard,
        "external symbolic links": external_symlinks,
        "prohibited CJK occurrences": cjk_count,
    }
    for label, count in results.items():
        print(f"{label}: {count}")
    failed = any(results.values())
    print("public-history scan: " + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
