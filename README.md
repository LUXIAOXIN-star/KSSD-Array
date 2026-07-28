# KSSD-Array

KSSD-Array is a C11 library for deterministic segmented permutation-array
mapping of 2-bit encoded DNA k-mers. It supports `1 <= k <= 32` and maps the
complete `2k`-bit input domain bijectively to itself for a fixed initialized
context.

## Five-minute workflow

```sh
git clone https://github.com/<OWNER>/KSSD-Array.git
cd KSSD-Array

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

## pkg-config

The CMake and Make installation paths both install `kssd-array.pc`. For a
non-system prefix:

```sh
export PKG_CONFIG_PATH=/desired/prefix/lib/pkgconfig
cc -std=c11 your_program.c $(pkg-config --cflags --libs kssd-array) \
  -o your_program
```

## Context API and fast API

The context API in [`include/kssd_array.h`](include/kssd_array.h) validates
initialization, `k`, and encoded input range. `kssd_array_map_unchecked()`
removes per-call checks after the caller has established those preconditions.

The fixed-k header [`include/kssd_array_fast.h`](include/kssd_array_fast.h)
requires `KSSD_ARRAY_FIXED_K` at compile time. It uses the same tables owned by
the context and does not implement a second permutation generator. See
[`docs/api.md`](docs/api.md) for the complete contract.

## Thread safety

After successful initialization and safe publication, multiple threads may
map concurrently through the same `const kssd_array_t`. Mapping is read-only.
Initialization and destruction must never overlap a mapping call, and the
owning context must not be copied by value.

## Build options

All optional CMake components are disabled by default:

| Option | Default | Purpose |
|---|---:|---|
| `KSSD_ARRAY_BUILD_SHARED` | `OFF` | Also build a shared library |
| `KSSD_ARRAY_BUILD_TESTS` | `OFF` | Build and register core tests |
| `KSSD_ARRAY_BUILD_EXAMPLES` | `OFF` | Build runnable examples |
| `KSSD_ARRAY_BUILD_REPRODUCIBILITY` | `OFF` | Build manuscript workflow targets |

The package version remains the development placeholder `0.0.0-dev` until the
release metadata is finalized.

## Limitations

KSSD-Array accepts encoded integers rather than DNA text and cannot detect an
ambiguous base after encoding. It is not a cryptographic primitive. Ordering
depends on `k`, seed, and RNG mode. Performance depends on workload, compiler,
hardware, storage, and host state; no universal acceleration is claimed.

The construction is described in [`docs/algorithm.md`](docs/algorithm.md),
dependencies in [`docs/dependencies.md`](docs/dependencies.md), and dataset
policy in [`docs/datasets.md`](docs/datasets.md).

## Paper reproducibility

Complete workflows for the manuscript tables, figures, ntHash comparison, and
Minimap2 supplement are documented in
[`reproducibility/README.md`](reproducibility/README.md). They are opt-in and
are never built by an ordinary Make or CMake library build.

## Citation and license

Citation metadata are in [`CITATION.cff`](CITATION.cff). KSSD-Array is licensed
under [`LICENSE`](LICENSE); third-party notices are in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
