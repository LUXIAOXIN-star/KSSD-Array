# Minimap2 indexing and accuracy experiments

## Manuscript reference

Supplementary Section S4 and Tables S10–S12. [Results](../../benchmark_results/supplementary_s4_minimap2/README.md).

## Experimental objective

Minimap2 indexing and accuracy experiments.

## Required inputs

Full reference FASTA files and, for accuracy, simulated reads, truth and alignments. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Reference indexing and historical mapping accuracy use different integrations and inputs.

## Parameters

Single-thread three-reference indexing; historical external-call accuracy; separate Human multi-thread indexing.

## Software dependencies

Minimap2 2.30-r1287 and the integration relevant to each task, plus zlib and required analysis tools. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Use the exact build record for each experiment; do not combine compiler settings.

## Build command

See the three task-specific subdirectories for current entry status.

## Execution command

See each subdirectory; no single combined benchmark is claimed.

## Output description

Index times and sizes, accuracy counts, or multithread indexing times.

## Result verification

Verify versions, inputs and repeat units separately.

## Current validation status

HISTORICAL_DATA_AVAILABLE; complete independent replay is not established.
