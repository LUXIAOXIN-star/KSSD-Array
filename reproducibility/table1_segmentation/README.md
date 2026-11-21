# Balanced segment layout and memory accounting

## Manuscript reference

Main Table 1. [Results](../../benchmark_results/table1_segmentation/README.md).

## Experimental objective

Balanced segment layout and memory accounting.

## Required inputs

Two-bit encoded k-mer configuration, no sequence file. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Initialize a context for the required k and seed.

## Parameters

C=8; k=1–32; deterministic fixed-width segments.

## Software dependencies

Core C11 library. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Project Makefile or CMake; no external hashing dependency.

## Build command

make && make examples && make test

## Execution command

```sh
./build/examples/minimal_api
```

## Output description

Context, segment lengths and mapped score.

## Result verification

Core examples and tests were previously checked in an isolated build.

## Current validation status

VERIFIED for the small core build; this does not constitute a benchmark rerun.
