# Final provenance documentation audit

Audit date: 2026-08-07 (Asia/Shanghai)

Baseline: commit `d24297bef54f06fb6366cca79cce6885e2e369f9`, tag
`v1.1.0-paper`.

## Conclusion

**Documentation complete.**

- Synthetic 300 Mb input provenance: **COMPLETE**.
- Supplementary S2 generation workflow: **COMPLETE**.
- Human repeat annotation provenance: **TRANSPARENT**.
- Zea mays repeat annotation provenance: **COMPLETE**.
- Separate large-file deposit: **NOT REQUIRED for this documentation state**.
- Benchmark, ART, Minimap2, and full-input reruns: **NOT PERFORMED OR REQUIRED**.
- Manuscript numerical changes: **NOT REQUIRED**.

No benchmark result, figure, formal-result directory, manuscript file, Git
history, tag, or remote repository was modified.

## Synthetic 300 Mb status

The public generator creates one FASTA record containing exactly 300,000,000
bases with fixed seed `1781167332`. It explicitly implements the recovered
historical random stream and nucleotide mapping, streams bounded output, and
verifies the accepted 300,000,057-byte SHA-256 identity
`a7eca29bdfa06ff373048fffa7a90139afc98acfa938a8ec0a98459608045962`.
The generated FASTA remains outside Git. Figure 2, Figure 3, and Table 4
documentation all point to the shared workflow.

## Supplementary S2 status

The workflow documents ART_Illumina Q 2.5.8, HS25, seed 42, both reference
identities, four exact simulation commands, FASTQ/ALN identities, authoritative
strand-aware ART ALN truth, the all-truth-read denominator, repeat conversion,
and the existing optional alignment-regeneration entry point. Large FASTA,
FASTQ, ALN, BED, BAM, index, and diagnostic files remain external and
checksum-bound.

## Human repeat provenance status

The recovered source is identified as a six-column BED derived from the UCSC
hg38 `rmsk` table. Its row count, size, and SHA-256 are recorded. The conversion
to the 25 GRCh38.p14 RefSeq chromosome accessions is public and reproduces the
accepted converted BED size, row count, and SHA-256.

The exact historical UCSC export command and record ordering were not
preserved. This limitation is stated explicitly and is not replaced by a claim
of exact upstream byte reconstruction. It does not prevent reproduction of the
accepted conversion when starting from the checksum-verified recovered source.

## Documentation changed in this cleanup

- `reproducibility/data_generation/repeat_annotations/README.md`;
- `reproducibility/data_generation/README.md`;
- `reproducibility/data_generation/supplementary_s2/README.md`;
- `reproducibility/data_generation/supplementary_s2/expected_sha256.tsv`;
- `docs/datasets.md`;
- `reproducibility/README.md`;
- `MANUSCRIPT_INPUT_PROVENANCE_RECOMMENDATION.md`;
- `INPUT_PROVENANCE_FINAL_REPORT.md`.

`README.md` already contained the requested one-sentence link to
`reproducibility/data_generation/`, so no additional root-README expansion was
needed during this cleanup.

## Added file

- `FINAL_PROVENANCE_DOCUMENTATION_AUDIT.md`.

## Validation

All requested non-benchmark checks passed:

- Markdown/local-link validation: **PASS**, 142 links;
- JSON syntax validation: **PASS**, 10 files;
- provenance TSV schema validation: **PASS**, 2 files;
- public-tree scan: **PASS**;
- secret-pattern scan: **PASS**;
- large-file scan: **PASS**;
- existing `make check-docs`: **PASS**, 142 links;
- `git diff --check`: **PASS**.

No formal benchmark, ART simulation, Minimap2 command, or full Synthetic 300 Mb
generation was run.

## Data Availability and release

The recommended Data Availability wording is now consistent with the
documented input model: public source/workflows/results/metadata, deterministic
Synthetic input reconstruction, and accession/command/conversion/checksum
records for large external inputs. No separate data deposit is required by the
provenance documentation.

No new tag is required because of a scientific or numerical change. However,
the current provenance edits are uncommitted changes on top of the immutable
`v1.1.0-paper` commit. If the Data Availability statement is intended to bind
these exact new files to a release tag, a new provenance-only patch tag is
recommended after normal commit and release review; the existing tag should not
be moved. No commit, tag, or push was performed in this task.

## Remaining issues

There is no remaining input-provenance documentation blocker. The missing
historical Human UCSC export command/order remains a disclosed limitation, not
an unsupported claim. The only operational release decision is whether to bind
the post-tag documentation changes with a later patch tag.
