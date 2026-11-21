# Thread scaling of preencoded scoring and window processing

## Manuscript reference

Supplementary Figure S1. [Results](../../benchmark_results/supplementary_s1_multithreading/README.md).

## Experimental objective

Thread scaling of preencoded scoring and window processing.

## Required inputs

Synthetic 300 Mb and processed GRCh38.p14 chr1. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

First FASTA record, delete non-ACGT then encode before timing.

## Parameters

k=21, w=10/20/50; 1,2,4,8,16 requested threads; five measurements.

## Software dependencies

Original OpenMP driver, KSSD and recorded shared xxHash. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Consult the historical build manifest; its original wrapper SHA was not frozen in that manifest.

## Build command

The original wrapper is tied to a historical layout and is not a verified portable build.

## Execution command

A safe complete launcher has not been verified.

## Output description

Mean throughput in million windows/s, with per-repeat data.

## Result verification

Check five repeats for each input/method/thread/w condition.

## Current validation status

HISTORICAL_DATA_AVAILABLE; this is not main Figure 3 or Minimap2 indexing.
