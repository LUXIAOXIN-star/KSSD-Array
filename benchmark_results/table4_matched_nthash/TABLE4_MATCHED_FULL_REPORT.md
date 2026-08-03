# Table 4 matched-workload descriptive full-grid report

Generated: `2026-07-31T17:59:49+08:00`

This is a separate descriptive K=W=4..32 experiment. It is not a continuation of, and does not alter, the stopped pilot. No pilot measurement was reused.

## Identity and validation

- Repository HEAD: `8922a3031a7ad327cbcac6f1e80748dff654537b`
- ntHash: 2.4.0, commit `c26bd4572a19de81e30d55042dbd33c1fd21d4b6`.
- ntHash canonical score: `forward_hash + reverse_hash` modulo 2^64.
- KSSD canonical input: `min(forward_kmer, reverse_complement_kmer)`.
- Normal and ASan/UBSan validations passed at K=4, 21, and 32.
- Strict preflight passed at `2026-07-31T16:27:25+08:00` with load `[0.55, 0.26, 0.15]` and no active swap I/O.

## Timing boundary

Both methods start from the identical cleaned first FASTA record, generate one strand-invariant score per k-mer inside timing, write each score once to the same W-element uint64 ring, reuse ring values during rescans, and run the same strict-`<`, leftmost-tie minimizer and checksum. One minimum is processed per window with no adjacent-window deduplication. FASTA I/O/cleaning, allocations, context/object initialization, validation, warm-up, and output are outside timing.

## Across-K results

- GRCh38.p14 chr1: geometric mean per-K speedup `1.099250676168`; median `1.078389690359`; KSSD faster at `25/29` K values; ntHash faster at `4/29`; range `0.972971329011` to `1.271228497563`.
- Synthetic 300 Mb: geometric mean per-K speedup `1.126204247659`; median `1.102914146465`; KSSD faster at `27/29` K values; ntHash faster at `2/29`; range `0.992560357169` to `1.312014871695`.

`matched_table4_by_k.csv` contains runtime and throughput means and sample SDs, every per-repeat paired ratio, median/geometric mean/range, and wins. Across-K summaries aggregate per-K median paired speedups and deliberately do not call an across-K runtime SD experimental uncertainty.

## Comparison

The stopped K=21 pilot reported median throughput ratios 1.070389 (Synthetic 300 Mb) and 1.048042 (GRCh38.p14 chr1), with the latter inside its predeclared inconclusive interval. This full grid was authorized separately and does not revise that decision.

The historical approximately 2.9-fold Table 4 value measured method-native workloads: pre-materialized forward KSSD inputs versus timed rolling canonical ntHash. The present matched-workload ratios measure a different timing boundary and must not be described as estimates of the same workload.

## Limitations

- Score orderings differ: KSSD maps a minimum two-bit canonical integer; ntHash uses its official modular-sum canonical hash.
- Parsing and ambiguity removal are outside timing.
- Separate processes reduce direct method-to-method warming, but the warm-cache/page-cache state and CPU frequency remain host-specific.
- `-march=native` binds these measurements to the recorded CPU.
