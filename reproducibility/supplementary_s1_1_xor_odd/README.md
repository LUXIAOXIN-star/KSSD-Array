# Independent scoring of XOR, odd multiplication and KSSD controls

## Manuscript reference

Supplementary Section S1.1 and Table S1. [Results](../../benchmark_results/supplementary_s1_1_xor_odd/README.md).

## Experimental objective

Independent scoring of XOR, odd multiplication and KSSD controls.

## Required inputs

Preencoded canonical k-mers under the saved protocol. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Use the same inputs and mapping table for every method.

## Parameters

k=21; four methods; 24 timed observations per method and group. Full natural stream uses one traversal per observation; the private-cache diagnostic uses its recorded repeated sweeps.

## Software dependencies

C++17 and recorded compiler/toolchain. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Use the timing manifest for the exact build; original source is retained under `historical_source/`.

## Build command

A safe end-to-end portable build is not verified.

## Execution command

No verified complete runner is supplied here.

## Output description

Separate per-method timing records and summaries.

## Result verification

Preserve the technical-repeat unit; do not reinterpret as independent process repeats.

## Current validation status

HISTORICAL_DATA_AVAILABLE; no formal benchmark was rerun.
