# KSSD-Array

KSSD-Array is a C11 library for deterministic segmented permutation-array
mapping of 2-bit encoded DNA k-mers.

## Overview

KSSD-Array supports `1 <= k <= 32` and maps the complete `4^k` encoded k-mer domain
bijectively to itself for a fixed initialized context. It provides
deterministic integer mapping for k-mer and minimizer workflows through a
small public C API, runtime-inline mapping, and fixed-k mapping interfaces.

## Quick navigation

| Goal | Start here |
|---|---|
| Build and use KSSD-Array | [Quick start](#quick-start) |
| Use the library in C | [`examples/minimal_api.c`](examples/minimal_api.c) |
| View the public API | [`docs/api.md`](docs/api.md) |
| Understand the algorithm | [`docs/algorithm.md`](docs/algorithm.md) |
| View manuscript results | [`benchmark_results/README.md`](benchmark_results/README.md) |
| Reproduce manuscript experiments | [`reproducibility/README.md`](reproducibility/README.md) |
| Understand datasets | [`docs/datasets.md`](docs/datasets.md) |
| Repository organization | [`docs/repository_map.md`](docs/repository_map.md) |
| Validation evidence | [`docs/validation/README.md`](docs/validation/README.md) |

Ordinary library users normally need only this README, `include/`, `examples/`,
and [`docs/api.md`](docs/api.md). Paper readers should start from
[`benchmark_results/`](benchmark_results/), while researchers reproducing the
experiments should use [`reproducibility/`](reproducibility/). Release auditors
can inspect [`docs/validation/`](docs/validation/) and
[`docs/provenance/`](docs/provenance/).

## Installation

The core library requires a C11 compiler and either Make or CMake. Ordinary
library builds do not require the optional manuscript benchmark dependencies.
Use the local build below to get started, or use the CMake installation section
to install the library and package metadata under a selected prefix.

## Quick start

From the release directory, run:

```sh
make

make examples
./build/examples/minimal_api

make test
```

`make` builds only `build/libkssd_array.a`. The runnable example validates a
DNA string, encodes A/C/G/T with two bits per base, initializes a deterministic
context, maps the k-mer, and prints the output domain.

## Use the static library from C

Include `kssd_array.h`, encode each base as `A=0`, `C=1`, `G=2`, `T=3`, and
reject or reset at ambiguous bases before calling the library. Compile a
program against the local static archive with:

```sh
cc -std=c11 -Iinclude your_program.c \
  build/libkssd_array.a \
  -o your_program
```

The canonical complete example is
[`examples/minimal_api.c`](examples/minimal_api.c). A distinct rolling
minimizer example using the fixed-k fast interface is in
[`examples/build_minimizers.c`](examples/build_minimizers.c).

## CMake build and installation

A normal CMake build compiles only the static library:

```sh
cmake -S . -B build-cmake
cmake --build build-cmake
```

Tests and examples are independent opt-in components:

```sh
cmake -S . -B build-test -DKSSD_ARRAY_BUILD_TESTS=ON \
  -DKSSD_ARRAY_BUILD_EXAMPLES=ON
cmake --build build-test
ctest --test-dir build-test --output-on-failure
```

With CMake/CTest 3.16, run `ctest --output-on-failure` from inside
`build-test/`; newer CTest versions support the `--test-dir` form above.

Install to a selected prefix:

```sh
cmake -S . -B build-install
cmake --build build-install
cmake --install build-install --prefix /desired/prefix
```

An installed CMake consumer can use:

```cmake
find_package(KSSDArray CONFIG REQUIRED)
add_executable(example your_program.c)
target_link_libraries(example PRIVATE KSSDArray::kssd_array)
```

Configure that consumer with the installation prefix:

```sh
cmake -S . -B build -DCMAKE_PREFIX_PATH=/desired/prefix
cmake --build build
```

### Build options

All optional CMake components are disabled by default:

| Option | Default | Purpose |
|---|---:|---|
| `KSSD_ARRAY_BUILD_SHARED` | `OFF` | Also build a shared library |
| `KSSD_ARRAY_BUILD_TESTS` | `OFF` | Build and register core tests |
| `KSSD_ARRAY_BUILD_EXAMPLES` | `OFF` | Build runnable examples |
| `KSSD_ARRAY_BUILD_REPRODUCIBILITY` | `OFF` | Build manuscript workflow targets |

### pkg-config

The CMake and Make installation paths both install `kssd-array.pc`. For a
non-system prefix:

```sh
export PKG_CONFIG_PATH=/desired/prefix/lib/pkgconfig
cc -std=c11 your_program.c $(pkg-config --cflags --libs kssd-array) \
  -o your_program
```

## API overview

KSSD-Array provides three interfaces for different caller needs. All use the
same initialized permutation tables and deterministic mapping semantics.

### Context API

The context API in [`include/kssd_array.h`](include/kssd_array.h) validates
initialization, `k`, and encoded input range. `kssd_array_map_unchecked()`
removes per-call checks after the caller has established those preconditions.

### Runtime-inline API

The runtime-inline header
[`include/kssd_array_inline.h`](include/kssd_array_inline.h) supports callers
whose `k` is selected at runtime. Initialize one
`kssd_array_inline_plan_t` from an initialized context, then call the public
always-inline `kssd_array_inline_map_unchecked()` in the hot loop. The plan
borrows direct table pointers from the context, so the context must outlive the
plan and must not be destroyed while mapping is active.

### Fixed-k API

The fixed-k header [`include/kssd_array_fast.h`](include/kssd_array_fast.h)
requires `KSSD_ARRAY_FIXED_K` at compile time. It uses the same tables owned by
the context and does not implement a second permutation generator. See
[`docs/api.md`](docs/api.md) for the complete contract.

## Thread safety

After successful initialization and safe publication, multiple threads may
map concurrently through the same `const kssd_array_t`. Mapping is read-only.
Initialization and destruction must never overlap a mapping call, and the
owning context must not be copied by value.

## Algorithm and design

The mapping is constructed from deterministic segmented permutation arrays.
For a fixed initialized context, it is a bijection over the complete encoded
input domain. The design and permutation construction are described in
[`docs/algorithm.md`](docs/algorithm.md); dependency details are in
[`docs/dependencies.md`](docs/dependencies.md), and input/dataset policy is in
[`docs/datasets.md`](docs/datasets.md).

### Limitations

KSSD-Array accepts encoded integers rather than DNA text and cannot detect an
ambiguous base after encoding. It is not a cryptographic primitive. Ordering
depends on `k`, seed, and RNG mode. Performance depends on workload, compiler,
hardware, storage, and host state; no universal acceleration is claimed.

## Performance summary

The independent preencoded scoring comparison (Figure 2a) has the highest
mean KSSD-Array throughput in 8 of 10 dataset-by-k conditions; XXH3 is faster
at k=31 on both inputs. Figure 2b additionally measures per-window minimum
selection, while Figure 3 compares runtime and sampling density. Figure 4,
the ntHash comparison, and Minimap2 indexing use separate experimental
protocols. Results and their limitations are described in
[`benchmark_results/README.md`](benchmark_results/README.md).

## Paper reproducibility

Ordinary library users do not need these workflows. Paper readers should use
the figures, tables, and data in [`benchmark_results/`](benchmark_results/),
while researchers can start from [`reproducibility/README.md`](reproducibility/README.md).
Input preparation and exact identities are described in [`docs/datasets.md`](docs/datasets.md).

Main manuscript:

- [Figure 1: algorithm example](benchmark_results/figure1_algorithm/README.md)
- [Figure 2a: independent scoring](benchmark_results/figure2a_independent_scoring/README.md)
- [Figure 2b: scoring and per-window selection](benchmark_results/figure2b_window_selection/README.md)
- [Figure 3: runtime and sampling density](benchmark_results/figure3_runtime_density/README.md)
- [Figure 4: bucket balance](benchmark_results/figure4_bucket_balance/README.md)
- [Table 1: segmentation](benchmark_results/table1_segmentation/README.md)
- [Table 2: ntHash](benchmark_results/table2_nthash/README.md)
- [Table 3: Minimap2 indexing](benchmark_results/table3_minimap2_indexing/README.md)

Supporting Information:

- [S1: multithreading](benchmark_results/supplementary_s1_multithreading/README.md)
- [S1.1: XOR and odd multiplication](benchmark_results/supplementary_s1_1_xor_odd/README.md)
- [S1.2: gxhash64](benchmark_results/supplementary_s1_2_gxhash/README.md)
- [S2: ntHash and LTO](benchmark_results/supplementary_s2_nthash/README.md)
- [S3.1: runtime and density](benchmark_results/supplementary_s3_1_runtime_density/README.md)
- [S3.2: streaming](benchmark_results/supplementary_s3_2_streaming/README.md)
- [S3.3: external SIMD A/B/C](benchmark_results/supplementary_s3_3_external_simd/README.md)
- [S3.4: repetitive-word selection](benchmark_results/supplementary_s3_4_repetitive_words/README.md)
- [S3.5: Alu controlled reads](benchmark_results/supplementary_s3_5_alu/README.md)
- [S4: Minimap2](benchmark_results/supplementary_s4_minimap2/README.md)

Each experiment's README describes its inputs, timing boundary, dependencies,
results and validation status. The experiments use different protocols and
are not interchangeable; saved data or small-input checks are not a complete
performance replay. The rolling minimizer example uses an unambiguous A/C/G/T
string and is not a general sequence-file parser.

All six small FASTA/FASTQ/BED smoke inputs are generated from the public C
source under `tests/fixture_generators/` into temporary directories and checked
against fixed SHA-256 values; generated sequence/BED files are not committed.
Run `make fixture-generator-test` to validate clean and repeated generation plus
the documented failure cases.
The simulated-read truth-origin workflow includes provenance packaging; its
README describes the required input files and Python/SciPy environment.

Commands, scope, status, and environment metadata are documented in
[`reproducibility/README.md`](reproducibility/README.md) and
[`reproducibility/ENVIRONMENT.md`](reproducibility/ENVIRONMENT.md). These
workflows are opt-in and are never built by an ordinary Make or CMake library
build. Compact results are available under `benchmark_results/`; SHA-256
inventories and build/run manifests record their identities. Large datasets,
reads, alignments, per-read diagnostics, indexes, and dependency caches are
external. Their identities and acquisition requirements are documented with
each workflow.

## Release, citation, and license

### Release

Software version: `1.1.0` (public runtime-inline API).

Associated manuscript: KSSD-Array.

This repository corresponds to the implementation and reproducibility
workflows used for the manuscript. Workflow and result mappings are listed in
[`docs/manuscript_result_mapping.md`](docs/manuscript_result_mapping.md).

### Citation and license

Citation metadata are in [`CITATION.cff`](CITATION.cff). KSSD-Array is licensed
under [`LICENSE`](LICENSE); third-party notices are in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
