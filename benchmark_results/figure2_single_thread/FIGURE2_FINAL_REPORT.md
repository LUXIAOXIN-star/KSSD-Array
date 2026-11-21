# Figure 2 final-release formal rerun

Generated: `2026-07-31T18:58:22+08:00`

## Completion and identity

- All 30 dataset/K/W groups completed with five repeats and five methods (750 raw rows).
- Repository HEAD: `8922a3031a7ad327cbcac6f1e80748dff654537b`.
- Inputs matched pinned SHA-256 identities: `Synthetic 300 Mb, GRCh38.p14 chr1`.
- Strict preflight passed at `2026-07-31T18:03:04+08:00` with one-minute load `0.300`, no active swap I/O, and CPU 15 available.

## Protocol scope

The current public workflow was run unchanged. It reads only the first FASTA record, removes non-ACGT symbols without resetting the rolling encoder (so valid sequence can bridge ambiguous regions), and performs FASTA parsing, two-bit k-mer materialization, context initialization, and parity validation outside timing. Each timed method uses strict `<`, retains the leftmost minimum on ties, processes one minimum per window, and performs no adjacent-window deduplication.

The five methods execute in the fixed source order KSSD-Array, XXH3, XXH64, MurmurHash3, wyhash within one process. The runner does not randomize method order; this is a limitation. The process and all children inherited `taskset -c 15`.

KSSD uses deterministic seed 42. The wyhash eight-byte path uses zero input-seed semantics and a deterministic `wy_make_secret` derived from run seed 42.

## Ranking result

- KSSD-Array won `30/30` accepted final groups.
- XXH3 won `0/30` accepted final groups.
- XXH64 won `0/30` accepted final groups.
- MurmurHash3 won `0/30` accepted final groups.
- wyhash won `0/30` accepted final groups.

Per-group accepted throughput and rankings for all methods are in
`figure2_ranking_summary.csv`. Absolute throughput is host- and
release-specific; ranking robustness is judged separately from exact numerical
reproduction.

## Manuscript implication

Use these accepted values if the manuscript claims final-release performance.
The qualitative leadership claim is limited to the final group win counts
above. The fixed method order and absence of plotted uncertainty remain
limitations.
