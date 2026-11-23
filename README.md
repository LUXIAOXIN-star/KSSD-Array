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
| --- | --- |
| Build the library and run the C example | [Installation and quick start](#installation) |
| Find data for a figure or table | [Index by manuscript figure and table number](docs/manuscript_result_mapping.md) |
| Reproduce a published result | [Experiment workflows and requirements](reproducibility/README.md) |

## Installation

The core library requires a C11-compatible compiler and either Make or CMake.
Ordinary library builds do not require the optional benchmark dependencies.
Clone the repository and enter its directory:

```sh
git clone https://github.com/LUXIAOXIN-star/KSSD-Array.git
cd KSSD-Array
```

Use the local Make build below to get started. To install the library and its
package metadata under a selected prefix, use the CMake installation section.

## Quick start

From the repository directory, build the static library, build and run the
example, and run the unit tests:

```sh
make

make examples
./build/examples/minimal_api

make test
```

`make` builds only `build/libkssd_array.a`; it does not install the library.
The runnable example validates a
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

Install to a selected prefix (replace `$HOME/.local` with your chosen path):

```sh
KSSD_PREFIX="$HOME/.local"
cmake -S . -B build-install -DCMAKE_INSTALL_PREFIX="$KSSD_PREFIX"
cmake --build build-install
cmake --install build-install
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

The [figure and table index](docs/manuscript_result_mapping.md) links each
manuscript item to its saved results and available workflow. Each workflow
lists its inputs, software and supported steps. For example, Figure 3 can be
redrawn from the saved measurements. Rerunning its historical timing
experiment requires additional inputs and software.

## Release, citation, and license

### Release

Software version: `1.1.0` (public runtime-inline API).

Associated manuscript: KSSD-Array.

### Citation and license

Citation metadata are in [`CITATION.cff`](CITATION.cff). KSSD-Array is licensed
under [`LICENSE`](LICENSE); third-party notices are in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
