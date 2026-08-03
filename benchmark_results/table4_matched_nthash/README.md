# Table 4 matched-workload results

Manuscript placement: these detailed matched-workload ntHash results are
intended for Supplementary material, with only a concise summary in the main
text.

Exact accepted source: `$KSSD_RELEASE_HOST/KSSD-Array-formal-results/final-validation-20260731-162115/01_table4_matched_full`.

The 580-row [`benchmark_raw_results.csv`](benchmark_raw_results.csv) covers
two datasets, K=W=4 through 32, two methods, and five paired repeats. The
by-K, paired, and across-K summaries independently recalculate from this raw
file. [`TABLE4_MATCHED_FULL_REPORT.md`](TABLE4_MATCHED_FULL_REPORT.md) gives
the accepted interpretation.

[`Table4_matched_speedup_vs_k.png`](Table4_matched_speedup_vs_k.png) and
[`Table4_matched_speedup_vs_k.pdf`](Table4_matched_speedup_vs_k.pdf) use the
exact theme parameters extracted from the hash-verified historical Figure 2/3
generator. The 58 points are exact five-repeat paired medians from the
accepted final data, with no smoothing. See
[`plot_table4_exact_manuscript_theme.R`](plot_table4_exact_manuscript_theme.R).
The two datasets are distinguished by blue and orange curves as well as by
line type and point shape. No benchmark or summary number changed.

The byte-identical benchmark implementation is tracked at
`reproducibility/table4_matched_workload/benchmark_matched_workload.cpp`.
Local machine paths in metadata files are represented by
`$KSSD_RELEASE_HOST`; accepted measurements are unchanged.
