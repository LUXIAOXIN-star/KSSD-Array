# Supplementary section S3.3 and Tables S7a–S7c

External SIMD comparison under three distinct workloads.

Two 10 Mb inputs, k = 21/31. A has no w; B and C use w = 20/50; five independent processes per condition.

`A/` records DNA-to-score generation, `B/` score materialization plus a common selector, and `C/` complete native pipelines. Path-only columns were removed from these historical tables, producing derived copies; B/C use the documented weak-canonical settings and C uses 16-bit ranking.

These are saved historical results, not a new performance run. The experiment-specific reproduction materials and validation limitations are documented in `reproducibility/supplementary_s3_3_external_simd/` when available; see the [results index](../README.md) and [dataset guide](../../docs/datasets.md).
