# Simulated-read truth-origin accuracy

This directory retains the corrected simulated-read accuracy analysis, called
Supplementary Table S2 in the historical release. In the current manuscript,
the Minimap2 results appear in Supplementary Section S4 and Table S11; current
Table S2 concerns gxhash. The corrected analysis supersedes the earlier
historical accuracy evaluation. It keeps
every simulated truth read in the global denominator, counts unmapped or
missing-primary reads as incorrect, reconstructs truth intervals with ART's
strand-aware coordinate conversion, and uses one fixed truth-origin repeat
subset for both methods.

The accepted Original Minimap2 and KSSD-Array BAM files were reused; Minimap2
was not rerun for the historical corrected analysis or this release. The full
historical inputs and result directory are external; a public archive of the
exact BAM and read files has not been verified. The accepted `output_sha256.tsv`
has SHA-256
`b4ff21d69901630e837268f4d9a592ed39e304c69324ff579fa1fee2c9029d06`.
The public workflow is
[`reproducibility/minimap2/alignment_consistency_truth_origin`](../../reproducibility/minimap2/alignment_consistency_truth_origin/README.md);
the historical `source_sha256.tsv` records 17 workflow and fixture-generator
source identities. A historical packaging check reproduced five numerical CSV
tables, 12 historical deltas, and 62 corrected validation checks. The full
dataset has not been rerun for this release; some packaging text and paths have
been adapted, so current files should be checked against the release inventory.

## Public tables and reports

- `supplementary_s2_corrected_counts.csv`: method-level count closure.
- `supplementary_s2_corrected_metrics.csv`: corrected all-read and fixed
  repeat-origin metrics.
- `supplementary_s2_corrected_paired.csv`: paired differences, bootstrap
  intervals, and exact McNemar results.
- `supplementary_table_s2_corrected.csv`: manuscript-facing corrected table.
- `supplementary_table_s2_mapq_corrected.csv`: corrected MAPQ table.
- `S2_CORRECTED_FINAL_REPORT.md`: accepted interpretation.
- `S2_CORRECTED_VALIDATION_REPORT.md` and
  `S2_CORRECTED_VALIDATION.tsv`: 62/62 validation checks.
- `HISTORICAL_METRIC_REPRODUCTION_REPORT.md` and
  `HISTORICAL_METRIC_REPRODUCTION.tsv`: 12/12 historical displayed deltas
  reproduced before correction.
- `TRUTH_SCHEMA_AUDIT.md` and `TRUTH_ORIGIN_REPEAT_AUDIT.md`: truth and
  repeat-subset evidence.

The corrected all-read accuracy differences remain within ±0.05 percentage
points and their paired 95% bootstrap intervals include zero. The historical
repeat-region wording is not retained: Human 100 bp has a small
Original-favoring difference on the corrected fixed truth-origin subset.

## Data policy

BAM/BAI, references, FASTQ, reduced truth TSV, ART ALN truth, repeat BED, and
the two full per-read diagnostic tables are not bundled. The historical
manifest records sizes and hashes; it does not establish that the exact files
are publicly downloadable. `output_sha256.tsv` covers the compact files
at the time of the historical release. The current README is adapted, so its
historical hash is not its current hash; use the release file inventory for
current identities. Historical definitions and checksums are retained
under
[`docs/provenance/supplementary_s2_historical`](../../docs/provenance/supplementary_s2_historical/README.md);
the obsolete table is not presented as an active result.
