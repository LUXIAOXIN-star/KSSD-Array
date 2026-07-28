#!/usr/bin/env python3
"""Check tracked-file size review thresholds."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WARNING = 10 * 1024 * 1024
HARD = 50 * 1024 * 1024
ALLOWLIST: dict[str, str] = {}


def main() -> int:
    output = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    failed = False
    for raw in output.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode()
        path = ROOT / relative
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > HARD:
            print(f"ERROR: {relative}: {size} bytes exceeds 50 MiB")
            failed = True
        elif size > WARNING and relative not in ALLOWLIST:
            print(f"ERROR: {relative}: {size} bytes exceeds 10 MiB without justification")
            failed = True
        elif size > WARNING:
            print(f"ALLOW: {relative}: {ALLOWLIST[relative]}")
    if failed:
        return 1
    print("large-file scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
