# Multithreaded score-plus-window results

Supplementary Figure S1 uses the original measurements in figure3_raw.csv (750 rows) and figure3_summary.csv (150 groups): two inputs, k21, w10/20/50, five methods, threads1/2/4/8/16 and five repeats per condition.

The final manuscript image is [Supplementary Figure S1](../supplementary_s1_multithreading/FigureS1_manuscript.png). The retained [log2 throughput plotting script](../../reproducibility/figure3/plot_figure3_loglog_throughput.R) uses absolute million-windows/s throughput and mean±sample SD in the original units; its previously rendered PNG and PDF are not included in this package.

The original score-plus-window program starts from preencoded k-mers. It is not current Figure2's score-only loop, a common-selector DNA pipeline or complete Minimap2 indexing. Archived GCC9.4/-O3/-march=native/C11/OpenMP and method-library identities belong to these measurements; do not substitute later inline xxHash/gxhash build settings.

The earlier Figure3_final files are historical views of the same source data, not additional experiments. References to “Figure 3” in FIGURE3_FINAL_REPORT.md use the earlier manuscript numbering and refer to this multithread experiment, now Supplementary Figure S1; they do not describe the current main Figure 3. The historical report, commands, and source/build/input manifests retain the original provenance. The [workflow](../../reproducibility/figure3/README.md) supplies functional checks and explicit full-run requirements.
