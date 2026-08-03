# Accepted manuscript benchmark results

This compact package contains only the exact accepted Table 4, Figure 2,
Figure 3, Supplementary S1, and Supplementary S2 result sets. Figure 4 and
bucket-balance material are intentionally outside the scope of this package.

| Manuscript item | Directory | Authoritative source |
|---|---|---|
| Table 4 | [`table4_matched_nthash/`](table4_matched_nthash/) | `final-validation-20260731-162115/01_table4_matched_full` |
| Figure 2 | [`figure2_single_thread/`](figure2_single_thread/) | `final-validation-20260731-162115/02_figure2_final` |
| Figure 3 | [`figure3_multithread/`](figure3_multithread/) | `final-validation-20260731-162115/03_figure3_final` |
| Supplementary S1 | [`supplementary_s1_minimap2_inline/`](supplementary_s1_minimap2_inline/) | `minimap2-indexing-s1-inline-final-20260731-214500` |
| Supplementary S2 | [`supplementary_s2_mapping/`](supplementary_s2_mapping/) | `minimap2-alignment-s2-20260728-v1` |

`artifact_manifest.tsv` binds every public file to its authoritative source
hash. Text files containing developer-local absolute paths were copied from
the exact source and then mechanically replaced with `$KSSD_RELEASE_HOST`;
the five locale-dependent environment/affinity snapshots were translated to
ASCII labels. Numerical fields are unchanged. The manifest records both the
original and public hashes and the transformation applied.

`source_binding.tsv` connects each result to its tracked implementation and
commit. Formal benchmarks were not rerun while assembling this package.
