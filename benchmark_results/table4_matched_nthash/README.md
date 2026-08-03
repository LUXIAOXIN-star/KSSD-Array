# Table 4 matched-workload results

Exact accepted source: `$KSSD_RELEASE_HOST/KSSD-Array-formal-results/final-validation-20260731-162115/01_table4_matched_full`.

The 580-row [`benchmark_raw_results.csv`](benchmark_raw_results.csv) covers
two datasets, K=W=4 through 32, two methods, and five paired repeats. The
by-K, paired, and across-K summaries independently recalculate from this raw
file. [`TABLE4_MATCHED_FULL_REPORT.md`](TABLE4_MATCHED_FULL_REPORT.md) gives
the accepted interpretation, and the PNG/PDF are the accepted plot.

The byte-identical benchmark implementation is tracked at
`reproducibility/table4_matched_workload/benchmark_matched_workload.cpp`.
Local machine paths in metadata files are represented by
`$KSSD_RELEASE_HOST`; accepted measurements are unchanged.
