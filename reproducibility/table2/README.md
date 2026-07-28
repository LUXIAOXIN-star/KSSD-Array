# Table 2 exhaustive 9-mer validation

This directory reproduces the collision counts reported in Table 2 by
enumerating all `4^9 = 262144` encoded 9-mers. It is a correctness validation,
not a performance benchmark.

## Compared strategies

The validation compares three mappings:

1. `rank-derived` calls the public KSSD-Array context API from
   `build/libkssd_array.a`. It contains no local master-permutation generation,
   rank derivation, or active reconstruction implementation.
2. `low-bit-mask` locally masks master-permutation values for the short
   segment. This lossy construction is retained only as an intentionally
   incorrect ablation.
3. `direct-old` locally indexes the master table at the short-segment value.
   This historical construction is also retained only as an intentionally
   incorrect ablation.

Neither ablation is exposed by a public header or compiled into the installed
library.

## Build and run

From the repository root, build and execute the full validation with:

```sh
make table2-validation
```

To choose a persistent output directory explicitly:

```sh
make
bash reproducibility/table2/run_exhaustive_9mer.sh \
  --output-dir "${TMPDIR:-/tmp}/table2-validation"
```

The runner refuses to overwrite any of its three output files. When no output
directory is supplied, it creates a new directory under `${TMPDIR:-/tmp}` and
prints its location.

The smoke target enumerates only the first 4,096 inputs to check compilation
and output format:

```sh
make table2-validation-smoke
```

Smoke output is explicitly marked as non-manuscript output and is not checked
against the full counts.

## Output

The runner writes:

- `exhaustive_9mer.csv`: one calculated statistics row per strategy;
- `exhaustive_9mer.log`: the mode, command, calculated values, and result;
- `run_manifest.txt`: fixed parameters and SHA-256 values for the source,
  linked library, executable, CSV, and log.

CSV columns are `method`, `total_inputs`, `unique_outputs`, `collisions`,
`collision_rate`, `min_output`, `max_output`, and
`outputs_outside_2k_domain`. The final name is retained from the historical
CSV and denotes the requested outside-domain count. `collision_rate` is stored
as a fraction; the log prints it as a percentage.

## Required full results

| Strategy | Total | Unique | Collisions | Rate | Min | Max | Outside |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rank-derived | 262144 | 262144 | 0 | 0.000000% | 0 | 262143 | 0 |
| low-bit-mask | 262144 | 183296 | 78848 | 30.078125% | 0 | 262143 | 0 |
| direct-old | 262144 | 117760 | 144384 | 55.078125% | 0 | 262143 | 0 |

The program calculates every field independently and exits with failure if any
required full-run count or range differs. The manuscript displays the rates
rounded to `0.00%`, `30.08%`, and `55.08%`.

The rank-derived path initializes `kssd_array_t` with `k=9`, seed 42, and the
default deterministic RNG. It calls `kssd_array_init`,
`kssd_array_map_unchecked`, and `kssd_array_destroy` from the public library.
The validation requires only the C11 standard library, the public header, and
`build/libkssd_array.a`; no historical CSV or external data is required.
