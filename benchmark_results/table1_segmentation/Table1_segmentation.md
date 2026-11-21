# Table 1. Segment ranges and examples

| K-mer length range | Number of segments | Actual examples (segment lengths in nucleotides) |
| --- | --- | --- |
| 1 <= k <= 8 | 1 | k=6: 6; k=8: 8 |
| 8 < k <= 16 | 2 | k=9: 5/4; k=15: 8/7; k=16: 8/8 |
| 16 < k <= 24 | 3 | k=19: 7/6/6; k=21: 7/7/7; k=24: 8/8/8 |
| 24 < k <= 32 | 4 | k=25: 7/6/6/6; k=31: 8/8/8/7; k=32: 8/8/8/8 |

Segment lengths are in nucleotides. The balanced layout uses ceil(k/8) segments; the first k mod n segments receive one extra nucleotide. Examples are derived from the unchanged layout function, not timing measurements.
