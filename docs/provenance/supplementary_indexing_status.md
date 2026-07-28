# Supplementary Figure S1 and Table S1 public status

## Accepted manuscript result

The manuscript reports indexing measurements obtained under the authors'
previously accepted controlled low-load protocol. These remain the manuscript
values. Phase 7 neither replaces them nor presents a different host-state run
as the authoritative result.

## Available workflow and validated fields

The repository provides the complete workflow under
`reproducibility/minimap2/indexing`. It builds original and integrated
Minimap2 2.30-r1287 executables from the same pinned upstream commit, validates
the three configured references, uses one indexing thread, alternates method
order, and retains three overwriteable dataset-specific indexes rather than
one index per repeat.

Deterministic fields verified against the historical protocol include sequence
and minimizer counts, total and average occurrences, average spacing, and the
configured algorithm parameters. Phase 7 validates the small fixture
preflight, not formal performance.

The formal workflow keeps only one overwriteable generated index per dataset
and method state. Repeats therefore do not accumulate eighteen simultaneous
large index files. Raw timing records, summaries, and figure generation remain
available, but generated artifacts must stay outside the repository.

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
is claimed. Supplementary Table S2 has a separate workflow and was formally
reproduced.
