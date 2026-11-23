# Figure 3: runtime and sampling density

The figure shows the 10-Mb forward-only materialized-score experiment with a
common leftmost window selector. The two inputs and k = 21/31 were tested at
w = 20 with KSSD-Array, seq-hash and GreedyMini-derived prefix12. Every point
uses all five independent-process timings; horizontal error bars show sample
standard deviations. Density is selected positions divided by valid k-mer
starts. The GreedyMini-derived method is not an unmodified native run.

`figure3_data.csv` contains the displayed values. The path-tokenized raw and path-redacted summary tables in this directory retain the measurements. The [reproduction workflow](../../reproducibility/figure3_runtime_density/README.md) documents the saved-data redraw command, source availability and the limits on a complete benchmark rebuild. Redrawing does not rerun performance measurements.

The current [sha256.tsv](sha256.tsv) verifies the distributed data and listed results. `SHA256SUMS.txt` is a historical checksum archive; some files it names are not included in the current repository.

`Figure3_manuscript.png` is the embedded figure from the final manuscript. `figure3_raw_path_tokenized.tsv` retains the 60 recorded process rows with machine path prefixes replaced; `figure3_summary_path_redacted.tsv` removes path-only columns. These are explicitly derived copies; their numeric values are unchanged.

`figure3_warmup_path_tokenized.tsv` retains all 12 warmup records separately from the 60 measured processes. It is a derived copy with historical machine path prefixes replaced by tokens; warmups are not included in the formal summary.
