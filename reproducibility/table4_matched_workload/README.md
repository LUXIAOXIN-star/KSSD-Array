# Table 4 matched-workload benchmark

This workflow is separate from the historical `reproducibility/table4`
implementation and does not replace its method-native measurements.

The matched benchmark starts both methods from the same cleaned first FASTA
record. Each timed path generates exactly one strand-invariant score per k-mer,
stores it in the same `std::vector<uint64_t>` ring buffer, and calls the same
sliding-window minimum implementation. The shared implementation uses strict
less-than comparisons, retains the leftmost score on ties, emits one minimum
per window without adjacent-window deduplication, reuses ring values on a
rescan, and applies the same checksum update.

The KSSD-Array path times rolling forward and reverse-complement two-bit
encoding, `min(forward, reverse_complement)` integer canonicalization, current
release fixed-k fast mapping, ring storage, minimizer selection, and checksum
updates.

The ntHash path directly uses the pinned official C++ `nthash::NtHash` API. It
times first and rolling forward/reverse hash generation, the official
strand-invariant score, ring storage, minimizer selection, and checksum
updates. ntHash 2.4.0 defines that canonical score as
`forward_hash + reverse_hash` modulo 2^64; this is not the same numerical
formula as KSSD-Array's minimum integer encoding.

FASTA I/O, first-record cleaning, allocation, KSSD context initialization,
ntHash object construction, validation, warm-up, and output are outside the
timers.

Run the predeclared validation, pilot, decision, and conditional full grid with:

```sh
python3 reproducibility/table4_matched_workload/run_matched_workload.py
```

Use `--nthash-source PATH` or set `NTHASH_SOURCE` when the pinned ntHash
checkout is not at the default `$HOME/ntHash` location. Input defaults may be
overridden with `KSSD_SYNTHETIC_FASTA` and `KSSD_HUMAN_FASTA`; set
`KSSD_FORMAL_RESULTS` or pass `--output-root` to select an external result
location.

The driver verifies the two retained input hashes, rebuilds ntHash commit
`c26bd4572a19de81e30d55042dbd33c1fd21d4b6` with the same performance
optimization flags, builds normal and ASan/UBSan validation executables for
K=4, 21, and 32, records system preflight state, pins each measured process to
one physical CPU with `taskset`, and alternates method order. It stops before
the pilot when the preflight detects active swap I/O, severe load, or a
high-usage process on the selected CPU.

The pilot uses K=W=21, one symmetric untimed warm-up, and seven measured
repeats per method and dataset. The complete K=W=4..32 grid is launched from
scratch only when both datasets have median paired KSSD/ntHash throughput ratio
at least 1.05, KSSD is faster in at least five of seven repeats on each, and
all validation and state checks pass.
