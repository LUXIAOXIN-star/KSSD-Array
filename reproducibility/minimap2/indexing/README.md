# Supplementary Figure S1 and Table S1 indexing workflow

This workflow compares Original Minimap2 and the public runtime-inline
KSSD-Array integration during single-thread index construction only. Alignment consistency is a
separate workflow and is not invoked here.

The public-inline implementation has a complete controlled rerun workflow.
Deterministic minimizer fields are validated for every run. Because timing depends on host
load, storage, memory pressure, cache state, and hardware, no universal or
hardware-independent acceleration is claimed.

Both executables are built from Minimap2 `2.30-r1287`, commit
`79c9cc186b95f50bd899f69b48eba995ced810c6`. The integrated copy applies the
public-library patch at `reproducibility/minimap2/patch/minimap2-v2.30-kssd-array.patch`
and statically links the current `build/libkssd_array.a`.

## Datasets and preparation

The pinned configuration requires TAIR10.1 as the original gzip FASTA,
GRCh38.p14 as decompressed FASTA, and B73 RefGen_v5 as uncompressed FASTA.
Exact names, sizes, checksums, sequence counts, and total bases are in
`reproducibility/minimap2/indexing/config.json`. The runner resolves repeated
`--dataset KEY=PATH` overrides first, then `KSSD_DATA_DIR`, then
`reproducibility/data/external`. It refuses a mismatched identity and never downloads or
decompresses an input.

## Public-inline final protocol

The timed command is:

```text
/usr/bin/time -v taskset -c 15 minimap2 -t 1 -k 15 -w 10 \
  -d UNIQUE_OUTPUT_INDEX REFERENCE
```

The options explicitly preserve `k=15`, `w=10`, and HPC disabled. Each method
receives one untimed warm-up per dataset. Five measured pairs follow
sequentially, with Original first on odd repeats and public-inline KSSD first
on even repeats, plus a 10-second cooldown after each measured run. There is
no explicit cache flush, so this is a controlled warm-cache protocol. Timing
excludes builds, input preparation, and output checksumming.

The full and per-dataset preflights capture load, memory, disk, topology,
governor, processes, affinity, and ten seconds of `vmstat`. Each run also has a
lightweight gate. A measured run with swap traffic is preserved in
`INVALID_MEASURED_ATTEMPTS.tsv`, excluded from the formal raw table, and
retried under a new stem after a fixed wait. The decision never uses observed
performance.

Run a small functional preflight with a new external directory:

```sh
make minimap2-indexing-preflight \
  MINIMAP2_SOURCE_DIR=/path/to/clean/minimap2-v2.30 \
  MINIMAP2_INDEXING_PREFLIGHT_DIR=/external/work/indexing-preflight
```

Run the formal experiment only with an explicit configuration, source, and
external output directory. `KSSD_DATA_DIR` may point to the root containing
the configured relative dataset paths:

```sh
KSSD_DATA_DIR=/path/to/data-root make minimap2-indexing-formal \
  MINIMAP2_SOURCE_DIR=/path/to/clean/minimap2-v2.30 \
  DATA_CONFIG=reproducibility/minimap2/indexing/config.json \
  OUTPUT_DIR=/external/results/minimap2-indexing-s1
```

The output directory must not already exist for the first invocation. A
controlled `--resume` verifies the existing executables and raw accepted rows,
uses new retry stems, and never overwrites prior run logs. The completed package
contains 30 raw rows, a six-row summary, 15 paired ratios, the final Table S1
and Figure S1 files, build/run/environment/command manifests, three identity
hash tables, and all run/preflight logs. Every run builds a uniquely named
temporary index, records its size, checksum, magic, and deterministic fields,
then deletes only that completed temporary index. Raw fields include
timing, peak RSS, dataset identity, minimizer statistics, index size and
checksum, executable identity, command, and per-run system state. Summary
fields preserve full precision; the Markdown table uses manuscript-style
rounding.

Full inputs, binaries, indexes, raw measurements, and generated figures stay
outside Git. Runtime and RSS depend on host load, filesystem state, and cache
state and are compared by direction and reasonable magnitude rather than
exact equality with historical values. The accepted public-inline rerun on the
development host is recorded outside Git; generated data remain external.
