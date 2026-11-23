# Historical Figure 3, now Supplementary Figure S1

[Supplementary Figure S1](../supplementary_s1_multithreading/FigureS1_manuscript.png) shows multithreaded scoring and window selection. “Figure 3” in this directory and its [historical report](FIGURE3_FINAL_REPORT.md) refers to an earlier manuscript number. For runtime and sampling density, see [Figure 3 in the final manuscript](../figure3_runtime_density/README.md).

The [raw measurements](figure3_raw.csv) contain 750 rows, and the [summary](figure3_summary.csv) contains 150 groups. The experiment used two inputs, `k = 21`, window sizes of 10, 20 and 50, five methods, and 1, 2, 4, 8 and 16 threads. Each condition was measured five times.

The program starts from preencoded k-mers and measures both scoring and window selection. The original measurements used GCC 9.4 with `-O3 -march=native`, C11 and OpenMP. The build and input manifests and saved commands document the method libraries and settings used.

The `Figure3_final` images are earlier plots of the same measurements. The [log-scale throughput script](../../reproducibility/figure3/plot_figure3_loglog_throughput.R) plots the mean and sample standard deviation in millions of windows per second. Its earlier PNG and PDF outputs are not distributed here. The [workflow](../../reproducibility/figure3/README.md) describes the functional checks and full-run requirements.
