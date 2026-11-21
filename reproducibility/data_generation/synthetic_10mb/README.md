# Synthetic 10 Mb deterministic input

The included historical generator uses SplitMix64 seed 42 and the low two bits
to select A/C/G/T. It is distinct from the recovered glibc-compatible 300-Mb
generator. It writes to a fixed directory relative to its source file; use an
isolated copy and inspect the output location before execution. An isolated
portable wrapper is not distributed in this package.

The expected plain sequence and FASTA SHA-256 values are respectively
`a2fb48653cea06d4bd329651e5038e1a264bf6f061387471e5cf1dcfcfd8241a` and
`3034401c1fb10382f8195e71f3fe01bd27f47acfe8a1ed436e275de7b7a3f8b6`.
These identify the historical input, not a new generation in this package.

**Status: HISTORICAL_DATA_AVAILABLE.** The historical source and expected
hashes are provided; the full 10-Mb generation was not rerun for this package.
