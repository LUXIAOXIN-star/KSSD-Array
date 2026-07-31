# Implementation boundary

The public `src/` implementation is the only active rank-derived
implementation.

The canonical C11 implementation is `src/kssd_array.c` and
`src/permutation.c`, exposed by `include/kssd_array.h`. It was reconstructed
and validated against the accepted manuscript implementation. Equal `k`,
seed, and RNG mode produce deterministic tables. The supported encoded domain
is `1 <= k <= 32`, and mapping returns a value in `[0, 4^k)`.

- `src/permutation.c` owns master permutation construction and rank-derived
  short tables.
- `src/kssd_array.c` owns segmentation, extraction, reconstruction, and
  context lifetime.
- `include/kssd_array_inline.h` is the public runtime-selected, plan-based
  always-inline hot path over context-owned tables.
- `include/kssd_array_fast.h` is a thin inline hot path over those tables.
- Benchmarks call public APIs and do not contain another KSSD table generator.
- The two Table 2 ablations are deliberately lossy local comparison methods.
- The Minimap2 patch is an adapter to public APIs, not an implementation copy.

Core tests cover ownership, error handling, concurrent read-only mapping,
injectivity on small domains, and parity between generic, runtime-inline, and
fixed-k APIs. Both inline headers perform only the mapping hot path against the
same context-owned tables.

`tools/check_public_tree.py` scans C and C++ files for known duplicate
implementation markers outside the allowed implementation and validation
boundaries.
