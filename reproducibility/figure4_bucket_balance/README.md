# Evaluate non-rejection rates of bucket-count chi-square tests

## Manuscript reference

Main Figure 4. [Results](../../benchmark_results/figure4_bucket_balance/README.md).

## Experimental objective

Evaluate non-rejection rates of bucket-count chi-square tests.

## Required inputs

Seeded synthetic DNA generated inside the original program. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Do not replace the original SplitMix64 stream or its per-condition seed rule.

## Parameters

k=6–14; 4/8 Mb; B=101,199,499; 100 repeats per condition.

## Software dependencies

Authorized original benchmark C, shared xxHash 0.7.3, Python, NumPy and SciPy. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Historical core `-O2`, driver `-O3 -march=native`; original NumPy/SciPy versions matter.

## Build command

Compile the included current C program using the Figure 4 workflow requirements; use a new build directory.

## Execution command

The current C program is included under `reproducibility/figure4/`; the separate wrapper requiring a byte-identical historical source is not included here. The current source differs from the recorded historical file in attribution comment and method-label case.

## Output description

Five histograms, chi-square p values and non-rejection summaries.

## Result verification

Verify bucket totals, deterministic repeated seed, source SHA and chi-square result.

## Current validation status

PARTIAL: the current included C program was built in isolation and run for k=9, B=101 and 10,000 bases; all five histograms contained 9,992 k-mers. The full formal experiment was not rerun. The current public C is [`../figure4/benchmark_bucket_balance.c`](../figure4/benchmark_bucket_balance.c); it differs from the recorded historical source in an attribution comment and method-label case.
