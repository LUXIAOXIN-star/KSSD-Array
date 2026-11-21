# Task A: rolling score generation

Supplementary Table S7a compares KSSD-Array full-width scoring and seq-hash's native 32-bit scores on two 10-Mb DNA inputs, with k=21/31 and five independent measured processes per condition. Its measured stage includes rolling score generation and score array allocation and writes; input reading and reusable setup are excluded. No window-selection time is part of Task A.

The KSSD code and benchmark driver parts recorded for this experiment are in the parent `historical_source/`; some code and exact third-party versions are deliberately not redistributed while their source/license provenance is reviewed. Original C build used `-O3 -march=native` and Rust release used opt3, native CPU, thin LTO and 16 codegen units. The exact inputs and hashes are in [the dataset guide](../../../docs/datasets.md), with fixed versions in [dependencies](../../../docs/dependencies.md).

A complete isolated build/run command has not yet been verified. Never use the historical runner against its old results directory. Validate the input, method output width, processed counts and per-run checksums before measuring.

**Status: HISTORICAL_DATA_AVAILABLE / NOT_FULLY_REPLAYED.** [A/B/C results](../../../benchmark_results/supplementary_s3_3_external_simd/README.md).
