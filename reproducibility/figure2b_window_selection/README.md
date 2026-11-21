# Scoring and minimum selection by per-window rescan

## Manuscript reference

Main Figure 2b. [Results](../../benchmark_results/figure2b_window_selection/README.md).

## Experimental objective

Scoring and minimum selection by per-window rescan.

## Required inputs

The same two preencoded sequence workloads as Figure 2a. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Read the first FASTA record, delete non-ACGT and encode before timing.

## Parameters

k=16,19,21,24,31; w=10,20,50; five process repeats; five methods.

## Software dependencies

C11, authorized historical benchmark source, dynamic xxHash 0.7.3 and Python 3. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

Historical core `-O2`; driver `-O3 -march=native`, with dynamic xxHash.

## Build command

Compile the included historical C program using the requirements in the Figure 2 workflow; use a new build directory.

## Execution command

The historical C program is included under `reproducibility/figure2/`; the independent wrapper used by an earlier package is not included here. See that directory for source and input requirements.

## Output description

Windows/s, counts and checksums for each process; no read mapping.

## Result verification

Source/input SHA, output counts and repeated checksums.

## Current validation status

PARTIAL: the included C program was built in an isolated directory and run on a small input at k=21, w=20. It reported five methods, 1,061 windows each and a passing KSSD fast/reference parity check. This was not a formal performance rerun.
