# ART truth-schema audit

Status: **PASS — the genomic truth interval is reconstructed unambiguously.**

## Authoritative semantics

The retained ART `.aln` file is the authoritative per-read truth source. Its body has four fields: `ref_seq_id`, `read_id`, `aln_start_pos`, and `ref_seq_strand`, followed by the aligned reference and read strings. The bundled ART documentation states that `aln_start_pos` is relative to the reported reference strand. The bundled official `aln2bed.pl` converter establishes the coordinate basis and conversion: plus-strand BED start is `aln_start_pos`; minus-strand BED end is `reference_length - aln_start_pos`; the reference span is the ungapped aligned-reference length. Therefore `aln_start_pos` is a zero-based strand-relative offset.

Pinned semantics sources:

- ART README: `$KSSD_RELEASE_HOST/art_bin_MountRainier/art_illumina_README.txt` (SHA-256 `cf9cf1b44d0f83408af2b339b7a74c1a52581c0b5f999e2b7116e90869537ad0`).
- ART `aln2bed.pl`: `$KSSD_RELEASE_HOST/art_bin_MountRainier/aln2bed.pl` (SHA-256 `00b3af7203a615626c1eed7645b319c8825c1b92e52507434f4ce309bf24efe3`).

## Stored TSV schemas

- Human TSV: `query_name`, `reference_name`, `strand_relative_offset0` (three tab-separated columns).
- Zea mays TSV: `query_name`, `reference_name:strand_relative_offset0` (two tab-separated columns).
- Neither TSV stores strand or aligned-reference span. Every TSV tuple was checked against the corresponding `.aln` tuple.
- FASTQ identifiers and ordering were checked one-for-one against the reconstructed truth records.

## Genomic interval conversion

Let `p` be ART's zero-based strand-relative offset, `Lref` the reference length, and `span` the ungapped aligned-reference length:

- plus strand: zero-based half-open interval `[p, p + span)`; expected SAM POS is `p + 1`;
- minus strand: zero-based half-open interval `[Lref - p - span, Lref - p)`; expected SAM POS is `Lref - p - span + 1`.

Primary corrected correctness requires the truth reference, truth strand, and SAM POS within ±5 bp of the expected one-based position. The historical `p` or `p-(read_length-1)` rule is retained only to reproduce the old table; it is not the ART genomic conversion.

## Query-name normalization

Exact query names are used first. A terminal `/1` or `/2` is removed only when the trimmed name exists in truth. The formal data are single-end and use exact names.

## Full-condition checks

| Dataset | Read length | Truth | FASTQ | Plus | Minus | Reference span range | Truth references |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Human_GRCh38 | 100 | 523688 | 523688 | 261753 | 261935 | 99–102 | 620 |
| Human_GRCh38 | 150 | 522254 | 522254 | 260762 | 261492 | 148–151 | 621 |
| Zea_mays | 100 | 511569 | 511569 | 255685 | 255884 | 99–101 | 685 |
| Zea_mays | 150 | 512303 | 512303 | 256127 | 256176 | 149–151 | 685 |

## Twenty reviewed examples

Exactly five reads per condition (three plus-strand and two minus-strand) were checked against both BAMs. The complete fields and classifications are in `TRUTH_SCHEMA_MANUAL_CHECKS.tsv`. The sample includes all four dataset/read-length conditions and both strands.

The examples were also reviewed after generation; plus-strand expected SAM positions equal `p+1`, while minus-strand examples match the official reference-length conversion rather than the historical reverse-offset expression.
