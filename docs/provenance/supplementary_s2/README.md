# Supplementary Table S2 source provenance

The accepted numerical output in Supplementary Table S2 was produced by the
historical Minimap2 integration lineage retained in the local repository at
commit `f1f783461f0b58acef0f92de67f9217dc99749d7`. That commit contains the
external-call Minimap2 patch preserved here as `minimap2_f1f7834.patch`.

The alignment-evaluation workflow itself was added by the descendant commit
`3da13ce1dc4f52b8a7a31d609cf74bb96fc0fece`. Its exact config, runner, and
summarizer are preserved in this directory. This distinction matters:
`f1f7834` identifies the historical integrated executable source, while
`3da13ce` identifies the workflow that generated and summarized Table S2.

## Comparison with the public release

- `historical_config.json` is byte-identical to
  `reproducibility/minimap2/alignment_consistency/config.json`.
- `historical_summarize_alignment_consistency.py` is byte-identical to the
  public summarizer.
- The public runner changes repository-relative locations and permits a fresh
  pinned-version executable during fixture preflight. Formal mode still checks
  the configured executable hashes and uses the same alignment commands,
  BAM filters, correctness calculation, repeat selection, diagnostics, and
  summarizer. Thus the Table S2 formal metric implementation is unchanged.
- The final public Minimap2 patch is the validated header-inline implementation,
  not the historical external-call patch. The accepted S2 numbers are therefore
  bound to the exact historical patch retained here. Functional equivalence of
  the mapping API is covered by the public inline equivalence and Minimap2
  output tests; this provenance record does not claim that the two patch files
  or executables are byte-identical.

No alignment was rerun and no accepted numerical value was changed while
creating this snapshot.

## SHA-256 identities

| File | SHA-256 |
|---|---|
| `historical_config.json` | `be0b8dcc06b3b281c8a7f8079593ba947510523a6dc4d122b6c34706b2ca8b6d` |
| `historical_run_alignment_consistency.py` | `8e5053d11339010d3072ecfc4c1af66be02b8eaac4c825de63d0b291fc3c7b07` |
| `historical_summarize_alignment_consistency.py` | `dab4b962655a817c47a2d6fd0d639a1011715020722a2de9856de865be45c298` |
| `minimap2_f1f7834.patch` | `89610194db47197c3eeb4ddee4c38c9233f00251246dd9210b597616791ba572` |

