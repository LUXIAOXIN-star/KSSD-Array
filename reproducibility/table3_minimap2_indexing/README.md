# Full single-thread reference indexing

## Manuscript reference

Main Table 3 and Supplementary Table S10. [Results](../../benchmark_results/table3_minimap2_indexing/README.md).

## Experimental objective

Full single-thread reference indexing.

## Required inputs

Arabidopsis, Human GRCh38.p14, and maize B73 reference files. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Preserve the recorded compression, file identity and whole-reference parsing.

## Parameters

k=15, w=10, no HPC; one thread; five paired process measurements.

## Software dependencies

Minimap2 2.30-r1287, commit 79c9cc186b95f50bd899f69b48eba995ced810c6; inline integration, zlib and matching references. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Historical Minimap2 build uses GCC 9.4 with `-g -Wall -O2 -Wc++-compat`; KSSD core flags must be read from its separate record.

## Build command

A portable complete build entry is not yet verified.

## Execution command

See the inline-indexing subdirectory under `supplementary_s4_minimap2/`; do not execute historical paths directly.

## Output description

Full-process elapsed time, index size and index statistics.

## Result verification

Check input SHA, version/patch identity and per-process logs; methods need not produce identical indexes.

## Current validation status

HISTORICAL_DATA_AVAILABLE; complete portable replay remains blocked by inputs/build packaging.
