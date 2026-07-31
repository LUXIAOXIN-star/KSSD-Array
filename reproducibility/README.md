# Manuscript reproducibility

This directory contains the exact public-library workflows used to validate
the KSSD-Array manuscript results. It is intentionally separate from the core
library interface while remaining in the same repository and version.

## Included workflows

- Figure 2 single-threaded minimizer benchmark;
- Figure 3 multithreaded benchmark;
- Table 4 ntHash comparison;
- Figure 4 bucket-balance analysis;
- Supplementary Figure S1 Minimap2 integration.

The recorded manuscript environment, compiler policy, workflow flags, and
pinned commits are summarized in [`ENVIRONMENT.md`](ENVIRONMENT.md).

## Status matrix

| Manuscript result | Public status | Formal rerun in the validated release candidate |
|---|---|---:|
| Table 2 | Fully reproduced exactly | yes |
| Figure 2 | Workflow migrated and smoke-tested | no |
| Table 4 | Workflow migrated and smoke-tested | no |
| Figure 3 | Workflow migrated and smoke-tested | no |
| Figure 4 | Formally reproduced; trends agree, with exact summary and plotted data in the accepted validation | yes |
| Supplementary Figure S1 and Table S1 | Public-inline integration validated; controlled three-dataset/five-pair workflow available | yes, public-inline final run |
| Supplementary Table S2 | Formally reproduced; all twelve displayed deltas match after rounding | yes |

The matrix does not claim that every performance result was formally rerun.
Figure 2, Table 4, and Figure 3 validation is functional smoke validation.
Indexing time is host-sensitive; the public-inline S1 run is reported only for
its recorded host and controlled protocol.

## Benchmark scope limitation

The throughput benchmark workflows implement minimizer selection independently
for each window and do not deduplicate equal minimizers selected by adjacent
windows. Their counts and throughput therefore describe per-window minimizer
selection, not a deduplicated minimizer stream. The workflow parity checks
validate the public and fast KSSD-Array mapping paths and the documented
per-window benchmark semantics; they do not claim full minimizer-output
equivalence with tools that apply adjacent-window deduplication or other
post-processing.

## Dependencies

The core and Table 2 require a C11 toolchain. Figure 2 and Figure 4 require
xxHash; Figure 3 additionally requires OpenMP and zlib; Table 4 requires the
pinned ntHash 2.4.0; plotting uses R or Python packages documented in
[`../docs/dependencies.md`](../docs/dependencies.md). Minimap2 workflows use a
clean checkout of the pinned Minimap2 2.30-r1287 commit.

## Dataset and output policy

Only small deterministic fixtures are committed. Full references, FASTQ
files, generated indexes, SAM/BAM/PAF files, raw formal tables, and manuscript
figures are not distributed. Dataset identities and resolution rules are in
[`../docs/datasets.md`](../docs/datasets.md) and
[`data/datasets.json`](data/datasets.json).

Formal commands require explicit input and output locations. Generated output
must be outside the source tree. The indexing workflow uses one unique
temporary index at a time, captures its identity, and removes it before the
next run.

## Unified command interface

```sh
reproducibility/reproduce_manuscript.sh help
reproducibility/reproduce_manuscript.sh status
reproducibility/reproduce_manuscript.sh core-tests
```

The lightweight commands are:

```sh
reproducibility/reproduce_manuscript.sh table2
reproducibility/reproduce_manuscript.sh figure2-smoke
reproducibility/reproduce_manuscript.sh table4-smoke
reproducibility/reproduce_manuscript.sh figure3-smoke
reproducibility/reproduce_manuscript.sh figure4-preflight
reproducibility/reproduce_manuscript.sh minimap2-smoke
reproducibility/reproduce_manuscript.sh minimap2-indexing-preflight
reproducibility/reproduce_manuscript.sh minimap2-alignment-preflight
```

