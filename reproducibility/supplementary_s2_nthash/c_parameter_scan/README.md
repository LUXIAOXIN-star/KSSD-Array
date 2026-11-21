# Segment-cap sensitivity

## Manuscript reference and objective

Main Section 3.3 compares C=4–8 choices. This diagnostic is separate from ntHash and LTO timing.

## Inputs and parameters

The original two processed sequences and k=16/19/21/24/31 are required. Saved scoring, common-window and initialization records use their own repeat definitions; consult the [dataset guide](../../../docs/datasets.md) and the result summary.

## Source and dependencies

`c_sensitivity.c` is a byte-identical copy of the recorded scientific source. It relies on the corresponding KSSD build and historical configuration. The frozen runner also performed other tasks and contains original path assumptions.

## Build and execution

A complete independently verified portable build command is not available here. Do not run the historical runner in place or combine C-scan observations from distinct workloads.

## Output and verification

The retained benchmark data include 250 score records, 750 common-window records and 250 initialization records. The published cross-condition geometric summary is not an arithmetic mean ± repeat SD.

## Validation status

**HISTORICAL_DATA_AVAILABLE / NOT_FULLY_REPLAYED.** No formal performance grid was rerun in this packaging.
