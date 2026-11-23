# Bucket-count balance results

Current Figure4 retains the original bucket-count experiment: figure4_bucket_balance_raw.csv has27000 rows, and figure4_bucket_balance_summary.csv has270 groups. Each condition contains100 generated sequences. The ordinate is the percentage of sequences with chi-square p>0.05, using the strict greater-than rule.

This is a non-rejection frequency under the stated test, not proof that a mapping is uniform. GC-response and low-complexity experiments are separate historical diagnostics and do not replace these data. Input lengths, k range, B101/199/499 and all five methods remain in the original tables.

Read the source-bound caption and [current result index](../README.md) for the current labeled plot. Original raw data, summary, plotted values, deterministic seed rules and per-method implementation identities remain unchanged. See [the workflow](../../reproducibility/figure4/README.md) for data generation, validation, plotting and dependencies.

[Figure4_bucket_count_nonrejection.png](Figure4_bucket_count_nonrejection.png)
is the manuscript-matching labeled image. [Figure4_manuscript.png](Figure4_manuscript.png)
is an alternative rendering with different axis and panel labels. The raw and
summary tables remain the historical records described above.

[`output_sha256.tsv`](output_sha256.tsv) is a historical snapshot: its README
hash describes an earlier version and does not verify this file. The parent
[artifact manifest](../artifact_manifest.tsv) records the README version in
commit `c4f77ada8a686fa238e4d6b4c9ffc44f43fdf8f7`, before later documentation
updates. Both historical records remain unchanged.

For current documentation checksums use
[`CURRENT_DOCUMENTS.sha256`](../CURRENT_DOCUMENTS.sha256), following the
[verification command](../README.md#file-identities). For the principal saved
data and images, use the current [`sha256.tsv`](sha256.tsv).
