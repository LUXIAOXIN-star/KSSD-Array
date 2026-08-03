#!/usr/bin/env python3
"""Unit tests for the source-generated public smoke fixtures."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
WRAPPER = HERE / "generate_test_fixtures.sh"
MANIFEST = HERE / "expected_sha256.tsv"


def manifest_rows(path: Path = MANIFEST) -> list[tuple[str, str]]:
    rows = []
    for line in path.read_text(encoding="ascii").splitlines():
        if line:
            digest, relative = line.split("\t", 1)
            rows.append((digest, relative))
    return rows


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_wrapper(output: Path, *extra: str,
                environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [str(WRAPPER), "--output-dir", str(output), *extra]
    return subprocess.run(
        command, cwd=HERE, env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


class FixtureGeneratorTest(unittest.TestCase):
    def test_clean_generation_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-fixture-test-") as temporary:
            root = Path(temporary) / "generated"
            completed = run_wrapper(root)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rows = manifest_rows()
            self.assertEqual(len(rows), 6)
            for expected, relative in rows:
                self.assertEqual(digest(root / relative), expected)
            self.assertFalse(any(path.name == "a.out" for path in root.rglob("*")))

    def test_repeated_generation_is_identical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-fixture-repeat-") as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            self.assertEqual(run_wrapper(first).returncode, 0)
            self.assertEqual(run_wrapper(second).returncode, 0)
            for _, relative in manifest_rows():
                self.assertEqual((first / relative).read_bytes(),
                                 (second / relative).read_bytes())

    def test_missing_compiler_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-fixture-no-cc-") as temporary:
            environment = os.environ.copy()
            environment["CC"] = "kssd-deliberately-missing-compiler"
            completed = run_wrapper(Path(temporary) / "generated",
                                    environment=environment)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("compiler is unavailable", completed.stderr)

    def test_invalid_seed_and_arguments_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-fixture-bad-seed-") as temporary:
            completed = run_wrapper(Path(temporary) / "generated", "--seed", "41")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("seed must be exactly 42", completed.stderr)
        completed = subprocess.run(
            [str(WRAPPER), "--not-an-option"], cwd=HERE, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(completed.returncode, 2)

    def test_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-fixture-bad-hash-") as temporary:
            root = Path(temporary)
            rows = manifest_rows()
            bad_manifest = root / "bad.tsv"
            bad_manifest.write_text(
                "0" * 64 + "\t" + rows[0][1] + "\n" +
                "\n".join(digest_value + "\t" + relative
                            for digest_value, relative in rows[1:]) + "\n",
                encoding="ascii",
            )
            completed = run_wrapper(
                root / "generated", "--manifest", str(bad_manifest)
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("FAILED", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
