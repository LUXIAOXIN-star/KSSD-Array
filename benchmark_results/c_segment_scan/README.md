# Segment-cap sensitivity (Supplementary S10)

The frozen Phase3 data contain 250 mapping runs (50 groups, five repeats), 750 common-window runs (150 groups, five repeats), and 250 initialization measurements (25 groups, ten repeats). C ranges from4 through8 and k is16/19/21/24/31. Full per-condition mean/sampleSD and all original repetitions are retained.

PHASE3_C_SENSITIVITY_TABLE.tsv is a different aggregation: the mapping throughput is a geometric mean of two input-specific arithmetic means, and the common-window throughput is a geometric mean across two inputs and three w values. These are not repeated-measurement means with an SD. Initialization milliseconds and allocation/payload bytes retain their separate definitions.

The compact saved tables preserve the historical aggregation. A complete portable reaggregation entry is not provided in this package; historical build and measurement details are documented separately.
