# Manuscript result mapping

| Item | Workflow and API | Command | External inputs | Output | Current status and limitation |
|---|---|---|---|---|---|
| Table 2 | exhaustive validator; context and unchecked mapping APIs | `reproducibility/reproduce_manuscript.sh table2` | none | counts/optional CSV | fully reproduced exactly |
| Figure 2 | single-thread benchmark; fixed-k fast API | `reproducibility/reproduce_manuscript.sh figure2-smoke` | formal synthetic and GRCh38 FASTA for formal mode | raw/summary CSV and plot | accepted result: KSSD fastest in 30/30 groups; smoke workflow validated |
| Matched-workload ntHash | paired benchmark; identical workload boundaries | `reproducibility/table4_matched_workload/run_matched_workload.py --smoke` | ntHash; formal FASTA for formal mode | paired raw/summary table and plot | detailed result intended for Supplementary material; concise main-text summary |
| Figure 3 | OpenMP benchmark; shared read-only context and fast API | `reproducibility/reproduce_manuscript.sh figure3-smoke` | formal synthetic and GRCh38 FASTA for formal mode | raw/summary CSV and plot | accepted result: KSSD fastest in 30/30 groups; smoke and thread consistency validated |
| Figure 4 | deterministic bucket workflow; unchecked mapping API | `reproducibility/reproduce_manuscript.sh figure4-preflight` | none for formal synthetic generation | 27,000 raw and 270 summary rows, plots | formal rerun complete; summary and plotted data exact, raw last-bit differences only |
| Supplementary Figure S1/Table S1 | pinned Minimap2 patch; public runtime-inline API | `reproducibility/reproduce_manuscript.sh minimap2-indexing-formal` | pinned upstream source and three references | raw/summary/pairwise timing, memory/index table and figure | inline/output/assembly validation passed; controlled three-dataset five-pair run completed externally |
| Corrected Supplementary Table S2 | accepted BAM reuse; all-read ART strand-aware evaluator | `python3 -m unittest discover -s reproducibility/minimap2/alignment_consistency_truth_origin/tests -v` | accepted BAMs, references, reads, ART ALN truth and repeat BED | corrected counts, paired metrics, validation tables | active corrected result: 7/7 fixtures, 12/12 historical compatibility deltas, and 62/62 corrected checks pass; historical S2 is superseded |

Formal commands require explicit inputs and explicit output directories; see
`reproducibility/reproduce_manuscript.sh help`. Generated artifacts must remain outside the
repository.
