# Release-candidate validation

## Scope

This report records the historical `v1.0.0-paper` validation baseline. The
current public-review state is assessed separately in
`FINAL_PUBLIC_REPOSITORY_VALIDATION.md`. Compact accepted results are now
published under `benchmark_results/`; large inputs and diagnostics remain
external.

## Release identity

- Repository: https://github.com/LUXIAOXIN-star/KSSD-Array
- Software version: `1.0.0`
- Release name/tag: `v1.0.0-paper`
- Release date: 2026-07-28

## Validated status

- Core Make build: PASS; the default target builds only the static library.
- Default CMake build: PASS; reproducibility targets are disabled by default.
- Runnable minimal API example: PASS; DNA validation, encoding, mapping, and
  output-domain reporting were exercised.
- Core tests: PASS through Make and CTest; all ten CTest cases passed.
- Table 2 exhaustive 9-mer validation: fully reproduced exactly.
- Figure 2, Table 4, and Figure 3: workflows migrated and smoke-tested; formal
  performance was not rerun for this release candidate.
- Figure 4: formally reproduced in the accepted validation; summary and plotted
  data matched exactly, while raw floating values differed only in numerical
  last bits.
- Minimap2 integration: PASS for original/integrated builds, static public
  library linkage, index and alignment thread consistency, ambiguous-base
  handling, HPC smoke, and index compatibility.
- Supplementary Figure S1 and Table S1: accepted low-load manuscript values
  retained; workflow and deterministic statistics validated; no new formal
  performance run was required for this release candidate.
- Supplementary Table S2 at this release point used the historical evaluator.
  Its 12 displayed deltas remain a compatibility check, but the table is
  superseded by the corrected all-read truth-origin evaluation.
- Pinned ntHash dependency preparation and Table 4 smoke: PASS.
- Installation: PASS for headers, static archive, CMake package files, and
  pkg-config metadata.
- External consumers: PASS through `find_package`, pkg-config, and direct
  static linking.
- Full-history policy scan: PASS; no legacy names, developer paths, internal
  audit paths, secret patterns, prohibited CJK, external symbolic links, or
  blobs larger than 10 MiB were found.
- Release-candidate metadata: PASS for version, date, repository URL, citation,
  and changelog consistency.
- CI status: the release candidate passed local validation. GitHub Actions must
  pass on the release commit before the final release tag is created.

## Known limitations

Performance depends on compiler, hardware, storage, data, and host load. The
historical 300-million-base synthetic input has a known identity but no
recovered exact generator. Formal reference genomes, reads, generated indexes,
alignments, large result tables, and per-read diagnostics are intentionally
excluded.

The final release tag is created only after GitHub Actions passes on the
release commit.
