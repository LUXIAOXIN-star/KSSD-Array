# Supplementary Figure S1 and Table S1 public status

## Public-inline final result

The public runtime-inline integration completed a controlled three-dataset run
with five accepted pairs per dataset. Generated raw data, figures, indexes,
and binaries remain outside Git; the repository contains the exact runner,
configuration, patch, and validation reports. The manuscript itself was not
modified in this change.

## Available workflow and validated fields

The repository provides the complete workflow under
`reproducibility/minimap2/indexing`. It builds original and integrated
Minimap2 2.30-r1287 executables from the same pinned upstream commit, validates
the three configured references, uses one indexing thread, performs one
discarded warm-up per method/dataset, and alternates method order across five
pairs. Every run uses a unique temporary index path; size, hash, magic, and
deterministic fields are captured before that completed index is deleted.

Deterministic fields verified against the historical protocol include sequence
and minimizer counts, total and average occurrences, average spacing, and the
configured algorithm parameters. Swap-polluted attempts are preserved and
excluded under a predeclared environmental rule, never based on observed
performance.

The formal workflow keeps at most one large temporary index at a time. Raw
timing records, paired ratios, summaries, final table/figure files, commands,
environment metadata, and recursive output hashes remain available, but
generated artifacts must stay outside the repository.

## Running a formal experiment

A formal run is always explicit and writes outside the repository:

```sh
KSSD_DATA_DIR=/path/to/data-root \
reproducibility/reproduce_manuscript.sh minimap2-indexing-formal \
  --config reproducibility/minimap2/indexing/config.json \
  --output-dir /external/results/indexing \
  --dataset Arabidopsis=/path/to/arabidopsis.fna.gz \
  --dataset Human_GRCh38=/path/to/grch38.fna \
  --dataset Zea_mays=/path/to/zea-mays.fa
```

Set `MINIMAP2_SOURCE_DIR` to a clean checkout of the pinned upstream commit.
Timing comparisons must record and control host load, storage, memory pressure,
cache state, and hardware. No universal or hardware-independent acceleration
is claimed. Corrected Supplementary Table S2 has a separate all-read,
truth-origin workflow that reuses accepted BAMs without rerunning Minimap2.
