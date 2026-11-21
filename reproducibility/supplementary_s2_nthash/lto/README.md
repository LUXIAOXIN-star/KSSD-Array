# LTO sensitivity of the ntHash comparison

## Manuscript reference and objective

Supplementary Section S2.3 and Table S4 measure LTO OFF/ON separately from the main ntHash comparison.

## Inputs and processing

The same two exact FASTA files as the ntHash 40-condition experiment are required; see the [dataset guide](../../../docs/datasets.md). First-record non-ACGT characters are deleted before concatenation. Inputs are external and must match their recorded SHA values.

## Parameters and dependencies

GCC/G++ 11.4.0, C++17, zlib, KSSD-Array and ntHash 2.4.0; k=15/19/21/24/31 and w=5/10/20/50. Each of 80 processes contains five paired technical repeats. OFF uses `-O3 -march=native -DNDEBUG -fno-lto`; ON uses `-O3 -march=native -DNDEBUG -flto` at compilation and final linkage.

## Build and execution

The independent historical path-adapted validation workspace is not distributed here: its scripts and input/output assumptions require additional public packaging. A complete portable build and run command is **not available**. Do not run the original fixed-path launcher against historical results. A future replay must check both input SHA values, 80 schedule rows, CPU affinity and frozen source hashes, and use a fresh isolated output.

## Output and verification

Historical measurements, source identity and summary are addressed by [the ntHash results](../../../benchmark_results/supplementary_s2_nthash/README.md). The LTO build and small correctness checks previously passed, but they are not the 80-process performance grid.

## Validation status

**BLOCKED / NOT_FULLY_REPLAYED:** no portable public LTO package or new 80-process grid has been verified. Do not reuse historical timings as new measurements.
