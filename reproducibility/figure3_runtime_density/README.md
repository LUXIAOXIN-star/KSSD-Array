# Forward-only runtime and minimizer sampling density

## Manuscript reference

Main Figure 3 and Supplementary Table S5. [Results](../../benchmark_results/figure3_runtime_density/README.md).

## Experimental objective

Forward-only runtime and minimizer sampling density.

## Required inputs

Synthetic 10 Mb and the specified 10 Mb chr1 interval. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Same in-memory DNA; include conversion, full score arrays, common selector and selected-position output.

## Parameters

k=21,31; w=20; five independent processes per condition; KSSD-Array, seq-hash and GreedyMini-derived prefix12.

## Software dependencies

The `historical_source` directory contains the historical `gm.cpp`, KSSD wrappers,
Cargo manifest and lockfile, and build script. The `gm_loader_exact.inc` file is
an independently written compatibility loader, not the original GreedyMini
loader. It reads the historical native `size_t` header followed by native
`uint64_t` ranks (64-bit little-endian in the recorded experiment); it does not
alter their order or values. Its handling of an incomplete header is explicitly
defined as failure, whereas the original loader did not define that case. The
comment in the unchanged historical `gm.cpp` referring to the original loader
does not describe this replacement.

The original experiment-specific Rust `main.rs` is not distributed pending
provenance review of its ntHash reference formula; no public acquisition URL
for that exact driver is available. The following dependencies must also be
supplied separately for a full benchmark build:

- [seq-hash](https://github.com/rust-seq/seq-hash), version 0.2.0, historical
  commit `4cd7eed354923f908e8d284a93a359a899199d2c`; its exact-version license
  text remains unconfirmed. Its path dependency is not distributed here.
- The `minimizer loading example/w20_k12.gm` order from
  [GreedyMini](https://github.com/OrensteinLab/GreedyMini) commit
  `a67eb90dc278ea78111a76d5813cf2ac7662b0ae`, SHA-256
  `6d18a02946d4e0fa9a5c86e14bf8967ba291bd55e2a4955c2e7d305e18221d71`.
  GreedyMini is [MIT licensed](https://github.com/OrensteinLab/GreedyMini/blob/a67eb90dc278ea78111a76d5813cf2ac7662b0ae/LICENSE)
  at that commit; the order and upstream loader are not distributed here.
- The [KSSD-Array core](../../README.md), placed in the source layout expected
  by the historical build script, and the exact Cargo.lock dependencies. The
  nested historical copy and dependency cache are not distributed here.
- [OpenSSL](https://www.openssl.org/) headers and `libcrypto` are external;
  the precise historical OpenSSL version and its matching license are not
  confirmed by the available build record.

The historical build also used Rust/Cargo 1.98.1, GCC/G++ 9.4.0 and OpenSSL.
These identities do not by themselves supply or license the missing driver.
See [dependencies](../../docs/dependencies.md) for third-party status.

## Compiler and build options

Recorded historical C and Rust optimization settings apply; complete build dependencies are not all distributed.

## Build command

This collection cannot currently build the complete benchmark on its own: the
driver and external dependencies described above are missing. No complete
public build command is provided.

## Execution command

For a saved-data redraw, install Python 3 and Matplotlib in a suitable isolated
environment, then run from the repository root with a new output directory:

```sh
python3 reproducibility/figure3_runtime_density/plot_figure3.py \
  --data benchmark_results/figure3_runtime_density/figure3_data.csv \
  --manifest benchmark_results/figure3_runtime_density/sha256.tsv \
  --out /tmp/kssd-figure3-redraw
```

The script verifies the data SHA-256, checks all 12 observations and writes PNG,
SVG, PDF and validation JSON. It refuses to replace an existing output file.
Choose another output directory if these files already exist. This command reads
saved data and does not rerun or remeasure the benchmark.

## Output description

Mean runtime, selected positions, density, and figure from saved data.

## Result verification

The redraw checks `figure3_data.csv` against the current public `sha256.tsv`.
The older `SHA256SUMS.txt` is a historical checksum archive, which lists some
files not distributed in this repository; it is not the current package manifest.

## Current validation status

HISTORICAL_DATA_AVAILABLE: the full benchmark was not rerun and some benchmark
dependencies are not included. The saved-data redraw was tested from a clean
snapshot with the updated plotter. The compatibility
loader was separately compared with the historical loader on the original and
a synthetic order, including rank and score outputs. A small end-to-end smoke
test also passed after supplying the missing historical driver and dependencies
in a separate local build workspace. Those files are not distributed here, so
the smoke test does not establish a standalone public build.
