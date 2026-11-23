# KSSD-Array results and source data

Start with the [experiment and reproducibility guide](../docs/EXPERIMENTS.md) for the manuscript numbering, protocols and saved data.

This directory contains compact experimental results, raw repetitions and their source bindings. Experiment code and full-run requirements are under [reproducibility](../reproducibility/README.md). Numerical data, captions and plots retain their actual input, version and timing definitions.

## Current manuscript materials

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
| Additional diagnostic, no SI table number | [c_segment_scan](c_segment_scan/README.md) | C=4–8 structural sensitivity |

Begin with each result directory’s README, then its manuscript figure or table and its summary data. Raw observations and source/identity records provide the detailed evidence. Some files are explicitly marked as derived path-redacted copies. The Figure 3 and gxhash raw tables with tokenized paths, and the Human multithread indexing formal and warmup tables, are derived metadata views of the saved records rather than byte-identical originals. Table S8 provides the available historical statistical summaries.

## Read a result

For each comparison, start with its README/caption, then the summary and raw table. Source, build, command, input-hash and validation records provide the detailed binding. Raw and summary tables are different views of the same measurements, not independent experiments.

- Means, sample SDs, medians, observed ranges and bootstrap intervals retain their stated definitions. A paired-ratio interval is not a throughput error bar.
- Pure integer scoring, canonical rolling DNA scoring, native minimizer sampling and complete indexing have different timing boundaries. Do not pool them into one speed ranking.
- Selected positions, distinct keys, occurrence totals, payload bytes and index bytes are different quantities. Standard density uses selected positions divided by valid k-mer starts where that definition applies.
- All conditions are retained, including those favoring simple reversible functions or other baselines. Small descriptive differences do not establish stable superiority or equivalence.

## Corrected all-read accuracy

The four simulated read conditions use all truth reads in the denominator, with unmapped or missing-primary reads counted as incorrect. Reference, strand and start-within-5-bp correctness follow the retained ART truth. The absolute differences are strictly below 0.05 percentage points for the four all-read conditions. That statement does not extend to the fixed repeat-origin subset or establish statistical equivalence.

## Historical results

The [original Figure 2 package](figure2_single_thread/README.md) records the score-plus-window rescan throughput used for current Figure 2b. Its historical 30/30 ranking must not be attributed to the independent-scoring panel, Figure 2a.

Large FASTA/FASTQ files, BAMs, indexes, encoded arrays and dependency caches are external. Their required identities and preparation are documented with the corresponding workflow. Source hashes and explicit projection records distinguish unchanged originals from any public metadata view that omits internal author instructions.

[Dataset identities and acquisition](../docs/datasets.md) accompany the compact measurements. For current labels use the [experiment guide](../docs/EXPERIMENTS.md).
