# Corrected S2 source binding

- Public workflow: `reproducibility/minimap2/alignment_consistency_truth_origin`
- Source identity: the 17 content hashes in `source_sha256.tsv`, including the
  public C fixture generator, wrapper, and expected-hash manifest
- Accepted BAM source: `$KSSD_RELEASE_HOST/KSSD-Array-formal-results/minimap2-alignment-s2-20260728-v1`
- Accepted corrected result source: `$KSSD_RELEASE_HOST/KSSD-Array-formal-results/minimap2-alignment-s2-corrected-20260804-145013`
- Alignments reused: **YES**
- Alignments rerun: **NO**
- Primary truth semantics: retained ART `.aln` plus bundled official
  `aln2bed.pl` conversion
- Historical parser compatibility: **12/12 displayed deltas reproduced**
- Corrected validation: **62/62 checks passed**
- Clean packaging replay: **PASS; no manual provenance copy required**
- Numerical replay: **five manuscript-facing/analysis CSVs byte-identical to
  the accepted result**
