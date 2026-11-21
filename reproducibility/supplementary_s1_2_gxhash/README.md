# Separate gxhash score-only comparison

## Manuscript reference

Supplementary Section S1.2 and Table S2. [Results](../../benchmark_results/supplementary_s1_2_gxhash/README.md).

## Experimental objective

Separate gxhash score-only comparison.

## Required inputs

Same preencoded arrays for KSSD, XXH3 and gxhash. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Exclude DNA encoding, initialization and allocation from scoring timer.

## Parameters

Two inputs, five k values, three methods, five independent processes.

## Software dependencies

Official gxhash 3.5.0, pinned XXH3 v0.8.3, Rust, C and compatible CPU instructions. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Use separately recorded Rust and C build options and LTO settings.

## Build command

A portable complete build requires its exact original source and locked dependencies.

## Execution command

No verified full runner is distributed in this directory. The historical [C driver](historical_source/score_driver.c) and the adjacent Phase 1 source snapshot are retained with their original relative include paths; the required gxhash wrapper and complete external dependencies are not included.

## Output description

150 process measurements and summary in the associated result directory.

## Result verification

Each method hashes one 8-byte input per k-mer; validate each implementation independently.

## Current validation status

HISTORICAL_DATA_AVAILABLE; no timing from a different run may be spliced into its summary.
