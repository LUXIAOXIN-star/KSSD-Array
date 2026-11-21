# Reproducing KSSD-Array experiments

The [experiment and reproducibility guide](../docs/EXPERIMENTS.md) maps each workflow to manuscript numbering and identifies its evidence and limitations.

This directory contains experiment source, input definitions, validation and plotting entries. Compact results are indexed under [benchmark_results](../benchmark_results/README.md). Ordinary library builds do not run these workflows.

## Choose the required operation

| Operation | Inputs and effect |
| --- | --- |
| Inspect existing results | Read the result table, raw measurements and protocol; no computation is required. |
| Check summary arithmetic | Consume compact existing CSV/TSV files; do not rebuild or measure the scientific programs. |
| Redraw a figure | Consume the bound raw or summary table with the stated plotting dependencies. |
| Validate functionality | Run the documented small fixtures; these tests do not establish performance. |
| Repeat a full experiment | Supply the exact external inputs and dependencies, build locally and measure into a new output directory. |

## Current experiment definitions

| Manuscript item | Directory | Workload |
| --- | --- | --- |
| Figure 1 | [figure1_algorithm](figure1_algorithm/README.md) | 19-mer algorithm example |
| Figure 2a | [figure2a_independent_scoring](figure2a_independent_scoring/README.md) | Independent scores from preencoded k-mers |
| Figure 2b | [figure2b_window_selection](figure2b_window_selection/README.md) | Scoring and per-window selection with rescan |
| Figure 3 / Table S5 | [figure3_runtime_density](figure3_runtime_density/README.md) | Forward-only materialized scores and sampling density |
| Figure 4 | [figure4_bucket_balance](figure4_bucket_balance/README.md) | Bucket-balance non-rejection |
| Table 1 | [table1_segmentation](table1_segmentation/README.md) | Segment layout and lookup storage |
| Table 2 / Table S3 | [table2_nthash](table2_nthash/README.md) | Continuous-DNA ntHash comparison |
| Table 3 / Table S10 | [table3_minimap2_indexing](table3_minimap2_indexing/README.md) | Three-reference single-thread indexing |
| Figure S1 | [supplementary_s1_multithreading](supplementary_s1_multithreading/README.md) | Multithread score/window scaling |
| Table S1 | [supplementary_s1_1_xor_odd](supplementary_s1_1_xor_odd/README.md) | XOR and odd-multiply controls |
| Table S2 | [supplementary_s1_2_gxhash](supplementary_s1_2_gxhash/README.md) | gxhash scoring comparison |
| Tables S3–S4 | [supplementary_s2_nthash](supplementary_s2_nthash/README.md) | Primary ntHash comparison and separate LTO sensitivity |
| Table S5 | [supplementary_s3_1_runtime_density](supplementary_s3_1_runtime_density/README.md) | Runtime and density supplementary data |
| Table S6 | [supplementary_s3_2_streaming](supplementary_s3_2_streaming/README.md) | Full-length streaming |
| Tables S7a–c | [supplementary_s3_3_external_simd](supplementary_s3_3_external_simd/README.md) | Separate external SIMD tasks A, B and C |
| Table S8 | [supplementary_s3_4_repetitive_words](supplementary_s3_4_repetitive_words/README.md) | Repetitive-word selection |
| Table S9 | [supplementary_s3_5_alu](supplementary_s3_5_alu/README.md) | Controlled Alu read placement |
| Tables S10–S12 | [supplementary_s4_minimap2](supplementary_s4_minimap2/README.md) | Indexing, accuracy and Human multithreading |

Each README states the available sources, input requirements and current validation status. Historical records and small tests are not complete benchmark replay. The Figure 2a, Figure 2b and Figure 4 historical programs have passed separate small-input checks; their complete performance campaigns have not been rerun. For the LTO workflow, small-input OFF/ON build and correctness checks passed in the adapted environment, but the public full-grid entry is not yet packaged or fully replayed.

## Existing-table checks and plotting

The [independent-scoring workflow](figure2a_independent_scoring/README.md) and [ntHash workflow](table2_nthash/README.md) describe their source and available checks. The 400 ntHash raw rows contain related score, window and total stages: each method-condition has five repeats, not fifteen.

Throughput summaries first calculate each repeat's count/time and then aggregate the individual rates. Sample standard deviation uses n−1. Paired-ratio bootstrap intervals are retained as intervals for the paired statistic; they are not either method's standard deviation. Where a source instead reports medians, observed ranges or a rate derived from median time, that definition remains explicit.

## Full experiments and dependencies

Core and exhaustive validation require C11. Individual experiments may additionally require pinned xxHash, ntHash, Rust/Cargo, OpenMP, zlib, Python plotting packages, R, Minimap2 or evaluation tools; see [dependencies](../docs/dependencies.md) and each workflow's own requirements.

The historical gxhash workflow is documented in [gxhash](supplementary_s1_2_gxhash/README.md). It requires the two exact external FASTA containers, a compatible local toolchain and the recorded CPU-affinity constraints. A new replay must build new executables, validate them, prepare its own arrays and generate fresh timing records. Historical expected checksums constrain deterministic outputs; historical timing and PASS files are not fresh measurements.

Cargo dependency resolution must match `Cargo.lock`. If dependency caches are excluded from a distribution, offline replay requires a separately supplied verified cache or vendored source, and must fail clearly when it is unavailable. Do not describe cache-free distribution as a self-contained offline build. Dependency preparation, if needed, is separate from the offline experiment computation.

All formal data and output paths are explicit. Verify the exact input identities and preprocessing rules before running; do not substitute another DNA sequence or use existing results as the output directory. Preserve failed or incomplete runs and their logs rather than overwriting them or silently changing parameters.

## Historical directory names

Legacy paths are retained so source and command bindings remain valid:

- [`table2`](table2/README.md) is the exhaustive nine-mer API/collision validation from an earlier table. It is **not** the current ntHash Table 2.
- [`figure2`](figure2/README.md) is the historical single-thread score-plus-window implementation. It is **not** the current independent-scoring Figure 2.

Retaining these sources does not transfer their versions, timing boundaries, selection rules or labels to the current experiments. The [input generation guide](data_generation/README.md) and [dataset guide](../docs/datasets.md) describe exact synthetic generation, ART truth and repeat-annotation provenance.

## Rebuild figures from saved results

The independent scoring panel can be redrawn from the saved measurements with
[`figure2a_independent_scoring/plot_figure2_independent_scoring.py`](figure2a_independent_scoring/plot_figure2_independent_scoring.py); the window-rescan and multithreaded
workflows are under [`figure2/`](figure2/) and [`figure3/`](figure3/),
respectively. These historical directory names predate the current manuscript
numbering. The final Figure 3 source data and script are under
[`benchmark_results/figure3_runtime_density/`](../benchmark_results/figure3_runtime_density/).
The final Figure 4 script is [`figure4/plot_figure4_manuscript_labels.py`](figure4/plot_figure4_manuscript_labels.py).
See each script's documented arguments and dependencies. A saved-data redraw is
not a new performance run; write output to a new location.
