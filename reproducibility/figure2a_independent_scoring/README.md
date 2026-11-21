# Independent scoring of preencoded k-mers

## Manuscript reference

Main Figure 2a. [Results](../../benchmark_results/figure2a_independent_scoring/README.md).

## Experimental objective

Independent scoring of preencoded k-mers.

## Required inputs

Synthetic 300 Mb and the first GRCh38.p14 chr1 FASTA record. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Read the first record and delete non-ACGT bases before k-mer encoding; encoding is outside the timer.

## Parameters

k=16,19,21,24,31; five technical repeats per condition; five methods reported.

## Software dependencies

The preserved Phase 1 driver and its direct-call adapter are included here. The Figure 2a methods use pinned inline xxHash 0.8.3, while additional shared-library anchor methods require runtime xxHash 0.7.3. C11, OpenMP, `__uint128_t`, GNU-compatible ELF symbol aliases, x86-64 little-endian operation and Python 3 are required for the historical implementation. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

The original driver is built at `-O3 -march=native`; compiler and full command are saved by the launcher.

## Build command

The launcher builds a single condition in a fresh external output; it never runs `make clean`.

## Execution command

```sh
python3 reproducibility/figure2a_independent_scoring/run_portable.py --phase1-dir reproducibility/figure2a_independent_scoring --fasta /path/to/input.fa --fasta-sha256 SHA256 --expected-valid-bases 300000000 --dataset Synthetic_300_Mb --output /path/to/new-output --k 21 --repeats 5 --warmup 1 --cpu CPU
```

## Output description

The original full 15-method per-condition stream and validation metadata; the manuscript uses five methods.

## Result verification

Input and source SHA, method row counts and repeated checksums are checked.

## Current validation status

The preserved driver is checked by SHA-256 before building. A k=21 small-input check passed, but the full formal conditions were not rerun. The [plot script](plot_figure2_independent_scoring.py) renders the [saved scoring data](../../benchmark_results/figure2a_independent_scoring/figure2a_plot_data_path_redacted.tsv); rendering saved data does not repeat the benchmark.

## Hash implementations and source identities

`phase1_benchmark.c` is the byte-identical historical driver (SHA-256 `6356f0ecc301afc03813fdfd95a58f4b8ca49c53db9892e3efa46aec3a4e4a63`). The two `accepted_xxhash_shared.*` files are the historical ELF call adapters. The five Figure 2a curves use inline xxHash v0.8.3 (`XXH_INLINE_ALL`), not the separate dynamically linked xxHash 0.7.3 anchors. Both hashes receive one 8-byte key and seed 0. The source and BSD-2-Clause terms are preserved under `third_party/xxhash-v0.8.3/`.

The local fixed-eight-byte MurmurHash3 specialization follows Austin Appleby’s public-domain `MurmurHash3_x64_128` and returns its first finalized 64-bit `h1` word with seed 0 on the historical x86-64 little-endian platform. It is not the complete Peter Scott C port. The fixed-eight-byte wyhash implementation is final4-style, uses `__uint128_t` multiplication and omits upstream variable-length and alternative-multiply branches. Its secret-generation seed is 42 and per-key hash seed is 0. The matching reference version’s Unlicense is retained at `third_party/wyhash-final4/LICENSE`; this does not assert that the local specialization is the complete upstream header or prove its direct copy history.

The driver also implements identity, bit reversal, odd multiplication, affine and xorshift controls and KSSD table variants. Its SplitMix64 arithmetic corresponds to the reference by Sebastiano Vigna; the reference permission statement and source URL are documented under `third_party/splitmix64/`. Upstream source correspondence does not establish the local implementation’s direct copy history. See [third-party notices](../../THIRD_PARTY_NOTICES.md).
