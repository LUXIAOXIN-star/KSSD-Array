#!/usr/bin/env python3
"""Lightweight tests for the exact Synthetic 300 Mb generator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate_synthetic_300M as generator  # noqa: E402


EXPECTED_PREFIX_256 = (
    "GAGGACGTGTGAGCCACCTCGGCCCCAGTCCTGCAGAGAGAAAGCCAAATCGAATCCCTAAGTG"
    "TTGCAGTAGTACGACGTTGTTAGACAAGGTCTCTGCTACACCCTCTTGCAAGAGGGGGCGAAACC"
    "GAGGGGTTCGAGAGTAAAAGAGGGTCACCCATGGACCCGATGGTGATGTTCTTTACGAATGACCG"
    "GACTGCCGCGCCATGTGACTTTATTCACACTGCGACCCTATGCTACGGCTAGCTTAGTCGAG"
).encode("ascii")


class SyntheticGeneratorTest(unittest.TestCase):
    def test_known_historical_prefix(self) -> None:
        observed = b"".join(generator.sequence_chunks(256, chunk_size=37))
        self.assertEqual(EXPECTED_PREFIX_256, observed)

    def test_binary_fasta_format_and_determinism(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-synthetic-prefix-") as temporary:
            root = Path(temporary)
            first = root / "first.fa"
            second = root / "second.fa"
            first_size, first_hash = generator.write_fasta(first, 4096)
            second_size, second_hash = generator.write_fasta(second, 4096)
            expected_size = len(generator.HEADER) + 4096 + 1
            self.assertEqual(expected_size, first_size)
            self.assertEqual(first_size, second_size)
            self.assertEqual(first_hash, second_hash)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            payload = first.read_bytes()
            self.assertTrue(payload.startswith(generator.HEADER))
            self.assertTrue(payload.endswith(b"\n"))
            self.assertEqual(2, payload.count(b"\n"))
            self.assertEqual(first_hash, hashlib.sha256(payload).hexdigest())

    def test_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-synthetic-overwrite-") as temporary:
            output = Path(temporary) / "existing.fa"
            output.write_bytes(b"keep-me")
            with self.assertRaises(FileExistsError):
                generator.write_fasta(output, 32)
            self.assertEqual(b"keep-me", output.read_bytes())


if __name__ == "__main__":
    unittest.main()

