# Historical single-thread score-plus-window results

This package preserves the original score-plus-window implementation and its accepted measurements. It is not the current manuscript Figure2, which uses the separate five-method preencoded score-only data.

Read [FIGURE2_FINAL_REPORT.md](FIGURE2_FINAL_REPORT.md), figure2_summary.csv and figure2_raw.csv for the original timing and repetitions. Figure2_final.png retains the historical plot. The documented rescan, per-window counting and no-adjacent-dedup semantics remain unchanged.

KSSD's historical30/30 ranking concerns this implementation only; do not transfer it to independent scoring. The newer score-only comparison retains k31 conditions favoring XXH3. See [the current result index](../README.md) for the current figure and its raw bindings.

The original reproducibility source and commands remain under [the historical workflow](../../reproducibility/figure2/README.md). Build, input, command and environment manifests in this package describe the actual historical run, not a new measurement.
