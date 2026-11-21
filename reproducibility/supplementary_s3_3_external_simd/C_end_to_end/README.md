# Task C: complete native pipelines

Supplementary Table S7c compares KSSD-Array and native simd-minimizers from DNA to retained positions on the same two 10-Mb inputs. k=21/31, w=20/50, five independent processes; the recorded setting is weak canonical. Native simd-minimizers uses high 16-bit ordering values; KSSD retains its own full score. Conversion, selection, allocation, and adjacent-position deduplication follow the individual native implementations.

The project-owned driver parts are in the parent `historical_source/`. Exact third-party sources and some reference-validation material are not distributed pending version-specific source/license review. Original C build used `-O3 -march=native`; Rust release used opt3, native CPU, thin LTO and 16 codegen units. See [datasets](../../../docs/datasets.md) and [dependencies](../../../docs/dependencies.md).

A complete independently verified build/run command is not available. Preserve native inputs, chain rules, output widths, counts and checksums; different methods are not required to select identical positions. Do not substitute Task A or B timing.

**Status: HISTORICAL_DATA_AVAILABLE / NOT_FULLY_REPLAYED.** [A/B/C results](../../../benchmark_results/supplementary_s3_3_external_simd/README.md).
