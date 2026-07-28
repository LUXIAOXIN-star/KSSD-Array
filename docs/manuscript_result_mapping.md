# Manuscript result mapping

| Item | Workflow and API | Command | External inputs | Output | Current status and limitation |
|---|---|---|---|---|---|
| Table 2 | exhaustive validator; context and unchecked mapping APIs | `reproducibility/reproduce_manuscript.sh table2` | none | counts/optional CSV | fully reproduced exactly |
| Figure 2 | single-thread benchmark; fixed-k fast API | `reproducibility/reproduce_manuscript.sh figure2-smoke` | formal synthetic and GRCh38 FASTA for formal mode | raw/summary CSV and plot | smoke validated; manuscript formal values not rerun during Phase 7 |
| Table 4 | paired benchmark; fixed-k fast API | `reproducibility/reproduce_manuscript.sh table4-smoke` | ntHash; formal FASTA for formal mode | paired raw/summary table | smoke validated; manuscript formal values not rerun during Phase 7 |
| Figure 3 | OpenMP benchmark; shared read-only context and fast API | `reproducibility/reproduce_manuscript.sh figure3-smoke` | formal synthetic and GRCh38 FASTA for formal mode | raw/summary CSV and plot | smoke and thread consistency validated; manuscript formal values not rerun during Phase 7 |
| Figure 4 | deterministic bucket workflow; unchecked mapping API | `reproducibility/reproduce_manuscript.sh figure4-preflight` | none for formal synthetic generation | 27,000 raw and 270 summary rows, plots | formal rerun complete; summary and plotted data exact, raw last-bit differences only |
| Supplementary Figure S1/Table S1 | pinned Minimap2 patch; public context API | `reproducibility/reproduce_manuscript.sh minimap2-indexing-preflight` | pinned upstream source and three references for formal mode | timing/memory/index summaries and figure | `manuscript_low_load_results_retained`; `workflow_available`; `deterministic_statistics_verified`; `lightweight_preflight_validated`; `formal_performance_not_rerun_in_phase7` |
| Supplementary Table S2 | pinned integration and alignment evaluator | `reproducibility/reproduce_manuscript.sh minimap2-alignment-preflight` | matching original/integrated indexes, references, reads, truth and BED files | counts, metrics, displayed deltas | fully reproduced; 12 displayed deltas match after rounding |

Formal commands require explicit inputs and explicit output directories; see
`reproducibility/reproduce_manuscript.sh help`. Generated artifacts must remain outside the
repository.
