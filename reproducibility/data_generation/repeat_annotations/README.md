# Repeat annotation provenance

This record binds the two repeat sources and exact conversions used by the
corrected Supplementary Table S2 truth-origin analysis. Large source and BED
files remain outside Git.

## Human GRCh38

The exact recovered source is a six-column, UCSC-name BED export:

| Field | Value |
|---|---|
| Filename | `hg38_repeats.bed` |
| Size | 211,063,376 bytes |
| Rows | 5,683,690 |
| SHA-256 | `fe9dd792d266a2ae2868da4993b6706ef257a7f8e41ae5f85731efcfbbf473dc` |
| Content origin | UCSC `hg38.rmsk`/RepeatMasker-derived records |
| Upstream comparison table | [UCSC hg38 `rmsk.txt.gz`](https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/rmsk.txt.gz) |

An audit on 2026-08-06 matched records against the UCSC hg38 `rmsk` table.
The recovered Human repeat source was derived from that table, but the original
six-column export command and record ordering were not preserved. The recovered
source BED is nevertheless fixed by its row count, byte size, and SHA-256; the
accepted RefSeq-converted BED is independently fixed by the same identity
records.

The conversion retains only `chr1`-`chr22`, `chrX`, `chrY`, and `chrM`, maps
them to the 25 corresponding GRCh38.p14 RefSeq accessions, and preserves the
remaining five BED columns. Alternate, unlocalized, and fix-patch records are
excluded. Output:

| Filename | Size | Rows | SHA-256 |
|---|---:|---:|---|
| `hg38_repeats_refseq.bed` | 233,983,952 bytes | 5,317,291 | `74a5a4b8887b7ad061ad81feca8546df8a3668651d0c0e7e187e9b08f403d1a2` |

Input and output are already BED coordinates: 0-based, half-open.
Starting from the checksum-verified recovered source, the provided conversion
workflow reproduces the accepted converted BED identity. This provenance claim
does not assert knowledge of the missing historical UCSC export command or
ordering.

## Zea mays B73 RefGen_v5

The exact source is the B73 RefGen_v5 transposable-element annotation from the
MaizeGDB `Zm-B73-REFERENCE-NAM-5.0` release directory:

| Field | Value |
|---|---|
| Release directory | [MaizeGDB B73 RefGen_v5](https://download.maizegdb.org/Zm-B73-REFERENCE-NAM-5.0/) |
| Compressed file | [Zm-B73-REFERENCE-NAM-5.0.TE.gff3.gz](https://download.maizegdb.org/Zm-B73-REFERENCE-NAM-5.0/Zm-B73-REFERENCE-NAM-5.0.TE.gff3.gz) |
| Source header date | 2020-08-24 |
| Compressed MD5 | `7898ef5fc280bf2e3f35d5a2d97a3ee` |
| Uncompressed filename | `Zm-B73-REFERENCE-NAM-5.0.TE.gff3` |
| Uncompressed size | 342,920,266 bytes |
| Uncompressed SHA-256 | `025c61d382dfc0355a09badd98c7197ad7a15eaf4c271cdea6ad3b53eccbbdc6` |
| Verified | 2026-08-06 |

The compressed MD5 matches the checksum published in the MaizeGDB release
directory. The exact conversion is:

```sh
LC_ALL=C awk 'BEGIN {OFS="\t"} !/^#/ {print $1, $4 - 1, $5, $3}' \
  Zm-B73-REFERENCE-NAM-5.0.TE.gff3 > maize_repeats_raw.bed
```

GFF3 coordinates are 1-based inclusive. Subtracting one from the start while
retaining the end produces BED 0-based half-open intervals. Output:

| Filename | Size | SHA-256 |
|---|---:|---|
| `maize_repeats_raw.bed` | 79,599,886 bytes | `e402860999e6de118f3deada95de01bc96e80ffc4f505b5962abfca687fab0e9` |

Use
[`../supplementary_s2/generate_repeat_annotations.sh`](../supplementary_s2/generate_repeat_annotations.sh)
to apply both exact conversions and validate all four identities.
