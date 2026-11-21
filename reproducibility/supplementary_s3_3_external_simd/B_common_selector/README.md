# Task B: common window selector

Supplementary Table S7b compares KSSD-Array and seq-hash through one shared window selector after materializing scores on the same two 10-Mb inputs. k=21/31, w=20/50, five independent processes; the recorded selection setting is weak canonical. Its timing boundary and output must remain distinct from Task A and from Task C.

The project-owned driver parts are in the parent `historical_source/`. Exact third-party sources and some reference-validation material are not distributed pending version-specific source/license review. Original C build used `-O3 -march=native`; Rust release used opt3, native CPU, thin LTO and 16 codegen units. See [datasets](../../../docs/datasets.md) and [dependencies](../../../docs/dependencies.md) for fixed identities.

A complete independently verified build/run command is not available. Before any later run, check fixed inputs, chain handling, selection/dedup rules, result counts and per-run checksums. Do not merge its measurements with a forward-only density experiment.

**Status: HISTORICAL_DATA_AVAILABLE / NOT_FULLY_REPLAYED.** [A/B/C results](../../../benchmark_results/supplementary_s3_3_external_simd/README.md).
