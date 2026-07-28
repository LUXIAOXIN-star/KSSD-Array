# Supplementary Table S2 provenance

The formal workflow used the exact GRCh38.p14 and Zea mays B73 RefGen_v5
references and four accepted simulated read files. It rebuilt both original
and integrated indexes, aligned at one thread, and evaluated global accuracy,
repeat-region accuracy, and MAPQ 60 fraction.

All integer counts matched the accepted record exactly. All twelve displayed
percentage-point deltas matched the manuscript after three-decimal rounding.
The full input identities and ART protocol are recorded in
[`reproducibility/minimap2/alignment_consistency/config.json`](../../reproducibility/minimap2/alignment_consistency/config.json)
and [`docs/datasets.md`](../datasets.md). Status: `fully_reproduced`.
