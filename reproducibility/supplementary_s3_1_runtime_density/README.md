# Results accompanying the materialized-score runtime and density figure

## Manuscript reference

Supplementary Section S3.1 and Table S5. [Results](../../benchmark_results/supplementary_s3_1_runtime_density/README.md).

## Experimental objective

Results accompanying the materialized-score runtime and density figure.

## Required inputs

Two 10 Mb DNA inputs. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Forward-only; conversion, scores, common selector and deduplicated output are included.

## Parameters

k=21/31, w=20; five independent processes.

## Software dependencies

KSSD, seq-hash and GreedyMini-derived prefix12; exact third-party dependencies/order required. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Use the build and environment evidence for the original run.

## Build command

No complete portable build is currently verified.

## Execution command

The previous portable redraw adapter is not included. The saved figures and data are retained.

## Output description

Runtime, selected count, density, figure and saved records.

## Result verification

Track original SHA for exact files and label path-tokenized data as derived.

## Current validation status

HISTORICAL_DATA_AVAILABLE; neither the complete benchmark nor a portable redraw was rerun for this package.
