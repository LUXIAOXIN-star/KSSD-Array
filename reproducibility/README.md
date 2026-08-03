# Manuscript reproducibility

This directory contains the paper experiment workflows used to validate the
KSSD-Array manuscript results. Ordinary library users do not need to run these
workflows; accepted compact outputs are under
[`benchmark_results/`](../benchmark_results/). Each workflow documents its
required external inputs, and large references, reads, alignments, and indexes
are deliberately not stored in Git.

## Workflow index

| Paper item | Workflow |
| --- | --- |
| Table 2 exhaustive validation | [`table2/`](table2/) |
| Figure 2 single-threaded minimizer benchmark | [`figure2/`](figure2/) |
| Figure 3 multithreaded benchmark | [`figure3/`](figure3/) |
| Main-text Figure 4 bucket-balance analysis | [`figure4/`](figure4/) |
| Matched-workload ntHash comparison | [`table4_matched_workload/`](table4_matched_workload/) |
| Method-native ntHash comparison workflow | [`table4/`](table4/) |
| Supplementary Figure S1 and Table S1 | [`minimap2/indexing/`](minimap2/indexing/) |
| Corrected Supplementary Table S2 | [`minimap2/alignment_consistency_truth_origin/`](minimap2/alignment_consistency_truth_origin/) |

The recorded manuscript environment, compiler policy, workflow flags, and
pinned commits are summarized in [`ENVIRONMENT.md`](ENVIRONMENT.md).

## Status matrix

| Manuscript result | Public status | Formal rerun in the validated release candidate |
|---|---|---:|
| Table 2 | Fully reproduced exactly | yes |
| Figure 2 | Accepted compact result; KSSD fastest in 30/30 groups; workflow smoke-tested | accepted external run |
| Matched-workload ntHash | Detailed Supplementary result; workflow smoke-tested | accepted external run |
| Figure 3 | Accepted compact result; KSSD fastest in 30/30 groups; workflow smoke-tested | accepted external run |
| Figure 4 | Formally reproduced; trends agree, with exact summary and plotted data in the accepted validation | yes |
| Supplementary Figure S1 and Table S1 | Public-inline integration validated; controlled three-dataset/five-pair workflow available | yes, public-inline final run |
| Corrected Supplementary Table S2 | All truth reads; ART strand-aware intervals; fixed truth-origin repeat subsets | accepted BAMs reused; 7/7 fixtures, 12/12 compatibility deltas, 62/62 corrected checks |

The matrix does not claim that every performance result was formally rerun.
Figure 2, matched ntHash, and Figure 3 public workflows have functional smoke
validation; their accepted formal results are copied with source manifests.
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

Only small deterministic fixtures are committed with workflow source. Compact
accepted CSVs, figures, reports, and manifests are published under
`benchmark_results/`. Full references, FASTQ files, generated indexes,
SAM/BAM/PAF files, per-read diagnostics, and large logs are not distributed.
Dataset identities and resolution rules are in
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
reproducibility/reproduce_manuscript.sh s2-corrected-tests
```

`all-smoke` runs all of them and therefore requires `MINIMAP2_SOURCE_DIR`.
The Make alias is
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
The preflight uses hash-verified fixtures generated from public C source in a
temporary directory. Formal mode requires the three pinned
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

## Corrected Supplementary Table S2

The corrected workflow reuses hash-verified accepted BAMs; it does not run
Minimap2. First run its deterministic fixture tests:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s reproducibility/minimap2/alignment_consistency_truth_origin/tests -v
```

The complete external-data commands and stop conditions are documented in
[`minimap2/alignment_consistency_truth_origin/README.md`](minimap2/alignment_consistency_truth_origin/README.md).
The historical evaluator remains available only for compatibility/provenance;
its table is superseded.
