# Algorithm

## Input domain

A k-mer is represented by an unsigned integer containing exactly `2k`
significant bits, with two bits per nucleotide. For `k < 32`, bits above the
low `2k` positions must be zero. For `k = 32`, the complete `uint64_t` domain
is valid.

The transformation is a permutation of this domain. It changes order while
preserving width and injectivity.

## Balanced segmentation

Let the per-segment nucleotide cap be `C = 8`. The number of segments is

```text
n = ceil(k / C).
```

Let `q = floor(k / n)` and `r = k mod n`. Segment `i`, numbered from zero, has
length

```text
s_i = q + 1  when i < r,
s_i = q      otherwise.
```

Therefore every length is at most eight, all segment lengths differ by at most
one, and their sum is exactly `k`. The master length is `L = s_0`, the longest
segment length.

## Master and rank-derived permutations

Initialization constructs one permutation `R_L` over the integer domain
`[0, 4^L)`. Fisher-Yates shuffling uses the selected deterministic RNG stream
and seed.

For every shorter segment length `s`, no independent shuffle is performed.
Instead, each `s`-nucleotide value `x` is zero-padded to the master width:

```text
z_s(x) = x << (2 * (L - s)).
```

The derived permutation is the rank of the selected master value among all
selected values:

```text
P_s(x) = rank of R_L(z_s(x)) in
         { R_L(z_s(y)) : 0 <= y < 4^s }.
```

Ranks are unique because `R_L` is a permutation. Consequently every `P_s` is
also a permutation of `[0, 4^s)`. For `s = L`, `P_L` is the master permutation
itself.

This rank construction is the defining relationship of the implementation.
Only `src/permutation.c` generates the master table and derives shorter tables.

## Mapping

The input k-mer is split from most significant segment to least significant
segment using the balanced lengths. Each segment `x_i` is replaced by
`P_{s_i}(x_i)`. The mapped segments are concatenated at their original widths:

```text
F(x) = P_{s_0}(x_0) || P_{s_1}(x_1) || ... || P_{s_{n-1}}(x_{n-1}).
```

Because each component is a width-preserving permutation and the segmentation
is fixed for a given `k`, `F` is a permutation of the full `2k`-bit domain.

## Determinism

The default RNG mode is SplitMix64. The library owns its RNG state locally;
initialization neither reads nor modifies process-global random state. A
glibc-compatible mode reproduces the legacy `rand()` sequence locally without
calling `srand()` or `rand()`.

No external random-array file is needed. The seed and RNG mode completely
determine the master table and every derived table.
