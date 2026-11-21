#!/usr/bin/env python3
"""Generate the exact historical Synthetic 300 Mb benchmark FASTA."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Iterator


SEED = 1781167332
FORMAL_LENGTH = 300_000_000
HEADER = b">AE016877.1 Bacillus cereus ATCC 14579, complete genome\n"
BASES = b"ATCG"
EXPECTED_SIZE = 300_000_057
EXPECTED_SHA256 = "a7eca29bdfa06ff373048fffa7a90139afc98acfa938a8ec0a98459608045962"
DEFAULT_CHUNK_SIZE = 1024 * 1024


class GlibcRand31:
    """Portable implementation of the glibc random()/rand() TYPE_3 stream.

    The recurrence and 344-value warm-up are implemented with fixed-width
    arithmetic, so output does not depend on the host C library or Python
    integer representation.
    """

    def __init__(self, seed: int) -> None:
        if not 1 <= seed <= 0x7FFFFFFF:
            raise ValueError("seed must be within 1..2147483647")
        values = [0] * 344
        values[0] = seed
        for index in range(1, 31):
            previous = values[index - 1]
            value = 16807 * (previous % 127773) - 2836 * (previous // 127773)
            values[index] = value + 2147483647 if value < 0 else value
        values[31] = values[0]
        values[32] = values[1]
        values[33] = values[2]
        for index in range(34, 344):
            values[index] = (
                values[index - 31] + values[index - 3]
            ) & 0xFFFFFFFF

        self._state = [0] * 31
        for index in range(313, 344):
            self._state[index % 31] = values[index]
        self._index = 344

    def next(self) -> int:
        index = self._index
        slot = index % 31
        value = (self._state[slot] + self._state[(index - 3) % 31]) & 0xFFFFFFFF
        self._state[slot] = value
        self._index = index + 1
        return value >> 1


def sequence_chunks(length: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Iterator[bytes]:
    """Yield the fixed-seed sequence in bounded-memory chunks."""
    if length < 1:
        raise ValueError("length must be positive")
    if chunk_size < 1:
        raise ValueError("chunk size must be positive")

    generator = GlibcRand31(SEED)
    remaining = length
    while remaining:
        count = min(remaining, chunk_size)
        block = bytearray(count)
        for offset in range(count):
            block[offset] = BASES[generator.next() & 3]
        yield bytes(block)
        remaining -= count


def write_fasta(output: Path, length: int = FORMAL_LENGTH) -> tuple[int, str]:
    """Write a new FASTA and return its byte size and SHA-256."""
    if output.exists():
        raise FileExistsError("refusing to overwrite existing output: {}".format(output))
    if not output.parent.is_dir():
        raise FileNotFoundError("output directory does not exist: {}".format(output.parent))

    digest = hashlib.sha256()
    size = 0
    try:
        with output.open("xb") as handle:
            handle.write(HEADER)
            digest.update(HEADER)
            size += len(HEADER)
            for block in sequence_chunks(length):
                handle.write(block)
                digest.update(block)
                size += len(block)
            handle.write(b"\n")
            digest.update(b"\n")
            size += 1
    except BaseException:
        output.unlink(missing_ok=True)
        raise

    observed_hash = digest.hexdigest()
    if length == FORMAL_LENGTH and (
        size != EXPECTED_SIZE or observed_hash != EXPECTED_SHA256
    ):
        output.unlink(missing_ok=True)
        raise RuntimeError(
            "formal output identity mismatch: size={} sha256={}".format(
                size, observed_hash
            )
        )
    return size, observed_hash


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the exact fixed-seed Synthetic 300 Mb FASTA."
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        help="new output FASTA path; an existing path is never overwritten",
    )
    parser.add_argument(
        "--length", type=int, default=FORMAL_LENGTH,
        help="sequence length; non-default values are for lightweight tests only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.length < 1:
        raise SystemExit("--length must be positive")
    output = args.output.expanduser().resolve()
    size, sha256 = write_fasta(output, args.length)
    print("output={}".format(output))
    print("seed={}".format(SEED))
    print("sequence_length={}".format(args.length))
    print("size_bytes={}".format(size))
    print("sha256={}".format(sha256))
    print("formal_identity={}".format("PASS" if args.length == FORMAL_LENGTH else "NOT_APPLICABLE"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

