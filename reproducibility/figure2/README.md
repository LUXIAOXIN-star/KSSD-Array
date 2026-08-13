# Figure 2 single-thread benchmark workflow

This directory contains the portable single-thread minimizer-construction
workflow associated with Figure 2. The migration preserves the relevant
historical benchmark definition but does not claim to reproduce formal
performance values during its small functional smoke test.

## Methods

Exactly five methods are active:

- KSSD-Array;
- XXH3;
- XXH64;
- MurmurHash3;
- wyhash.

The obsolete sixth comparator from the historical workflow has been removed in
full. There is no compatibility switch or hidden output row for it.

KSSD-Array initialization and ownership use `kssd_array_init` and
`kssd_array_destroy` from `<kssd_array.h>`. The timed hot path calls
`kssd_array_fast_with_tables` from `<kssd_array_fast.h>`. Before timing, up to
1,024 k-mers are compared with `kssd_array_map_unchecked`; a mismatch stops the
run.

## Preserved semantics and caveat

Valid bases use the two-bit encoding `A=0`, `C=1`, `G=2`, and `T=3`. The
historical program uses only the first FASTA record and skips non-ACGT symbols
without resetting the rolling encoding. That behavior can concatenate valid
bases across an ambiguous region. It is retained and explicitly recorded in
the run manifest because silently resetting would change the measured input.

Each window selects the minimum hash using a strict less-than comparison. Ties
therefore keep the leftmost current position. When that position leaves the
window, the entire window is rescanned. The workflow emits one selected
minimizer per window and performs no adjacent-window deduplication. File
reading, k-mer encoding, context creation, and parity validation are outside
the timed interval. Throughput is valid minimizer windows divided by timed
seconds and is reported in windows/s and million windows/s.

The wyhash final4-style fixed-width adaptation generates its secret with
`wy_make_secret` from the recorded run seed, defaulting to 42. Its eight-byte
hash path uses zero input-seed semantics. XXH3, XXH64, and MurmurHash3 also use
seed zero in these throughput benchmark hot paths.

## Functional smoke test

Build and run the smoke workflow from the repository root:

```sh
make figure2-build
make figure2-smoke
```

The runner creates a deterministic FASTA under a new temporary output
directory. It runs one dataset with `k=21`, `w=20`, one repeat, and five
methods. The expected raw and summary data-row counts are both five. The smoke
test validates build/link behavior, counts, method coverage, parity, output
format, and plotting. It does not validate performance rankings.

## Formal input preparation

The Synthetic 300M input is shared with Figure 3 and the matched-workload
ntHash comparison. Generate the exact accepted `AEEE.fasta` once and verify its
identity as documented in
[`../data_generation/synthetic_300M/`](../data_generation/synthetic_300M/README.md):

```sh
python3 reproducibility/data_generation/synthetic_300M/generate_synthetic_300M.py \
  --output /data/AEEE.fasta
printf '%s  %s\n' \
  a7eca29bdfa06ff373048fffa7a90139afc98acfa938a8ec0a98459608045962 \
  /data/AEEE.fasta | sha256sum --check --strict
```

Input preparation is also summarized in
[`../data_generation/README.md`](../data_generation/README.md). The full
generator is never run by CI.

## Later formal run

The documented formal configuration uses two caller-supplied datasets,
`k=16,19,21,24,31`, `w=10,20,50`, and five repeats:

```sh
python3 reproducibility/figure2/run_figure2_single_thread.py \
  --datasets /data/AEEE.fasta /data/GCF_000001405.40_GRCh38.p14_genomic.fna \
  --dataset-names Synthetic_300M Human_GRCh38 \
  --k-values 16 19 21 24 31 \
  --w-values 10 20 50 \
  --repeats 5 \
  --seed 42 \
  --output-dir /results/figure2-single-thread
```

This full command is documentation only and is not launched automatically.
The same values are recorded in `reproducibility/figure2/config.json`.

## Outputs

The selected output directory receives:

- `figure2_single_thread_raw.csv`;
- `figure2_single_thread_summary.csv`;
- `build_manifest.txt`;
- `run_manifest.txt`;
- `logs/` and `bin/`;
- `figure2_single_thread_realistic_kw.png` and an optional-review PDF.

Raw CSV columns record result status, dataset identity and hash, `k`, `w`,
repeat, seed, method, runtime, throughput, base/k-mer/window/minimizer counts,
parity samples, and the run log. Summary columns contain the grouping keys,
runtime and throughput mean/standard deviation, counts, and repeat number.

Output defaults to a newly created directory under the system temporary
directory. Nothing is written into the repository unless a caller explicitly
chooses a repository path.

The plot can also be regenerated independently:

```sh
Rscript reproducibility/figure2/plot_figure2_single_thread.R \
  --summary /results/figure2-single-thread/figure2_single_thread_summary.csv \
  --output-dir /results/figure2-single-thread
```

The formal run requires the public static KSSD-Array library, a C11 compiler,
libxxhash, Python 3, R, and ggplot2. Generated measurements and plots are review
artifacts and are not committed.
