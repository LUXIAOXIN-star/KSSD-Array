# Changelog

## 1.1.0 — 2026-07-31

- Added the runtime-selected `kssd_array_inline_plan_t` and always-inline
  mapper for `k=1..32`, retaining the existing context and fixed-k APIs.
- Added parity, boundary and small-domain validation for the mapping interfaces.
- Provided an adapter for integrating the runtime-inline mapper with Minimap2.

## 1.0.0-paper — 2026-07-28

- Added the C11 rank-derived permutation-array library, checked context API,
  and compile-time fixed-k fast path.
- Added a 9-mer implementation check and core test coverage.
- Added installation metadata, examples and experiment workflows.
