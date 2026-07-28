# API reference

## Headers

Include `kssd_array.h` for all context, initialization, inspection, and runtime
mapping functions. Include `kssd_array_fast.h` only after defining
`KSSD_ARRAY_FIXED_K` to an integer in the range 1 through 32.

## Context ownership

`kssd_array_t` owns all allocations reachable through its table pointers.
Start with `KSSD_ARRAY_CONTEXT_INIT` or equivalent zero initialization. A
successful initialization must eventually be paired with
`kssd_array_destroy`.

The context is non-copyable: do not copy it by value. Its fields are public so
it can be stack-allocated and so the inline fast path can access tables, but
callers must not mutate those fields. Inspection functions return borrowed,
read-only pointers that become invalid when the context is destroyed.

`kssd_array_destroy` accepts a null pointer or a zero-initialized context. To
change `k`, seed, or RNG mode, destroy the current context and initialize it
again.

## Initialization

```c
kssd_array_status_t kssd_array_init(kssd_array_t *context,
                                    size_t k,
                                    uint64_t seed);
```

Initializes a context with the default SplitMix64 stream.

```c
kssd_array_status_t kssd_array_init_with_rng(kssd_array_t *context,
                                             size_t k,
                                             uint64_t seed,
                                             kssd_array_rng_t rng);
```

Selects either `KSSD_ARRAY_RNG_SPLITMIX64` or
`KSSD_ARRAY_RNG_GLIBC_COMPAT`. The glibc-compatible mode accepts a seed no
larger than `UINT32_MAX`.

Both functions accept `k` from 1 through 32. On allocation failure, all partial
allocations are released and the context returns to its zero state.

## Mapping

```c
kssd_array_status_t kssd_array_map(const kssd_array_t *context,
                                   uint64_t encoded_kmer,
                                   uint64_t *result);
```

Checks pointers, initialization state, and input width. `result` is written
only on success.

```c
uint64_t kssd_array_map_unchecked(const kssd_array_t *context,
                                  uint64_t encoded_kmer);
```

Skips all checks. Use it only when the context and input were already
validated.

```c
uint64_t kssd_array_fast_with_tables(uint64_t encoded_kmer,
                                     const kssd_array_t *context);
```

This inline function specializes segmentation for `KSSD_ARRAY_FIXED_K` and
uses the context's existing tables. It performs no allocation, table creation,
or error checking. Its preconditions are:

1. `context` was initialized successfully.
2. `context` was initialized for exactly `KSSD_ARRAY_FIXED_K`.
3. The encoded input is within the low `2k` bits when `k < 32`.
4. The context remains alive and unchanged for the duration of the call.

## Layout and inspection

`kssd_array_layout` computes the balanced nucleotide segmentation without
allocating. `kssd_array_master_permutation` and `kssd_array_permutation` return
borrowed pointers and optionally report table sizes. They return null when the
request is invalid or the context is not initialized.

## Error handling

Public operations return `kssd_array_status_t`. The possible values describe
invalid arguments, unsupported `k`, allocation failure, uninitialized use,
out-of-range input, and double initialization. `kssd_array_status_string`
returns a stable English description for logging; applications should branch
on the enum value, not the text.

## Output domain and ambiguous bases

For a context initialized with `k`, every successful mapping is in
`[0, 4^k)`. The fixed mapping is bijective over all encoded `k`-mers. The
library accepts integers and cannot distinguish an ambiguous nucleotide after
encoding; text parsers must reject the affected k-mer or reset their rolling
value and valid-base count at every non-ACGT symbol.

## Thread safety

After safe publication, any number of threads may call mapping and inspection
functions concurrently through the same `const kssd_array_t`. These operations
are read-only. Initialization and destruction are exclusive operations and
must not overlap mapping, inspection, or one another. Different contexts are
independent because the implementation has no mutable global state.

## Limitations

The mapper is deterministic rather than cryptographic. Mapping order changes
with `k`, seed, or RNG mode. The API does not parse DNA text, select canonical
strand orientation, roll between adjacent k-mers, or implement the minimizer
window rule; those responsibilities remain with the caller. The fixed-k fast
path is unchecked and misuse is undefined at the API-contract level.
