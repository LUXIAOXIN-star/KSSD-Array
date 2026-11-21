# Controlled Alu localization and seed workload

## Manuscript reference

Supplementary Section S3.5 and Table S9. [Results](../../benchmark_results/supplementary_s3_5_alu/README.md).

## Experimental objective

Controlled Alu localization and seed workload.

## Required inputs

Reference-derived chr21/chr22 queries and matching reference sequences. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Preserve cohort, strand and known source locus; queries and coordinates are not distributed.

## Parameters

k=21, w=20, four methods and two frequency policies.

## Software dependencies

C++17, original fixed permutation table and exact external reference/query inputs. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

The historical mapper source is retained as `read_mapper_four.cpp`; historical compiler details require the original build record.

## Build command

No complete portable build is verified without the full authorized inputs.

## Execution command

No verified full runner is supplied.

## Output description

Per-read placements, selected candidate diagnostics and timing summaries.

## Result verification

Alternative locations exclude only the exact known source locus; candidate trace covers a selected subset, not every candidate position.

## Current validation status

HISTORICAL_DATA_AVAILABLE; distribution of reference-derived reads/coordinates and complete replay remain unverified.
