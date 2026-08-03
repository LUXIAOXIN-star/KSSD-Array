# Figure 3 multithread benchmark workflow

This directory contains the portable five-method multithread minimizer
workflow associated with Figure 3. Phase 4C validates builds, thread ownership,
deterministic merging, and single-thread semantic equivalence. Its smoke output
is not a formal performance reproduction, and no speedup or ranking is required.

## Methods and public KSSD API

Exactly five methods are active: KSSD-Array, XXH3, XXH64, MurmurHash3, and
wyhash. The obsolete sixth comparator from the historical program was removed
with its implementation, branch, output row, and plot entry.

One `kssd_array_t` context is initialized with `kssd_array_init` before any
timed parallel region. Up to 1,024 encoded k-mers are compared through
`kssd_array_map_unchecked` and `kssd_array_fast_with_tables` outside timing.
Worker threads share only a const pointer to the initialized context and call
the public fast API in the timed path. The main thread destroys the context
after all method regions have joined. The executable links
`build/libkssd_array.a`; it does not compile KSSD core sources.

## Partition and deterministic merge

OpenMP workers receive contiguous, non-overlapping ranges of minimizer-window
indices using integer proportional partitioning. A worker owning windows
`[a,b)` reads k-mers through `b+w-2`; adjacent workers therefore share read-only
access to `w-1` boundary k-mers while never sharing a window. Each non-empty
worker initializes the leftmost minimum of its first window and advances within
its range using strict less-than comparison. One minimizer is counted per
window, with no adjacent-window deduplication.

Per-worker counters, current minimum state, and output slots are isolated.
After the OpenMP join, the main thread verifies that the processed-window sum
equals the global window count. It XOR-merges the historical per-window
coverage checksum and obtains the final-window checksum from the worker that
owns the last window. XOR merging is independent of worker completion order,
and the final checksum matches the Figure 2 definition.

The benchmark disables dynamic OpenMP teams and reports both requested and
observed thread counts. `OMP_NUM_THREADS`, `OMP_PROC_BIND`, `OMP_PLACES`, and
`OMP_SCHEDULE` are recorded. Partitioning is manual static contiguous rather
than an `omp for` schedule.

## Input and formal configuration

The gzip-transparent parser preserves the historical behavior: only the first
FASTA record is measured, and non-ACGT symbols are skipped without resetting
the rolling encoding. Dataset paths resolve in this order: explicit
`--datasets`, `KSSD_DATA_DIR`, then `reproducibility/data/external`.

The current Figure 3 configuration uses `k=21`, `w=10,20,50`, thread counts
`1,2,4,8,16`, three repeats, and the Synthetic 300M and Human GRCh38 datasets.
The repeat count of three was recovered from the historical runner and complete
raw grid. A later formal command is:

```sh
python3 reproducibility/figure3/run_figure3_multithread.py \
  --datasets /data/AEEE.fasta /data/GCF_000001405.40_GRCh38.p14_genomic.fna \
  --dataset-names Synthetic_300M Human_GRCh38 \
  --k 21 --w-values 10 20 50 --threads 1 2 4 8 16 --repeats 3 \
  --output-dir /results/figure3-multithread
```

This command is documentation only and is not run during Phase 4C.

## Functional smoke test

```sh
make figure3-build
make figure3-smoke
```

The smoke generates
`reproducibility/figure3/fixtures/figure3_smoke.fa` beneath a temporary output
root using `tests/fixture_generators/generate_test_fixtures.sh`; it then uses
`k=21`, `w=20`, thread
counts 1 and 2, one repeat, and five methods. It expects ten raw rows and ten
summary rows. For every method it requires identical parsed counts, minimizer
counts, final checksum, coverage checksum, tie mode, and deduplication mode at
one and two threads. Both two-thread intervals must be non-empty.

The runner also executes the migrated Figure 2 workflow on the same fixture at
`k=21`, `w=20`, one repeat, and seed 42. It compares all five one-thread counts
and final checksums. Runtime values are intentionally excluded from both
consistency tests.

## Outputs and plotting

Output defaults to a new temporary directory outside the repository. A selected
directory receives:

- `figure3_multithread_raw.csv`, one row per dataset/w/thread/repeat/method;
- `figure3_multithread_summary.csv`, one row per dataset/w/thread/method;
- `build_manifest.txt` and `run_manifest.txt`;
- `logs/` and `bin/`;
- `figure3_multithread_k21.png` and `.pdf`.

Raw fields include dataset provenance, k/w, repeat, requested/observed threads,
non-empty worker count, runtime, throughput, input/window/minimizer counts, both
checksums, parity samples, tie/deduplication modes, and log path. Summary fields
contain arithmetic mean and sample standard deviation for runtime and
throughput plus invariant counts.

The plot can be regenerated independently:

```sh
Rscript reproducibility/figure3/plot_figure3_multithread.R \
  --summary /results/figure3-multithread/figure3_multithread_summary.csv \
  --output-dir /results/figure3-multithread
```

Formal speedups depend on processor topology, affinity, OpenMP runtime,
compiler, memory behavior, system load, and background activity. Generated
measurements, plots, logs, and binaries are not committed.
