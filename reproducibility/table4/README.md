# Table 4 KSSD-Array versus ntHash workflow

This directory migrates the current-manuscript Table 4 comparison between
KSSD-Array and ntHash. The Phase 4B smoke run is a build and functional check;
it does not reproduce manuscript performance values or establish a ranking.
Performance depends on the compiler, processor, operating system, and system
load.

## Implementations and preserved protocol

KSSD-Array owns its tables through `kssd_array_init_with_rng` and
`kssd_array_destroy`. Fixed seed 42 and `KSSD_ARRAY_RNG_GLIBC_COMPAT`
reproduce the historical table-generation stream through the current public
context API. Up to 1,024 inputs are checked with
`kssd_array_map_unchecked` before timing, and the timed hot path calls
`kssd_array_fast_with_tables`. The benchmark links the public static archive
`build/libkssd_array.a`; it does not compile KSSD core sources.

The opaque wrapper in this directory is the only code that includes the ntHash
C++ header. It owns one `nthash::NtHash` object and exposes create, roll,
current-hash, and destroy operations. The pinned dependency is ntHash 2.4.0 at
commit `c26bd4572a19de81e30d55042dbd33c1fd21d4b6`. Prepare it with:

```sh
reproducibility/table4/prepare_nthash.sh
```

An existing verified installation can be copied into the ignored local prefix
with `reproducibility/table4/prepare_nthash.sh --source-prefix /path/to/install`. Resolution
order is `--nthash-prefix`, `NTHASH_ROOT`, then
`third_party/ntHash/install`.

The historical parser reads only the first FASTA record and removes non-ACGT
symbols without resetting the rolling sequence. Each window retains the
leftmost minimum on ties and produces one minimizer; adjacent windows are not
deduplicated. The KSSD interval maps pre-encoded k-mers and selects minimizers.
The ntHash interval generates rolling hashes and selects minimizers; both
implementations initialize outside timing. The additional KSSD re-evaluations
during a full window rescan and ntHash's reuse of ring-buffered hashes are also
preserved. These asymmetric work boundaries are historical protocol, are
recorded in the run manifest, and must be considered when interpreting results.

## Smoke run

```sh
make table4-build
make table4-smoke
```

The smoke source-generates `reproducibility/table4/fixtures/table4_smoke.fa`
beneath a temporary output root, then uses `k=w=21`, one repeat,
and exactly two methods. It expects two raw rows and two summary rows. Output
defaults to a new system temporary directory outside the repository.

## Later formal run

Provide the full datasets explicitly:

```sh
python3 reproducibility/table4/run_table4_nthash.py \
  --datasets /data/AEEE.fasta /data/GCF_000001405.40_GRCh38.p14_genomic.fna \
  --dataset-names Synthetic_300M Human_GRCh38 \
  --k-start 4 --k-end 32 --repeats 3 \
  --nthash-prefix /dependencies/nthash-install \
  --output-dir /results/table4-nthash
```

If `--datasets` is omitted, formal dataset filenames are resolved below
`KSSD_DATA_DIR`, or below `reproducibility/data/external` when that variable is absent. Missing
data stops with an actionable error. The command above is documentation only;
Phase 4B never launches the formal grid.

## Outputs and schemas

The output directory contains raw and across-k summary CSV files, formatted
CSV and Markdown tables, build and run manifests, logs, and per-k binaries.
The raw CSV has one row per dataset, k, repeat, and method. It records dataset
identity/checksum, k/w, seed, timing, throughput, parser counts, minimizer count,
checksum, parity samples, and log path.

The summary CSV has one row per dataset and method. Runtime and throughput are
the arithmetic mean and sample standard deviation across all requested k values
and repeats, matching the historical across-k aggregation. The formatter pairs
the two method rows, calculates runtime and throughput ratios from the new
values, preserves full-precision inputs in CSV, and rounds only the Markdown
preview:

```sh
python3 reproducibility/table4/format_table4_nthash.py \
  --summary /results/table4-nthash/table4_nthash_summary.csv \
  --output-dir /results/table4-nthash
```

Dataset provenance and exclusion policy are documented in
`docs/datasets.md`. Generated measurements, binaries, logs, and full datasets are
not committed.
