# Long-sequence streaming comparison

## Manuscript reference

Supplementary Section S3.2 and Table S6. [Results](../../benchmark_results/supplementary_s3_2_streaming/README.md).

## Experimental objective

Long-sequence streaming comparison.

## Required inputs

Long DNA input, including non-ACGT positions. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Non-ACGT characters are boundaries: no k-mer or window crosses them.

## Parameters

Preserve the 11 parameter slots, P11 repeat confirmation and mod-minimizer fallback.

## Software dependencies

KSSD, GreedyMini-derived order and fixed mod-minimizer; unresolved versions are not included. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

The saved build record distinguishes the C++ and Rust builds.

## Build command

A fully distributable sampler build remains blocked by dependencies/permissions.

## Execution command

The separate preflight entry is not included in this package.

## Output description

Historical results report selected counts, timing and density.

## Result verification

Validate input SHA, boundary counts, P11 and fallback.

## Current validation status

BLOCKED for a complete sampler build: required fixed third-party dependencies and the separate preflight are not included.
