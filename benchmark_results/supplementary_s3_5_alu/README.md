# Supplementary section S3.5 and Table S9

Controlled seed-supported placements in AluSx and AluJb.

Supplementary Table S9 reports the **unfiltered** policy for 3,349 AluSx and
2,929 AluJb reads, each 150 bases long with zero substitutions; k = 21 and
w = 20. Both `unfiltered` and `copycap1000` results occur in the saved data;
the latter is a separate filtered control. Timing used eight technical cycles
with four complete read-set sweeps per cycle, not eight biological replicates.

`kernel_timings.csv` contains individual cycle-level CPU and wall timings;
`kernel_timing_summary.csv` summarizes those measurements. The separate
`workload_by_context_method_policy.csv` provides candidate and seed-match
statistics, and `primary_candidate_comparisons.csv` contains paired workload
comparisons. These workload values are not timing measurements. Alternative
locations exclude the exact known source locus, not every start within its
source interval. Reference-derived reads and per-read coordinates are not
distributed here.

These are saved historical results, not a new performance run. The experiment-specific reproduction materials and validation limitations are documented in `reproducibility/supplementary_s3_5_alu/` when available; see the [results index](../README.md) and [dataset guide](../../docs/datasets.md).
