#!/usr/bin/env python3
"""Report manuscript-workflow dependencies without downloading anything."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def command_status(command: str, category: str, required: bool) -> tuple[bool, str]:
    path = shutil.which(command)
    label = "required" if required else "optional"
    if path:
        return True, f"PASS  {command:<12} {category} ({label})"
    return False, f"MISS  {command:<12} {category} ({label}); install it and ensure it is on PATH"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-all", action="store_true", help="fail for missing optional workflow tools")
    args = parser.parse_args()
    specifications = [
        (os.environ.get("CC", "cc"), "core build, C11", True),
        ("cmake", "core packaging, version 3.16 or newer", True),
        ("python3", "workflow orchestration, version 3.8 or newer", True),
        ("pkg-config", "installed-consumer validation", False),
        ("Rscript", "Figure 2/3 plotting", False),
        ("samtools", "Table S2 metrics", False),
        ("bedtools", "Table S2 repeat-region metrics", False),
        ("art_illumina", "Table S2 read simulation", False),
        ("meson", "ntHash preparation", False),
        ("ninja", "ntHash preparation", False),
    ]
    failed = False
    for command, category, required in specifications:
        present, message = command_status(command, category, required)
        print(message)
        if not present and (required or args.require_all):
            failed = True

    nthash_root = os.environ.get("NTHASH_ROOT")
    nthash = Path(nthash_root) if nthash_root else ROOT / "third_party/ntHash/install"
    nthash_ok = (nthash / "include/nthash/nthash.hpp").is_file() and (
        nthash / "lib/libnthash.a"
    ).is_file()
    print(
        "PASS  ntHash       pinned benchmark dependency"
        if nthash_ok
        else "MISS  ntHash       run reproducibility/table4/prepare_nthash.sh or set NTHASH_ROOT"
    )
    if args.require_all and not nthash_ok:
        failed = True

    if os.environ.get("MINIMAP2_SOURCE_DIR"):
        print("PASS  Minimap2     source directory selected by MINIMAP2_SOURCE_DIR")
    else:
        print("MISS  Minimap2     set MINIMAP2_SOURCE_DIR for integration commands")
        failed = failed or args.require_all
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
