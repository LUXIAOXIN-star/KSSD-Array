#!/usr/bin/env python3
"""Scan tracked text without echoing possible secret contents."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private-key header": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "OpenAI-style key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "credential in URL": re.compile(r"https?://[^\s/:]+:[^\s/@]+@"),
}


def main() -> int:
    output = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    failures: list[tuple[str, str]] = []
    for raw in output.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode()
        path = ROOT / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue
        text = data.decode("utf-8", errors="ignore")
        for category, pattern in PATTERNS.items():
            if pattern.search(text):
                failures.append((relative, category))
    if failures:
        for relative, category in failures:
            print(f"ERROR: possible {category} in {relative}")
        return 1
    print("secret-pattern scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
