# Public corrected-S2 workflow source state

This deterministic provenance record is distributed with the public workflow.
It is materialized automatically by `package_corrected_s2.py`; no manual copy
from a developer machine is required.

- Project release: `KSSD-Array 1.1.0-paper`
- Workflow: `reproducibility/minimap2/alignment_consistency_truth_origin`
- Source identity: content-addressed by the generated `source_sha256.tsv`
- Commit identity: intentionally not embedded, so packaging does not depend on
  an unpublished or pending release commit
- Accepted scientific inputs: pinned by `config.json` and the generated input
  and BAM SHA-256 inventories
- Minimap2 alignments rerun by this workflow: `NO`
- Private developer paths permitted in this record: `NO`

The packaging step requires any pre-existing `SOURCE_REPOSITORY_STATE.md` in the
output directory to be byte-identical to this public template. A mismatch or a
private developer path is a hard failure.
