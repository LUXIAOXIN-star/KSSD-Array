# Public-library integration for minimap2 2.30

This directory contains a reviewable patch and deterministic verification
tools for minimap2 `2.30-r1287`, upstream commit
`79c9cc186b95f50bd899f69b48eba995ced810c6`. The repository does not
redistribute the upstream source tree.

## Integration design

The patch replaces minimap2's post-canonicalization integer mixer with the
public KSSD-Array runtime-inline API. It includes `kssd_array.h` and
`kssd_array_inline.h`, compiles
only a small ownership adapter, and links the existing public archive with:

```text
-I${KSSD_ARRAY_ROOT}/include
-L${KSSD_ARRAY_ROOT}/build -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic
```

It never compiles KSSD-Array core source files into minimap2. The cold public
calls are `kssd_array_init_with_rng`, `kssd_array_inline_plan_init`,
`kssd_array_destroy`, and `kssd_array_status_string`; the canonical-k-mer hot
loop uses the public always-inline `kssd_array_inline_map_unchecked`. The final
executable has no hot-loop call to the generic mapper. Initialization uses seed
42 and the explicitly versioned GLIBC-compatible stream used by the historical
server integration.

Every `mm_idx_t` owns one context and one borrowed inline plan. `mm_idx_init()` creates them before indexing
workers start, `mm_sketch()` receives a const adapter pointer, and parallel
workers perform read-only mapping only. `mm_idx_destroy()` releases the
context after indexing or mapping workers have joined. Split-index merge owns
a separate context with the same lifetime. Independent index operations never
share mutable KSSD state, and there is no worker-side lazy initialization.

Canonical forward/reverse selection, strand recording, symmetric-k-mer
filtering, ambiguous-base reset, and homopolymer-compression span accounting
remain in the original control flow. Only the mapped value is replaced.

## Index compatibility

KSSD-Array minimizers change serialized index semantics. Integrated indexes
therefore use the versioned four-byte magic `KSA\x01`, while standard indexes
use a different magic. The integrated executable:

- loads `KSA\x01` indexes produced by the same integration;
- rejects standard indexes with a rebuild instruction;
- rejects unknown `KSA` versions with the observed version byte and a rebuild
  instruction.

Unmodified minimap2 does not recognize `KSA\x01` as an index. Its generic
input parser may nevertheless treat an unknown binary file as sequence input
and exit successfully with no alignments. The verifier records this upstream
limitation. Users must not pass integrated indexes to an unmodified binary;
the supported workflow always pairs the integrated executable with its
versioned index.

## Obtain, apply, and build

All paths are caller-selected. A local checkout avoids network access:

```sh
reproducibility/minimap2/fetch_minimap2.sh \
  /path/to/clean/minimap2-v2.30 \
  /external/work/minimap2-source

reproducibility/minimap2/patch/apply_patch.sh --check \
  /external/work/minimap2-source
reproducibility/minimap2/patch/apply_patch.sh --apply \
  /external/work/minimap2-source

make -C /path/to/KSSD-Array build/libkssd_array.a
make -C /external/work/minimap2-source -j4 \
  KSSD_ARRAY_ROOT=/path/to/KSSD-Array
```

The combined build helper creates a fresh pinned checkout and refuses an
existing build directory:

```sh
reproducibility/minimap2/build_minimap2.sh integrated \
  /path/to/clean/minimap2-v2.30 \
  /external/work/integrated-build \
  /path/to/KSSD-Array
```

Passing a URL to the fetch/build helpers is an explicit request to use the
network. Ordinary repository builds, tests, and CTest never fetch minimap2.

## Deterministic fixtures and smoke validation

`fixtures/reference.fa` and `fixtures/query.fa` are small synthetic inputs.
They contain ambiguous-base regions and homopolymer-rich regions. The C probe
checks that two eight-base runs separated by an ambiguous base produce no
9-mer minimizers, while the same bases joined without the boundary do produce
minimizers.

Run build-only verification or the complete Phase 5A smoke suite with new
external output directories:

```sh
make minimap2-verify-build \
  MINIMAP2_SOURCE_DIR=/path/to/clean/minimap2-v2.30 \
  MINIMAP2_VERIFY_DIR=/external/work/build-verification

make minimap2-smoke \
  MINIMAP2_SOURCE_DIR=/path/to/clean/minimap2-v2.30 \
  MINIMAP2_SMOKE_DIR=/external/work/smoke
```

The smoke suite builds original and integrated executables, checks static
public-library symbols, creates byte-identical one-thread/four-thread indexes,
compares all four index/alignment thread combinations, tests ambiguous reset,
runs one-thread/four-thread HPC alignment, and verifies index rejection in
both supported incompatibility cases.

Optional CMake custom targets are enabled only when both
`KSSD_ARRAY_MINIMAP2_SOURCE_DIR` and `KSSD_ARRAY_MINIMAP2_WORK_ROOT` are set.
They are not registered as CTest tests and never run as part of a normal
configure, build, or test invocation.

The patch modifies upstream `Makefile`, `index.c`, `map.c`, `minimap.h`,
`mmpriv.h`, `sketch.c`, and `splitidx.c`, and adds
`kssd_array_minimap2.c/.h`. Its SHA-256 is
`84ef84315357c7754180ff2c2b4a006877146dfa22986131aebcb842529e49e2`.

The integration smoke test makes no performance claim. The single-thread
indexing workflow is documented in
[`indexing`](indexing). The manuscript's accepted
low-load Supplementary Figure S1 and Table S1 values remain authoritative;
Phase 7 validates only the lightweight preflight. Timing is environment-
sensitive, and the repository makes no universal or hardware-independent
indexing-acceleration claim. Alignment consistency is documented in
[`alignment_consistency`](alignment_consistency) and
reproduces Supplementary Table S2 from exact historical reads. It is never
run by the indexing targets or ordinary builds/tests.
