# Public runtime-inline API changelog

Date: 2026-07-31 (Asia/Shanghai)

Proposed release: `v1.1.0`

## Public API

- Added `include/kssd_array_inline.h`.
- Added `kssd_array_inline_plan_t`, which stores a precomputed segment count,
  input shifts/masks, output shifts, and up to four direct `uint16_t`
  permutation-table pointers borrowed from a current `kssd_array_t`.
- Added the cold-path `kssd_array_inline_plan_init()` function.
- Added `kssd_array_inline_map_unchecked()` as a public `static inline`
  function with `always_inline` on GCC/Clang.  Its one-to-four-segment switch
  is unrolled and calls neither the generic mapper nor a per-k-mer table
  selector.
- Retained `kssd_array_map_unchecked()` unchanged as a public compatibility
  API.

The plan supports every public `k` from 1 through 32.  It borrows pointers,
so the source context must outlive the plan and must not be destroyed or
mutated while mapping is active.

## Integration

- Updated the pinned Minimap2 2.30 patch to store the context and inline plan
  in Minimap2-owned state.
- Plan initialization occurs once after context initialization.
- `mm_sketch` now invokes the header-inline mapper directly on the canonical
  encoded k-mer; the former hot-loop external adapter is absent.
- The final executable contains direct permutation-table lookup and
  recombination instructions in `mm_sketch`, with no call to either prohibited
  mapping symbol.

## Validation and reproducibility

- Added parity coverage for both RNG modes and all `k=1..32`, including 100,000
  deterministic random inputs per k/RNG combination and exhaustive domains
  through `k=9`.
- Added the parity test to Make, CMake/CTest, ASan, and UBSan workflows.
- Installed the new header through both Make and CMake install paths.
- Confirmed byte-identical fixture index/alignment output and byte-identical
  GRCh38.p14 index output at the preserved `k=15,w=10` settings.
- Completed the controlled three-dataset Supplementary Figure S1/Table S1
  rerun with five paired repeats per dataset.
- Added atomic raw-data updates, controlled resume, preservation/retry of
  environment-filtered attempts, paired-ratio output, output hashes, and final
  S1 figure/table generation to the public workflow.

## Compatibility and unaffected results

The new API is additive.  Figure 2, matched-workload Table 4, and Figure 3
continue to use the byte-identical fixed-k header and unchanged timed sources;
their existing results remain source-valid.  No manuscript file or historical
result directory was modified or deleted.
