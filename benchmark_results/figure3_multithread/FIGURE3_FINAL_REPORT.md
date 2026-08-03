# Figure 3 final-release controlled rerun

Generated: `2026-07-31T19:32:37+08:00`

## Completion and execution policy

- All 30 dataset/W/thread groups completed with five repeats and five methods (750 raw rows).
- Repository HEAD: `8922a3031a7ad327cbcac6f1e80748dff654537b`.
- The process was pinned to physical-core CPU set `0-15`; CPUs 0--15 map to distinct core IDs and exclude SMT siblings 16--31.
- `OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=TRUE`, and `OMP_PLACES=cores` were set for every invocation.
- Requested threads equalled observed threads in all 750 method-level records.
- Strict preflight passed at `2026-07-31T19:03:37+08:00` with one-minute load `0.280`, 54.35 GiB available memory, and no active swap-in/swap-out.

## Protocol scope

The current public workflow was run unchanged. It reads only the first FASTA record and skips non-ACGT symbols without resetting the rolling encoder. Parsing, two-bit k-mer materialization, context initialization, parity checking, and wyhash-secret creation are outside each timed method. Timed OpenMP regions use manual contiguous window partitions, strict `<` leftmost-minimum selection, one output per window, deterministic checksum merging, and no adjacent-window deduplication.

Methods execute in the fixed source order KSSD-Array, XXH3, XXH64, MurmurHash3, wyhash within every process. The runner does not randomize method order; this is a limitation.

## Scaling and rankings

Mean throughput, sample SD, speedup relative to the one-thread mean, and parallel efficiency are recorded for all 150 dataset/W/thread/method cells in `figure3_scaling_summary.csv`.

- KSSD-Array won `30/30` final groups (historical preliminary: `30/30`).
- XXH3 won `0/30` final groups (historical preliminary: `0/30`).
- XXH64 won `0/30` final groups (historical preliminary: `0/30`).
- MurmurHash3 won `0/30` final groups (historical preliminary: `0/30`).
- wyhash won `0/30` final groups (historical preliminary: `0/30`).

Historical all-group KSSD leadership reproduced: **YES**.

Fastest-method changes: `0`. Full five-method ordering changes: `30`.

The complete final and historical order for every condition is in `figure3_ranking_comparison.csv`. Historical values are comparison data only and were not reused as final measurements.

## Manuscript implication

Use the final-release means and sample SDs if Figure 3 is presented as a measurement of the tagged public implementation. Do not mix the historical preliminary values with these results. Absolute throughput and scaling remain dependent on this host, compiler, OpenMP runtime, fixed method order, and the first-record-only input scope.
