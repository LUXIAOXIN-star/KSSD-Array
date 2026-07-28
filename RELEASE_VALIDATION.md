# Release-candidate validation

## Scope

This report covers the public core library, lightweight manuscript workflows,
installation interfaces, repository policy checks, and the clean public Git
history. The final tracked tree contains 101 files. Formal datasets and
generated outputs are not distributed.

## Validated status

- Core Make build: PASS; the default target builds only the static library.
- Default CMake build: PASS; reproducibility targets are disabled by default.
- Runnable minimal API example: PASS; DNA validation, encoding, mapping, and
  output-domain reporting were exercised.
- Core tests: PASS through Make and CTest; all ten CTest cases passed.
- Table 2 exhaustive 9-mer validation: fully reproduced exactly.
- Figure 2, Table 4, and Figure 3: workflows migrated and smoke-tested; formal
  performance was not rerun in Phase 7B.
- Figure 4: formally reproduced in the accepted validation; summary and plotted
  data matched exactly, while raw floating values differed only in numerical
  last bits.
- Minimap2 integration: PASS for original/integrated builds, static public
  library linkage, index and alignment thread consistency, ambiguous-base
  handling, HPC smoke, and index compatibility.
- Supplementary Figure S1 and Table S1: accepted low-load manuscript values
  retained; workflow and deterministic statistics validated; no Phase 7B
  formal performance rerun.
- Supplementary Table S2: formally reproduced; all twelve manuscript-displayed
  deltas matched after rounding.
- Pinned ntHash dependency preparation and Table 4 smoke: PASS.
- Installation: PASS for headers, static archive, CMake package files, and
  pkg-config metadata.
- External consumers: PASS through `find_package`, pkg-config, and direct
  static linking.
- Full-history policy scan: PASS; no legacy names, developer paths, internal
  audit paths, secret patterns, prohibited CJK, external symbolic links, or
  blobs larger than 10 MiB were found.
- GitHub readiness: PASS after replacing the release placeholders listed
  below; no remote, push, or release tag was created during validation.

## Known limitations

The package version and publication metadata remain placeholders. Performance
depends on compiler, hardware, storage, data, and host load. The historical
300-million-base synthetic input has a known identity but no recovered exact
generator. Formal reference genomes, reads, generated indexes, alignments,
large result tables, and manuscript figures are intentionally excluded.

Before publication, replace `<OWNER>` in the clone URL, assign the final
version, complete publication metadata in `CITATION.cff`, configure the GitHub
remote, create the release tag, and publish the release notes.
