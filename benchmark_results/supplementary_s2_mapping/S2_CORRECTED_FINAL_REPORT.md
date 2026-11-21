# Corrected Supplementary Table S2 final report

Final validation: **PASS**.

- Accepted alignments were reused; Minimap2 was not rerun.
- All required inputs and 16 BAMs were hash verified; BAM quickcheck passed.
- ART truth semantics are unambiguous and 20 both-strand examples were reviewed.
- All 12 historical displayed deltas were reproduced before correction.
- Four all-read, four fixed repeat-origin, mapping-rate, MAPQ, paired bootstrap, and McNemar analyses completed.
- All validation checks and seven synthetic fixture tests passed.
- Historical results remain untouched in `$KSSD_RELEASE_HOST/KSSD-Array-formal-results/minimap2-alignment-s2-20260728-v1`.

## Corrected all-read accuracy

| Reference | Read | Original | KSSD | KSSD−Original (95% CI), pp | McNemar p |
| --- | ---: | ---: | ---: | ---: | ---: |
| Human GRCh38.p14 | 100 bp | 89.747% | 89.714% | -0.033 pp (95% CI -0.097, +0.028) | 0.2956 |
| Human GRCh38.p14 | 150 bp | 91.250% | 91.231% | -0.019 pp (95% CI -0.080, +0.041) | 0.5334 |
| Zea mays B73 RefGen_v5 | 100 bp | 71.912% | 71.945% | +0.033 pp (95% CI -0.041, +0.107) | 0.3786 |
| Zea mays B73 RefGen_v5 | 150 bp | 82.161% | 82.113% | -0.048 pp (95% CI -0.113, +0.017) | 0.1502 |

## Corrected repeat-origin accuracy

| Reference | Read | Original | KSSD | KSSD−Original (95% CI), pp | McNemar p |
| --- | ---: | ---: | ---: | ---: | ---: |
| Human GRCh38.p14 | 100 bp | 91.199% | 91.096% | -0.103 pp (95% CI -0.173, -0.033) | 0.004109 |
| Human GRCh38.p14 | 150 bp | 93.569% | 93.557% | -0.011 pp (95% CI -0.073, +0.050) | 0.7319 |
| Zea mays B73 RefGen_v5 | 100 bp | 69.074% | 69.107% | +0.033 pp (95% CI -0.048, +0.116) | 0.4267 |
| Zea mays B73 RefGen_v5 | 150 bp | 80.652% | 80.612% | -0.040 pp (95% CI -0.112, +0.032) | 0.2709 |

## Mapping rate

| Reference | Read | Original | KSSD | KSSD−Original, pp |
| --- | ---: | ---: | ---: | ---: |
| Human GRCh38.p14 | 100 bp | 99.198% | 99.062% | -0.136 |
| Human GRCh38.p14 | 150 bp | 99.853% | 99.811% | -0.041 |
| Zea mays B73 RefGen_v5 | 100 bp | 97.859% | 97.751% | -0.108 |
| Zea mays B73 RefGen_v5 | 150 bp | 99.142% | 99.131% | -0.011 |

## MAPQ = 60 among all truth reads

| Reference | Read | Original | KSSD | KSSD−Original (95% CI), pp |
| --- | ---: | ---: | ---: | ---: |
| Human GRCh38.p14 | 100 bp | 72.554% | 72.381% | -0.174 pp (95% CI -0.218, -0.131) |
| Human GRCh38.p14 | 150 bp | 77.834% | 77.596% | -0.238 pp (95% CI -0.275, -0.202) |
| Zea mays B73 RefGen_v5 | 100 bp | 37.369% | 36.931% | -0.437 pp (95% CI -0.499, -0.377) |
| Zea mays B73 RefGen_v5 | 150 bp | 48.767% | 48.270% | -0.497 pp (95% CI -0.559, -0.435) |

Conclusion: the corrected all-read analysis still supports negligible global correctness differences. The repeat-origin conclusion requires revised wording because Human 100 bp shows a small but paired-significant difference favoring Original and both Human directions differ from the historical method-specific repeat subsets.

The manuscript-ready tables are `supplementary_table_s2_corrected.csv` and
`supplementary_table_s2_mapq_corrected.csv`. The compact review archive is
`S2_CORRECTED_REVIEW_PACKET.tar.gz`; large per-read diagnostics remain outside
Git and outside that archive.
