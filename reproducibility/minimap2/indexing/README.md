# Supplementary Figure S1 and Table S1 indexing workflow

This Phase 5B workflow compares Original Minimap2 and KSSD-Array during
single-thread index construction only. Phase 5C alignment consistency is a
separate workflow and is not invoked here.

The manuscript's accepted low-load measurements remain the reported
Supplementary Figure S1 and Table S1 values. Phase 7 runs only the fixture
preflight; it does not repeat the formal performance experiment or replace the
manuscript values. Deterministic minimizer fields have been verified against
the historical protocol. Because timing depends on host load, storage, memory
pressure, cache state, and hardware, no universal or hardware-independent
acceleration is claimed.

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

## Historical protocol

The timed command is:

```text
/usr/bin/time -v minimap2 -t 1 -d OUTPUT_INDEX REFERENCE
```

No explicit k, w, or HPC option is supplied, preserving Minimap2 defaults
`k=15`, `w=10`, and HPC disabled. Each dataset/method combination is repeated
three times with alternating method order and a 10-second cooldown after each
run. There is no warm-up and no explicit cache flush. Timing excludes builds,
input preparation, and output checksumming.

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

The output directory must not already exist. It contains one raw row per
dataset, method, and replicate; a six-row summary; machine-readable and
Markdown Table S1 files; build and run manifests; a system preflight; logs;
three retained indexes; and PNG/PDF Figure S1 files. Every replicate builds a
fresh index and records its size and checksum, then the next run for that
dataset overwrites the same dataset-specific index path. This limits retained
storage without reusing an existing index as a measurement. Raw fields include
timing, peak RSS, dataset identity, minimizer statistics, index size and
checksum, executable identity, command, and per-run system state. Summary
fields preserve full precision; the Markdown table uses manuscript-style
rounding.

Full inputs, binaries, indexes, raw measurements, and generated figures stay
outside Git. Runtime and RSS depend on host load, filesystem state, and cache
state and are compared by direction and reasonable magnitude rather than
exact equality with historical values.
