# Input provenance final report

Audit date: 2026-08-06; documentation conclusion updated 2026-08-07
(Asia/Shanghai)

Repository baseline: tag `v1.1.0-paper`, commit
`d24297bef54f06fb6366cca79cce6885e2e369f9`.

## Outcome

The deterministic Synthetic 300 Mb chain and the Supplementary S2
simulation/truth/alignment recipes are public and hash-bound. Zea mays repeat
provenance is complete. Human repeat provenance is transparent: the recovered
source and converted BED are hash-bound and the public conversion reproduces
the accepted identity, while the missing historical UCSC export command and
record ordering are stated explicitly.

No benchmark, ART simulation, Minimap2 alignment, or full 300 MB generation
was run during this task. No manuscript, accepted CSV, final figure, benchmark
result, or formal-result directory was modified.

## Synthetic 300 Mb status

Status: **complete publication generator**.

- fixed seed: `1781167332`;
- exact sequence length: 300,000,000 bases;
- portable explicit replay of the recovered glibc TYPE_3 stream;
- explicit nucleotide mapping: `0=A`, `1=T`, `2=C`, `3=G`;
- bounded-memory binary output with fixed newline/header bytes;
- existing-output refusal and formal size/hash enforcement;
- accepted identity: 300,000,057 bytes and SHA-256
  `a7eca29bdfa06ff373048fffa7a90139afc98acfa938a8ec0a98459608045962`;
- lightweight CI test covers the recovered 256-base prefix, deterministic
  formatting, and overwrite refusal.

Figure 2, Figure 3, and Table 4 documentation now points to this one shared
input generator and includes a pre-run SHA-256 check.

## Supplementary S2 status

Status: **complete reproducibility recipe; large artifacts remain external**.

- `simulate_reads.sh` pins ART_Illumina Q 2.5.8, its accepted executable hash,
  HS25, seed 42, both reference identities, all four exact commands, output
  FASTQ/ALN identities, and read counts.
- `generate_truth.sh` pins the official ART `aln2bed.pl`, treats retained ART
  ALN as authoritative, and recreates only the reduced historical TSV
  compatibility views.
- The README documents official strand-aware interval semantics and the
  corrected all-truth-read denominator.
- `generate_repeat_annotations.sh` applies and verifies both recovered exact
  repeat conversions.
- `run_alignment.sh` exposes the existing pinned `minimap2 -ax sr -t 1 |
  samtools sort` workflow while keeping BAMs external. It was not executed.

## Repeat annotation status

### Zea mays

Status: **complete**.

The exact B73 RefGen_v5 TE GFF3 source URL, compressed MD5, uncompressed
size/SHA-256, source header date, and GFF3-to-BED conversion are recorded. The
conversion reproduces the accepted BED identity
`e402860999e6de118f3deada95de01bc96e80ffc4f505b5962abfca687fab0e9`.

### Human

Status: **transparent and conversion-complete**.

The recovered six-column hg38 `rmsk`-derived BED and converted RefSeq-name BED
are pinned by size, row count, and SHA-256. Matching records were found in the
official UCSC hg38 `rmsk` table, but the original six-column export command and
record ordering were not recovered. The public documentation does not claim
otherwise. Starting from the checksum-verified recovered source, the provided
workflow reproduces the accepted RefSeq-name BED identity.

## Added files

- `MANUSCRIPT_INPUT_PROVENANCE_RECOMMENDATION.md`;
- `INPUT_PROVENANCE_FINAL_REPORT.md`;
- `reproducibility/data_generation/README.md`;
- `reproducibility/data_generation/synthetic_300M/README.md`;
- `reproducibility/data_generation/synthetic_300M/generate_synthetic_300M.py`;
- `reproducibility/data_generation/synthetic_300M/test_generate_synthetic_300M.py`;
- `reproducibility/data_generation/synthetic_300M/expected_sha256.tsv`;
- `reproducibility/data_generation/supplementary_s2/README.md`;
- `reproducibility/data_generation/supplementary_s2/simulate_reads.sh`;
- `reproducibility/data_generation/supplementary_s2/generate_truth.sh`;
- `reproducibility/data_generation/supplementary_s2/run_alignment.sh`;
- `reproducibility/data_generation/supplementary_s2/generate_repeat_annotations.sh`;
- `reproducibility/data_generation/supplementary_s2/expected_sha256.tsv`;
- `reproducibility/data_generation/repeat_annotations/README.md`.

## Modified files

- `.github/workflows/ci.yml`;
- `Makefile`;
- `README.md` (this task added only the short input-provenance sentence; other
  uncommitted README edits existed before this task and were preserved);
- `docs/datasets.md`;
- `reproducibility/README.md`;
- `reproducibility/data/datasets.json`;
- `reproducibility/figure2/README.md`;
- `reproducibility/figure3/README.md`;
- `reproducibility/table4/README.md`.

## Validation

Passed:

- four new shell scripts: `bash -n` and `--help` entry points;
- Synthetic generator unit tests: 3/3;
- JSON parsing and both TSV column-schema checks;
- documentation links: 142 local links;
- core library tests and runtime-inline/fast-path parity;
- exhaustive Table 2 9-mer validation;
- fixture-generator tests: 5/5;
- public-tree, secret-pattern, large-file, and documentation scans.

`make check` reached `check-public-history` and stopped because the existing
Git history contains one developer absolute-path string in
`FINAL_RESTYLE_UPDATE_REPORT.md` from commit `bf1af64`. The current input-
provenance files contain no such path. The failure predates this task and
cannot be corrected without a separate approved history-rewrite/release-policy
decision. Checks scheduled after that target were run separately and passed.

## Release and manuscript decision

The manuscript Data Availability statement **should be updated** using
`MANUSCRIPT_INPUT_PROVENANCE_RECOMMENDATION.md`. Its wording now matches the
repository: generated inputs are reproducible and large external inputs are
identified by accessions, commands, conversions, sizes, and checksums. No
separate data deposit is required for this documentation conclusion.

No tag, commit, or push was performed here. These documentation changes do not
require a benchmark rerun or a manuscript numerical revision. If an immutable
release is intended to include changes committed after `v1.1.0-paper`, use a
new provenance-only patch tag after normal release review rather than moving
the existing tag.
