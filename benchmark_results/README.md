# Accepted manuscript benchmark results

This compact package contains the accepted Figure 2, Figure 3, main-text
Figure 4, matched-workload ntHash, Supplementary S1, and Supplementary S2
result sets. Formal benchmarks were not rerun while assembling the package.

| Manuscript item | Directory | Authoritative source |
|---|---|---|
| Matched-workload ntHash (detailed Supplementary result) | [`table4_matched_nthash/`](table4_matched_nthash/) | `final-validation-20260731-162115/01_table4_matched_full` |
| Figure 2 | [`figure2_single_thread/`](figure2_single_thread/) | `final-validation-20260731-162115/02_figure2_final` |
| Figure 3 | [`figure3_multithread/`](figure3_multithread/) | `final-validation-20260731-162115/03_figure3_final` |
| Main-text Figure 4 | [`figure4_bucket_balance/`](figure4_bucket_balance/) | `figure4-20260727-phase4d` |
| Supplementary S1 | [`supplementary_s1_minimap2_inline/`](supplementary_s1_minimap2_inline/) | `minimap2-indexing-s1-inline-final-20260731-214500` |
| Supplementary S2 | [`supplementary_s2_mapping/`](supplementary_s2_mapping/) | `minimap2-alignment-s2-20260728-v1` |

The bucket-balance package is **main-text Figure 4**, not a Supplementary
result. For the matched-workload ntHash comparison, the detailed tables and
plots in `table4_matched_nthash/` are intended for Supplementary material;
the main text should retain only a concise summary of that comparison.

`artifact_manifest.tsv` binds every public file to its authoritative source
hash. Text files containing developer-local absolute paths were copied from
the exact source and then mechanically replaced with `$KSSD_RELEASE_HOST`;
the five locale-dependent environment/affinity snapshots were translated to
ASCII labels. Numerical fields are unchanged. The manifest records both the
original and public hashes and the transformation applied.

`source_binding.tsv` connects each result to its tracked implementation and
provenance.
