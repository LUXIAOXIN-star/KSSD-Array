# Existing benchmark impact assessment

Date: 2026-07-31 (Asia/Shanghai)

Baseline commit:
`8922a3031a7ad327cbcac6f1e80748dff654537b`.

## Scope and result

The public runtime-inline API is additive.  Figure 2, matched-workload Table
4, and Figure 3 continue to use `kssd_array_fast_with_tables()` from
`include/kssd_array_fast.h` in their timed KSSD paths.  The generic
`kssd_array_map_unchecked()` calls in those benchmark sources are parity
checks performed before timing; none was replaced with the new runtime-inline
API.

`git diff --quiet` against the baseline passed for the fixed-k header and all
three workflow directories:

```text
include/kssd_array_fast.h
reproducibility/figure2/
reproducibility/table4/
reproducibility/figure3/
```

Therefore no existing timed source path changed.  Their existing results
remain source-valid, and the workflows were not rerun.

## Unaffected source hashes

For every entry below, the working-tree SHA-256 equals the SHA-256 obtained
from the same path at the baseline commit.

| Path | SHA-256 |
|---|---|
| `include/kssd_array_fast.h` | `b64c3a14b9df415dcc73eebde920c113518fec46b26862b848491b4ca3cde5f4` |
| `reproducibility/figure2/benchmark_single_thread_realistic_kw.c` | `9bc61b12e2ec9e87382339070103fad042fdd2bc6c8baaf1a9d468ab425ca1c1` |
| `reproducibility/figure2/run_figure2_single_thread.py` | `6b30e2ebd885e8602d898e6f24a8b77d7449db190dce4385633b1601c5ab7227` |
| `reproducibility/table4/benchmark_table4_nthash.cpp` | `597e9691455a26d6d309ed46ee27400faf3f66fbec017444dbbe28ea1da5a28f` |
| `reproducibility/table4/run_table4_nthash.py` | `a305e2e14509f92aa491a1b0c2dea79ec297ca45459360445b00e9811aa0dd67` |
| `reproducibility/figure3/benchmark_multithread_k21.c` | `60c73dd883e44cfafcd8dca11bdb8c522946a345815360f54443ea47a984dc96` |
| `reproducibility/figure3/run_figure3_multithread.py` | `c8b2b23cda70aa273aa321a136f9784d721e0d2c2dfd969328227fcaf07a80e1` |

## Decision

- Figure 2: no rerun required.
- Matched-workload Table 4: no rerun required.
- Figure 3: no rerun required.
- Supplementary Figure S1/Table S1: rerun completed because its Minimap2 hot
  path was intentionally changed.
