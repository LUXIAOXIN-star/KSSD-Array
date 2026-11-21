# Forward-only runtime and minimizer sampling density

## Manuscript reference

Main Figure 3 and Supplementary Table S5. [Results](../../benchmark_results/figure3_runtime_density/README.md).

## Experimental objective

Forward-only runtime and minimizer sampling density.

## Required inputs

Synthetic 10 Mb and the specified 10 Mb chr1 interval. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Same in-memory DNA; include conversion, full score arrays, common selector and selected-position output.

## Parameters

k=21,31; w=20; five independent processes per condition; KSSD-Array, seq-hash and GreedyMini-derived prefix12.

## Software dependencies

Recorded Rust and C toolchains and exact external seq-hash and GreedyMini order are needed for a new benchmark. The frozen Rust driver includes a direct ntHash reference formula and remains unavailable pending its third-party provenance review. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Recorded historical C and Rust optimization settings apply; complete build dependencies are not all distributed.

## Build command

No verified complete benchmark build command is available in this collection.

## Execution command

The earlier redraw adapter is not included in this package. No portable redraw command is currently provided.

## Output description

Mean runtime, selected positions, density, and figure from saved data.

## Result verification

The historical plotter and input are retained, but their original file-layout and provenance dependencies are not all present. A portable redraw has not been verified for this package.

## Current validation status

HISTORICAL_DATA_AVAILABLE: the full benchmark was not rerun; a portable redraw adapter and some benchmark dependencies are not included.
