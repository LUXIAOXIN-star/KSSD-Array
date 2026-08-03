# Accepted manuscript benchmark results

This directory stores the accepted paper results and the evidence needed to
verify them. The experiment-running code is primarily under
[`reproducibility/`](../reproducibility/); ordinary readers can use the three
recommended files for each result below without opening every manifest or hash
inventory. Those detailed records are retained for reproducibility and
integrity review. Formal benchmarks were not rerun while assembling this
compact package.

## Result navigation

Each row identifies exactly three recommended entry files: an explanatory
README or final report, the manuscript-facing visual/table, and compact data.

| Paper item | Result directory | Three recommended entry files | Reproduction workflow |
| --- | --- | --- | --- |
| Figure 2 | [`figure2_single_thread/`](figure2_single_thread/) | [`README.md`](figure2_single_thread/README.md)<br>[`Figure2_final.png`](figure2_single_thread/Figure2_final.png)<br>[`figure2_summary.csv`](figure2_single_thread/figure2_summary.csv) | [`figure2/README.md`](../reproducibility/figure2/README.md) |
| Figure 3 | [`figure3_multithread/`](figure3_multithread/) | [`README.md`](figure3_multithread/README.md)<br>[`Figure3_final.png`](figure3_multithread/Figure3_final.png)<br>[`figure3_summary.csv`](figure3_multithread/figure3_summary.csv) | [`figure3/README.md`](../reproducibility/figure3/README.md) |
| Main-text Figure 4 bucket balance | [`figure4_bucket_balance/`](figure4_bucket_balance/) | [`README.md`](figure4_bucket_balance/README.md)<br>[`figure4_bucket_balance.png`](figure4_bucket_balance/figure4_bucket_balance.png)<br>[`figure4_bucket_balance_summary.csv`](figure4_bucket_balance/figure4_bucket_balance_summary.csv) | [`figure4/README.md`](../reproducibility/figure4/README.md) |
| Matched-workload ntHash detail | [`table4_matched_nthash/`](table4_matched_nthash/) | [`TABLE4_MATCHED_FULL_REPORT.md`](table4_matched_nthash/TABLE4_MATCHED_FULL_REPORT.md)<br>[`Table4_matched_speedup_vs_k.png`](table4_matched_nthash/Table4_matched_speedup_vs_k.png)<br>[`matched_table4_summary.csv`](table4_matched_nthash/matched_table4_summary.csv) | [`table4_matched_workload/README.md`](../reproducibility/table4_matched_workload/README.md) |
| Supplementary Figure S1 and Table S1 | [`supplementary_s1_minimap2_inline/`](supplementary_s1_minimap2_inline/) | [`S1_INLINE_FINAL_REPORT.md`](supplementary_s1_minimap2_inline/S1_INLINE_FINAL_REPORT.md)<br>[`supplementary_figure_s1_final.png`](supplementary_s1_minimap2_inline/supplementary_figure_s1_final.png)<br>[`supplementary_table_s1_final.csv`](supplementary_s1_minimap2_inline/supplementary_table_s1_final.csv) | [`minimap2/indexing/README.md`](../reproducibility/minimap2/indexing/README.md) |
| Corrected Supplementary Table S2 | [`supplementary_s2_mapping/`](supplementary_s2_mapping/) | [`S2_CORRECTED_FINAL_REPORT.md`](supplementary_s2_mapping/S2_CORRECTED_FINAL_REPORT.md)<br>[`supplementary_table_s2_corrected.csv`](supplementary_s2_mapping/supplementary_table_s2_corrected.csv)<br>[`supplementary_s2_corrected_paired.csv`](supplementary_s2_mapping/supplementary_s2_corrected_paired.csv) | [`alignment_consistency_truth_origin/README.md`](../reproducibility/minimap2/alignment_consistency_truth_origin/README.md) |

## File types inside each result package

| File type | Purpose |
| --- | --- |
| `README.md` / final report | Recommended starting point |
| PNG/PDF | Paper figure |
| Manuscript-ready table CSV | Values intended for the manuscript |
| Summary CSV | Compact accepted results |
| Raw CSV | Accepted individual measurements |
| Plotting script | Regenerates the visual from accepted data |
| `commands.sh` | Executed commands |
| Build/run manifests | Build and protocol identity |
| `environment.txt` | Software and hardware environment |
| SHA-256 manifests | Integrity verification |

These evidence files have different audiences; readers do not need to open
every manifest to understand the result.

## Accepted result sources

| Manuscript item | Directory | Authoritative source |
|---|---|---|
| Matched-workload ntHash (detailed Supplementary result) | [`table4_matched_nthash/`](table4_matched_nthash/) | `final-validation-20260731-162115/01_table4_matched_full` |
| Figure 2 | [`figure2_single_thread/`](figure2_single_thread/) | `final-validation-20260731-162115/02_figure2_final` |
| Figure 3 | [`figure3_multithread/`](figure3_multithread/) | `final-validation-20260731-162115/03_figure3_final` |
| Main-text Figure 4 | [`figure4_bucket_balance/`](figure4_bucket_balance/) | `figure4-20260727-phase4d` |
| Supplementary S1 | [`supplementary_s1_minimap2_inline/`](supplementary_s1_minimap2_inline/) | `minimap2-indexing-s1-inline-final-20260731-214500` |
| Corrected Supplementary S2 | [`supplementary_s2_mapping/`](supplementary_s2_mapping/) | `minimap2-alignment-s2-corrected-20260804-145013` |

The bucket-balance package is **main-text Figure 4**, not a Supplementary
result. For the matched-workload ntHash comparison, the detailed tables and
plots in `table4_matched_nthash/` are intended for Supplementary material;
the main text should retain only a concise summary of that comparison.
KSSD-Array is fastest in all 30/30 accepted Figure 2 groups and all 30/30
accepted Figure 3 groups. Supplementary S1 is the public runtime-inline
integration result. Corrected S2 uses every truth read and one fixed
truth-origin repeat subset; it supersedes the historical mapped-primary,
method-specific-repeat evaluation.
Its refreshed source inventory binds the deterministic fixture generator and
the corrected packaging workflow; the accepted numerical tables were not
changed.

`artifact_manifest.tsv` binds every public file to its authoritative source
hash. Text files containing developer-local absolute paths were copied from
the exact source and then mechanically replaced with `$KSSD_RELEASE_HOST`;
the five locale-dependent environment/affinity snapshots were translated to
ASCII labels. Numerical fields are unchanged. The manifest records both the
original and public hashes and the transformation applied.

`source_binding.tsv` connects each result to its tracked implementation and
provenance.
