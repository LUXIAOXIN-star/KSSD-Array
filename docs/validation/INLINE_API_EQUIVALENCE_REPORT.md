# Runtime inline API equivalence report

Date: 2026-07-31 (Asia/Shanghai)

## Scope

The new public runtime plan and mapper are implemented in
`include/kssd_array_inline.h`; cold plan initialization is implemented in
`src/kssd_array.c`.  The plan borrows the current context's `uint16_t`
permutation tables and precomputes segment count, input shifts and masks,
output shifts, and direct table pointers.  It does not introduce historical
global ownership or historical initialization/cleanup code.

The computation was derived from the segment extraction, lookup, and
recombination in the separately inspected historical Minimap2 KSSD checkout's
`sketch.c` lines 51--102.  Unlike that historical function, segmentation and
table selection come from the current `kssd_array_t` layout and ownership
model.

## Validation

Commands completed successfully:

```text
make -j4 test
make -j4 sanitize
```

`tests/test_inline_parity.c` compared
`kssd_array_inline_map_unchecked()` with
`kssd_array_map_unchecked()` for both supported RNG modes and every `k` from
1 through 32.  Coverage included:

- zero, the maximum valid value, maximum minus one, and half maximum;
- the existing fixed values `0`, `1`, `0x0123456789abcdef`,
  `0xfedcba9876543210`, `0xaaaaaaaaaaaaaaaa`, and
  `0x5555555555555555`, masked to the valid domain;
- low/high boundaries for every segment;
- exhaustive enumeration for `k=1..9` (699,048 values across both RNG modes);
- 100,000 deterministic pseudorandom valid inputs per `k` and RNG mode
  (6,400,000 random comparisons total);
- the transition values `k=7,8,9`, `15,16,17`, `23,24,25`, and `31,32` as
  part of the complete range.

All comparisons passed.  The ASan/UBSan build executed the same coverage with
no sanitizer diagnostic, including `k=32` and full-width `uint64_t` inputs.
Existing core tests, fixed-k parity tests, and the exhaustive Table 2 validator
also passed.

## Result

**PASS — inline and generic results were identical for every tested input.**
