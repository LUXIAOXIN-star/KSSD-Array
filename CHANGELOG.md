# Changelog

## 1.1.0 — 2026-07-31

- Added the public runtime-selected `kssd_array_inline_plan_t` and
  always-inline mapper for `k=1..32` while retaining the generic API.
- Added all-k, fixed-vector, boundary, exhaustive-small-domain, deterministic
  random, ASan, and UBSan equivalence coverage.
- Updated the pinned Minimap2 integration to initialize one inline plan per
  index and perform direct table lookup/recombination inside `mm_sketch`.
- Confirmed the final executable hot path by symbol and assembly inspection,
  and confirmed byte-identical fixture and GRCh38 KSSD index output.
- Updated the Supplementary Figure S1/Table S1 workflow to one warm-up and
  five alternating pairs per dataset with controlled resume, swap-polluted
  attempt preservation, paired ratios, final figures/tables, and complete
  identity/output manifests.
- The runtime-inline API is additive. Figure 2, matched-workload Table 4, and
  Figure 3 timed sources and the fixed-k header are unchanged.

## 1.0.0-paper — 2026-07-28

Repository: https://github.com/LUXIAOXIN-star/KSSD-Array

- Added the canonical C11 rank-derived permutation-array library, checked
  context API, and compile-time fixed-k fast path.
- Added exact exhaustive 9-mer validation for Table 2.
- Migrated functional workflows for Figure 2, Table 4, and Figure 3.
- Reproduced Figure 4 at the summary and plotted-data layers.
- Added a pinned, patch-based Minimap2 2.30 integration.
- Retained the manuscript's accepted low-load Supplementary Figure S1/Table S1
  values and published the complete reproducible indexing workflow with a
  lightweight preflight.
- Formally reproduced Supplementary Table S2 displayed deltas.
- Added installation metadata, public provenance, repository checks, and
  lightweight CI preparation.
