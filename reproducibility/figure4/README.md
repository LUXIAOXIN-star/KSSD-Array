# Figure 4 bucket-balance reproduction

This directory contains the portable workflow for the six-panel Figure 4
bucket-balance experiment. It measures how often an equal-probability
chi-square test does not reject the observed modulo-bucket counts. This is a
specific empirical bucket-balance diagnostic, not a general randomness test
or proof of uniformity.

## Methods and mapping definitions

The active workflow contains exactly five methods, in this public order:

1. KSSD-Array
2. XXH3
3. XXH64
4. MurmurHash3
5. wyhash

KSSD-Array is initialized with `kssd_array_init_with_rng`, using the public
SplitMix64 mode and the condition seed. Mapping uses
`kssd_array_map_unchecked`, and the owning context is released with
`kssd_array_destroy`. No KSSD table construction or mapping implementation is
embedded in the benchmark. The executable links the repository's
`build/libkssd_array.a`.

The other methods hash the packed 2-bit k-mer as an eight-byte `uint64_t` and
retain their full 64-bit outputs. XXH3 and XXH64 use the condition seed.
MurmurHash3 uses the low 32 bits of that seed, matching its historical API.
wyhash builds its secret from the condition seed and uses zero as the hash
input seed. Every method assigns a mapped value to `mapped_value % bins`.

## Deterministic input and seeds

Synthetic DNA uses `A=0`, `C=1`, `G=2`, and `T=3`. Successive SplitMix64
outputs contribute their low two bits, so each base has probability 0.25. For
base seed `20260708`, the condition seed is

```text
base_seed + k * 1000000 + sequence_length // 100 + bins * 100 + repeat
```

The sequence RNG starts from `condition_seed + 1000003`. The same condition
seed initializes the KSSD master permutation and the general hash settings
described above. A length `n` sequence produces exactly `n - k + 1` mapped
k-mers. The implementation streams the rolling packed k-mers instead of
retaining the historical temporary array; the RNG calls, encoded values, and
mapping order are unchanged.

## Statistical definition

For `N` mapped values and `B` bins, the expected count is `N / B`, and

```text
chi_square = sum((observed[i] - N / B)^2 / (N / B))
degrees_of_freedom = B - 1
```

The runner uses `scipy.stats.chisquare` and its upper-tail chi-square
probability. A repetition is a non-rejection when `p > 0.05`. The plotted
quantity is `100 * mean(non_reject)` and is labeled
`Chi-square non-rejection rate (%)`.

## Configuration and expected sizes

The formal grid in
[`reproducibility/figure4/config.json`](../../reproducibility/figure4/config.json)
uses `k=6..14`, sequence lengths 4,000,000 and 8,000,000, bin counts 101, 199,
and 499, and 100 repeats. It produces 27,000 raw rows and 270 summary rows.
Generated CSV files, logs, binaries, manifests, and figures must be written to
a caller-selected directory outside the repository.

Build and run the five-row preflight with:

```sh
make figure4-build
make figure4-preflight
```

Run the formal grid only with an explicit external output directory:

```sh
make figure4-formal \
  OUTPUT_DIR=/external/results/figure4-run \
  FIGURE4_JOBS=1
```

The runner may also be called directly:

```sh
python3 reproducibility/figure4/run_figure4_bucket_balance.py \
  --k-values 6 7 8 9 10 11 12 13 14 \
  --sequence-lengths 4000000 8000000 \
  --bins 101 199 499 --repeats 100 \
  --output-dir /external/results/figure4-run
```

The output directory contains `figure4_bucket_balance_raw.csv`,
`figure4_bucket_balance_summary.csv`, `build_manifest.txt`,
`run_manifest.txt`, `logs/`, and `bin/`. Raw rows store the complete condition
key, seeds, mapped and bucket-count totals, chi-square result, degrees of
freedom, p-value, and non-rejection indicator. Summary rows store the repeat
count, non-rejection count/rate/percentage, and descriptive statistics.

## Comparison and plotting

The comparison utility accepts paths and legacy display labels at runtime. It
filters the retired sixth method, renames the former KSSD display key, reports
exact/numerical differences, and evaluates trend similarity without changing
either result set:

```sh
python3 reproducibility/figure4/compare_figure4_reproduction.py \
  --new-raw /external/results/figure4-run/figure4_bucket_balance_raw.csv \
  --new-summary /external/results/figure4-run/figure4_bucket_balance_summary.csv \
  --historical-raw /external/reference/raw.csv \
  --historical-summary /external/reference/summary.csv \
  --exclude-method RETIRED_LABEL \
  --legacy-kssd-label LEGACY_KSSD_LABEL \
  --new-kssd-label KSSD-Array \
  --output-dir /external/results/figure4-run/comparison
```

Render the 2-by-3 review figure with:

```sh
python3 reproducibility/figure4/plot_figure4_bucket_balance.py \
  --summary /external/results/figure4-run/figure4_bucket_balance_summary.csv \
  --output-dir /external/results/figure4-run
```

The retired sixth method is absent from the benchmark, configuration, output
schema, summary, and plotting code. Its historical rows are handled only by
the caller-configured comparison boundary.
