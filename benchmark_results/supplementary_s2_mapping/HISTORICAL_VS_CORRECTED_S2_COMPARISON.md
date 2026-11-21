# Historical versus corrected Supplementary Table S2

The old evaluator is reproduced exactly, but it used mapped-primary denominators, method-specific reported-alignment repeat subsets, and a reverse-coordinate expression that is not ART's genomic conversion. The corrected primary analysis uses all truth reads, official ART strand-aware genomic intervals, and one fixed truth-origin repeat set.

| Reference | Read | Old global Δ | Corrected all-read Δ | Old reported-repeat Δ | Corrected truth-origin-repeat Δ | Old MAPQ60/mapped Δ | Corrected MAPQ60/all Δ | Corrected MAPQ60/mapped Δ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Human GRCh38.p14 | 100 bp | +0.047 | -0.033 | +0.040 | -0.103 | -0.075 | -0.174 | -0.075 |
| Human GRCh38.p14 | 150 bp | +0.030 | -0.019 | +0.035 | -0.011 | -0.207 | -0.238 | -0.207 |
| Zea mays B73 RefGen_v5 | 100 bp | +0.063 | +0.033 | +0.070 | +0.033 | -0.405 | -0.437 | -0.405 |
| Zea mays B73 RefGen_v5 | 150 bp | -0.037 | -0.048 | -0.030 | -0.040 | -0.496 | -0.497 | -0.496 |

## Flags and interpretation

- Global-delta sign changes occur for Human 100 bp, Human 150 bp, and Zea mays 150 bp; none of the global old-to-new changes exceeds 0.05 percentage points.
- Repeat-delta sign changes occur for Human 100 bp and Human 150 bp. Human 100 bp changes by more than 0.05 percentage points; the other repeat changes do not.
- Mapping-rate differences are negative for KSSD in all four conditions (−0.136, −0.041, −0.108, and −0.011 percentage points), so an all-read denominator incorporates those differences instead of conditioning them away.
- Replacing method-specific reported-alignment repeat subsets with one truth-origin subset changes both denominator composition and direction for the two Human conditions.
- Correct ART strand conversion raises absolute accuracy substantially relative to the historical coordinate test; this is a coordinate-definition correction, not an alignment rerun.

The statement **‘global mapping-accuracy differences were negligible’ remains supported** under the corrected all-read metric: all four KSSD–Original deltas are within ±0.05 percentage points, all four 95% paired bootstrap intervals include zero, and the exact McNemar tests for all-read correctness are non-significant.

The old repeat-region conclusion needs qualification. Absolute method differences remain small (maximum 0.103 percentage points), but Human 100 bp favors Original by 0.103 percentage points (95% CI −0.173 to −0.033; exact McNemar p=0.0041), and both Human directions reverse relative to the historical method-specific subsets. Any statement that KSSD was consistently equal or favorable in repeat regions is not supported; the corrected fixed-subset values should replace it.
