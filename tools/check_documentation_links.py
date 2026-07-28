#!/usr/bin/env python3
"""Check local links in tracked Markdown documents."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def main() -> int:
    output = subprocess.run(
        ["git", "ls-files", "-z", "*.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    failures: list[str] = []
    checked = 0
    for raw in output.split(b"\0"):
        if not raw:
            continue
        path = ROOT / raw.decode()
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            destination = match.group(1).strip().split()[0].strip("<>")
            if destination.startswith(("http://", "https://", "mailto:", "#")):
                continue
            local = unquote(destination.split("#", 1)[0])
            if not local:
                continue
            checked += 1
            target = (path.parent / local).resolve()
            try:
                target.relative_to(ROOT.resolve())
            except ValueError:
                failures.append(f"{path.relative_to(ROOT)}: link leaves repository: {destination}")
                continue
            if not target.exists():
                failures.append(f"{path.relative_to(ROOT)}: missing link target: {destination}")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print(f"documentation-link scan: PASS ({checked} local links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
