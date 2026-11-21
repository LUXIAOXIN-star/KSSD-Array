# External SIMD score and minimizer comparisons

## Manuscript reference

Supplementary Section S3.3 and Tables S7a–S7c. [Results](../../benchmark_results/supplementary_s3_3_external_simd/README.md).

## Experimental objective

External SIMD score and minimizer comparisons.

## Required inputs

Synthetic 10 Mb and the specified human chr1 10 Mb interval. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Maintain each task’s original conversion, chain handling and output requirements.

## Parameters

A: scoring; B: scoring plus common selector; C: complete native sampling; k=21/31, w=20/50 for B/C; five process repeats.

## Software dependencies

Recorded seq-hash and simd-minimizers versions, fixed Cargo.lock and required SIMD CPU features. The fixed driver validation source includes a direct ntHash formula and is not redistributed pending its third-party provenance review. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Historical C `-O3 -march=native`; Rust release opt3, thin LTO, 16 codegen units, native CPU target.

## Build command

A complete build remains blocked until fixed third-party licensing and dependencies are established.

## Execution command

No complete portable benchmark command is currently verified.

## Output description

A/B/C raw data, checksums and summaries are kept separate.

## Result verification

Use the exact timing boundary and score width of each task; do not combine their results.

## Current validation status

HISTORICAL_DATA_AVAILABLE; unresolved versions are not redistributed and no full replay was done.

## Separate task descriptions

- [A: score generation](A_score_generation/README.md)
- [B: common selector](B_common_selector/README.md)
- [C: complete native pipelines](C_end_to_end/README.md)