`all-smoke` runs all of them and therefore requires `MINIMAP2_SOURCE_DIR` and
`PHASE5B_OUTPUT` as described below. The Make alias is
`make reproducibility-smoke`.

## Table 2

The exhaustive 9-mer validator requires no external dataset:

```sh
make table2-validation
```

Details: [`table2/README.md`](table2/README.md).

## Figure 2

```sh
make figure2-smoke
reproducibility/reproduce_manuscript.sh figure2-formal \
  --datasets /path/to/a.fa /path/to/b.fa \
  --dataset-names Synthetic_300M Human_GRCh38 \
  --k-values 16 19 21 24 31 --w-values 10 20 50 --repeats 3 \
  --output-dir /external/results/figure2
```

Details: [`figure2/README.md`](figure2/README.md).

## Table 4

Prepare or select the pinned ntHash prefix before running:

```sh
reproducibility/table4/prepare_nthash.sh
make table4-smoke
reproducibility/reproduce_manuscript.sh table4-formal \
  --datasets /path/to/a.fa /path/to/b.fa \
  --dataset-names Synthetic_300M Human_GRCh38 \
  --k-start 4 --k-end 32 --repeats 3 \
  --output-dir /external/results/table4
```

Details: [`table4/README.md`](table4/README.md).

## Figure 3

```sh
make figure3-smoke
reproducibility/reproduce_manuscript.sh figure3-formal \
  --datasets /path/to/a.fa /path/to/b.fa \
  --dataset-names Synthetic_300M Human_GRCh38 \
  --w-values 10 20 50 --threads 1 2 4 8 16 --repeats 3 \
  --output-dir /external/results/figure3
```

Details: [`figure3/README.md`](figure3/README.md).

## Figure 4

```sh
make figure4-preflight
reproducibility/reproduce_manuscript.sh figure4-formal \
  --k-values 6 7 8 9 10 11 12 13 14 \
  --sequence-lengths 4000000 8000000 --bins 101 199 499 \
  --repeats 100 --jobs 1 --output-dir /external/results/figure4
```

Details: [`figure4/README.md`](figure4/README.md).

## Supplementary Figure S1 and Table S1

Set `MINIMAP2_SOURCE_DIR` to a clean checkout of the pinned upstream commit.
The preflight uses committed fixtures. Formal mode requires the three pinned
reference genomes and an explicit external output directory.

```sh
MINIMAP2_SOURCE_DIR=/path/to/minimap2 \
  reproducibility/reproduce_manuscript.sh minimap2-indexing-preflight

MINIMAP2_SOURCE_DIR=/path/to/minimap2 KSSD_DATA_DIR=/path/to/data-root \
  reproducibility/reproduce_manuscript.sh minimap2-indexing-formal \
  --output-dir /external/results/indexing \
  --dataset Arabidopsis=/path/to/arabidopsis.fna.gz \
  --dataset Human_GRCh38=/path/to/grch38.fna \
  --dataset Zea_mays=/path/to/zea-mays.fa
```

Details: [`minimap2/indexing/README.md`](minimap2/indexing/README.md).

## Supplementary Table S2

Set `PHASE5B_OUTPUT` to the accepted indexing output containing the matching
original and integrated executables and indexes.

```sh
PHASE5B_OUTPUT=/path/to/indexing-output \
  reproducibility/reproduce_manuscript.sh minimap2-alignment-preflight

PHASE5B_OUTPUT=/path/to/indexing-output \
  reproducibility/reproduce_manuscript.sh minimap2-alignment-formal \
  --output-dir /external/results/alignment \
  --reference Dataset=/path/to/reference.fa \
  --reads Dataset:100=/path/to/reads.fq \
  --truth Dataset:100=/path/to/truth.tsv \
  --bed Dataset=/path/to/repeats.bed
```

Details:
[`minimap2/alignment_consistency/README.md`](minimap2/alignment_consistency/README.md).
