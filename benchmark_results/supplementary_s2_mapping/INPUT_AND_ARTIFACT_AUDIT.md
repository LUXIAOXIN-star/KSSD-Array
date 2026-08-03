# Input and artifact audit

Status: **PASS**. All required accepted artifacts are present and hash verified; all 16 accepted BAM files pass `samtools quickcheck`.

- Accepted historical directory: `$KSSD_RELEASE_HOST/KSSD-Array-formal-results/minimap2-alignment-s2-20260728-v1`.
- Non-BAM pinned inputs verified: 18.
- BAMs verified: 16 (8 global and 8 historical reported-repeat subsets).
- BAM index files: none were present or required; evaluation streams coordinate-sorted BAM records with `samtools view`.
- Historical raw/summary tables, build manifest, run manifest, configuration, method definition, and output hash inventory are present.
- Existing BAMs are reused. No Minimap2 alignment or index construction is run by this workflow.

The complete absolute paths, sizes, and SHA-256 values are in `input_sha256.tsv` and `bam_sha256.tsv`.
