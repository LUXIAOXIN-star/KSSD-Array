# Table 2 validation provenance

`make table2-validation` enumerates all 262,144 encoded 9-mers through the
public library. The calculated results are:

| Method | Unique | Collisions | Collision rate |
|---|---:|---:|---:|
| rank-derived | 262,144 | 0 | 0.000000% |
| low-bit mask ablation | 183,296 | 78,848 | 30.078125% |
| direct mapping ablation | 117,760 | 144,384 | 55.078125% |

The manuscript-rounded rates are 0.00%, 30.08%, and 55.08%. The calculated
CSV had SHA-256
`faeccdebb9f98b56070e81c734a719f4b823643a98fb43c6960ddf24b2f7ea30`
and matched the accepted historical CSV exactly. Status:
`fully_reproduced_exact`.
