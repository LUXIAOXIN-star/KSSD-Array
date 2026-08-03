# Historical Supplementary Table S2 provenance

This is a compact provenance record, not the active Supplementary Table S2
result. The historical evaluation is superseded by the corrected all-read,
ART strand-aware, fixed truth-origin-repeat analysis published in
[`benchmark_results/supplementary_s2_mapping`](../../../benchmark_results/supplementary_s2_mapping/README.md).
The historical formal result directory remains unchanged outside Git.

The historical analysis was superseded because:

1. unmapped or missing-primary reads were excluded from its global accuracy
   denominator;
2. repeat subsets were selected separately for each method from reported
   alignment coordinates instead of once from simulated truth origin;
3. its reduced truth TSV did not retain ART strand;
4. negative-strand positions require ART's reference-length and aligned-span
   conversion, not the historical `offset-(read_length-1)` shortcut.

The historical evaluator nevertheless remains useful as a compatibility
check: the corrected workflow first reproduced all 12 displayed historical
deltas from the accepted BAMs before applying the corrected definitions.
`HISTORICAL_METRIC_DEFINITIONS.md` records the exact old denominators and
coordinate rule, and `historical_table_s2.sha256` records the checksum of the
former active public table without republishing it as a result.

## Source lineage

- Historical integrated Minimap2 source commit:
  `f1f783461f0b58acef0f92de67f9217dc99749d7`.
- Historical evaluation-workflow commit:
  `3da13ce1dc4f52b8a7a31d609cf74bb96fc0fece`.
- `historical_config.json`,
  `historical_run_alignment_consistency.py`, and
  `historical_summarize_alignment_consistency.py` are source snapshots.
- `minimap2_f1f7834.patch` is the historical external-call integration
  patch; the current public integration is the separately validated
  runtime-inline patch.
- `source_manifest.tsv` binds every snapshot to its original path, commit,
  and SHA-256.

No alignment was rerun and no formal or historical result directory was
modified while creating this provenance record.
