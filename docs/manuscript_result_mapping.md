# Manuscript-to-result mapping

The results and reproducibility directories follow the figures, tables and sections of the final manuscript. The complete experiment index records workloads, input identities, available source and validation status. A saved measurement is a historical result; it does not by itself establish a new benchmark replay.

| Manuscript item | Result materials | Reproduction materials |
| --- | --- | --- |
| Figure 1: algorithm example | [Figure 1](../benchmark_results/figure1_algorithm/) | [Figure 1](../reproducibility/figure1_algorithm/) |
| Figure 2a: preencoded independent scoring | [Figure 2a](../benchmark_results/figure2a_independent_scoring/) | [Figure 2a](../reproducibility/figure2a_independent_scoring/) |
| Figure 2b: scoring and per-window selection | [Figure 2b](../benchmark_results/figure2b_window_selection/) | [Figure 2b](../reproducibility/figure2b_window_selection/) |
| Figure 3 / Table S5: runtime and sampling density | [Figure 3](../benchmark_results/figure3_runtime_density/) | [Figure 3](../reproducibility/figure3_runtime_density/) |
| Figure 4: bucket balance | [Figure 4](../benchmark_results/figure4_bucket_balance/) | [Figure 4](../reproducibility/figure4_bucket_balance/) |
| Table 1: segment layout | [Table 1](../benchmark_results/table1_segmentation/) | [Table 1](../reproducibility/table1_segmentation/) |
| Table 2 / Table S3: ntHash comparison | [Table 2](../benchmark_results/table2_nthash/) | [Table 2](../reproducibility/table2_nthash/) |
| Table 3 / Table S10: three-reference indexing | [Table 3](../benchmark_results/table3_minimap2_indexing/) | [Table 3](../reproducibility/table3_minimap2_indexing/) |
| Figure S1: thread scaling | [Figure S1](../benchmark_results/supplementary_s1_multithreading/) | [Figure S1](../reproducibility/supplementary_s1_multithreading/) |
| Table S1: XOR and odd multiplication | [Table S1](../benchmark_results/supplementary_s1_1_xor_odd/) | [Table S1](../reproducibility/supplementary_s1_1_xor_odd/) |
| Table S2: gxhash64 | [Table S2](../benchmark_results/supplementary_s1_2_gxhash/) | [Table S2](../reproducibility/supplementary_s1_2_gxhash/) |
| Tables S3–S4: ntHash and separate LTO sensitivity | [S2 results](../benchmark_results/supplementary_s2_nthash/) | [S2 workflows](../reproducibility/supplementary_s2_nthash/) |
| Table S5: runtime and density | [S3.1 results](../benchmark_results/supplementary_s3_1_runtime_density/) | [S3.1 workflow](../reproducibility/supplementary_s3_1_runtime_density/) |
| Table S6: full-length streaming | [S3.2 results](../benchmark_results/supplementary_s3_2_streaming/) | [S3.2 workflow](../reproducibility/supplementary_s3_2_streaming/) |
| Tables S7a–c: external SIMD A/B/C | [S3.3 results](../benchmark_results/supplementary_s3_3_external_simd/) | [S3.3 workflows](../reproducibility/supplementary_s3_3_external_simd/) |
| Table S8: repetitive-word selection | [S3.4 results](../benchmark_results/supplementary_s3_4_repetitive_words/) | [S3.4 workflow](../reproducibility/supplementary_s3_4_repetitive_words/) |
| Table S9: Alu controlled reads | [S3.5 results](../benchmark_results/supplementary_s3_5_alu/) | [S3.5 workflow](../reproducibility/supplementary_s3_5_alu/) |
| Tables S10–S12: Minimap2 integration | [S4 results](../benchmark_results/supplementary_s4_minimap2/) | [S4 workflows](../reproducibility/supplementary_s4_minimap2/) |

Figure 2a and Figure 2b use different timed work. Figure 3 uses materialized scores and a common selector; full-length streaming is a separate experiment. The three Minimap2 workflows respectively cover inline indexing, historical external-call mapping accuracy, and Human multithreaded indexing. Their source versions and repeats are not interchangeable. SIMD tasks A/B/C retain their own timing boundaries and output widths.

The historical `reproducibility/table2/` is an exhaustive 9-mer implementation check, not current Table 2 and not a general proof of bijectivity. Check each experiment README for input preprocessing, dependencies, timing boundaries, the availability of original measurements, and whether a portable entrypoint has actually been validated.

The [C=4–8 segment-cap diagnostic](../benchmark_results/c_segment_scan/README.md)
is additional material and is not assigned a Supplementary Information table
number. The associated [source and limitations](../reproducibility/supplementary_s2_nthash/c_parameter_scan/README.md)
are documented separately; Table S10 is the Minimap2 indexing table.

## Primary files

The following links identify a primary recorded result and a primary source or
protocol entry for each manuscript item. A protocol README is an entry point,
not a claim that every historical dependency or executable is distributed.
Consult each workflow for the exact build, inputs, timing boundary and status.

| Manuscript item | Primary result | Primary source or protocol entry |
| --- | --- | --- |
| Main Figure 1 | [Figure1_manuscript.png](../benchmark_results/figure1_algorithm/Figure1_manuscript.png) | [figure1_from_manuscript.drawio](../reproducibility/figure1_algorithm/figure1_from_manuscript.drawio) |
| Main Figure 2a | [figure2a_summary.csv](../benchmark_results/figure2a_independent_scoring/figure2a_summary.csv) | [phase1_benchmark.c](../reproducibility/figure2a_independent_scoring/phase1_benchmark.c) |
| Main Figure 2b | [figure2b_summary.csv](../benchmark_results/figure2b_window_selection/figure2b_summary.csv) | [benchmark_single_thread_realistic_kw.c](../reproducibility/figure2/benchmark_single_thread_realistic_kw.c) |
| Main Figure 3 | [figure3_summary_path_redacted.tsv](../benchmark_results/figure3_runtime_density/figure3_summary_path_redacted.tsv) | [kssd_score.c](../reproducibility/figure3_runtime_density/historical_source/kssd_score.c) |
| Main Figure 4 | [figure4_bucket_balance_summary.csv](../benchmark_results/figure4_bucket_balance/figure4_bucket_balance_summary.csv) | [benchmark_bucket_balance.c](../reproducibility/figure4/benchmark_bucket_balance.c) |
| Main Table 1 | [Table1_segmentation.tsv](../benchmark_results/table1_segmentation/Table1_segmentation.tsv) | [kssd_array.c](../src/kssd_array.c) |
| Main Table 2 | [table2_s3_all40.tsv](../benchmark_results/table2_nthash/table2_s3_all40.tsv) | [practical_nthash.cpp](../reproducibility/table2_nthash/frozen_worktree/reproducibility/reviewer_phase3/practical_nthash.cpp) |
| Main Table 3 | [table3_indexing_summary.csv](../benchmark_results/table3_minimap2_indexing/table3_indexing_summary.csv) | [README.md](../reproducibility/supplementary_s4_minimap2/inline_indexing/README.md) |
| SI Figure S1 | [s1_summary.csv](../benchmark_results/supplementary_s1_multithreading/s1_summary.csv) | [README.md](../reproducibility/figure3/README.md) |
| SI Table S1 | [hash_throughput_summary.csv](../benchmark_results/supplementary_s1_1_xor_odd/hash_throughput_summary.csv) | [hash_bench.cpp](../reproducibility/supplementary_s1_1_xor_odd/historical_source/hash_bench.cpp) |
| SI Table S2 | [gxhash_summary.tsv](../benchmark_results/supplementary_s1_2_gxhash/gxhash_summary.tsv) | [score_driver.c](../reproducibility/supplementary_s1_2_gxhash/historical_source/score_driver.c) |
| SI Table S3 | [table2_s3_all40.tsv](../benchmark_results/table2_nthash/table2_s3_all40.tsv) | [practical_nthash.cpp](../reproducibility/table2_nthash/frozen_worktree/reproducibility/reviewer_phase3/practical_nthash.cpp) |
| SI Table S4 | [lto_summary.csv](../benchmark_results/supplementary_s2_nthash/lto/lto_summary.csv) | [README.md](../reproducibility/supplementary_s2_nthash/lto/README.md) |
| SI Table S5 | [figure3_summary_path_redacted.tsv](../benchmark_results/figure3_runtime_density/figure3_summary_path_redacted.tsv) | [kssd_score.c](../reproducibility/figure3_runtime_density/historical_source/kssd_score.c) |
| SI Table S6 | [LOW_DENSITY_RESULTS.tsv](../benchmark_results/supplementary_s3_2_streaming/LOW_DENSITY_RESULTS.tsv) | [sampler.cpp](../reproducibility/supplementary_s3_2_streaming/historical_source/sampler.cpp) |
| SI Table S7a | [A_summary_path_redacted.tsv](../benchmark_results/supplementary_s3_3_external_simd/A/A_summary_path_redacted.tsv) | [rolling_score_benchmark.rs](../reproducibility/supplementary_s3_3_external_simd/historical_source/benchmark_driver/src/bin/rolling_score_benchmark.rs) |
| SI Table S7b | [B_summary_path_redacted.tsv](../benchmark_results/supplementary_s3_3_external_simd/B/B_summary_path_redacted.tsv) | [common_selector_benchmark.rs](../reproducibility/supplementary_s3_3_external_simd/historical_source/benchmark_driver/src/bin/common_selector_benchmark.rs) |
| SI Table S7c | [C_summary_path_redacted.tsv](../benchmark_results/supplementary_s3_3_external_simd/C/C_summary_path_redacted.tsv) | [end_to_end_benchmark.rs](../reproducibility/supplementary_s3_3_external_simd/historical_source/benchmark_driver/src/bin/end_to_end_benchmark.rs) |
| SI Table S8 | [fixed_summary_all.csv](../benchmark_results/supplementary_s3_4_repetitive_words/fixed_summary_all.csv) | [README.md](../reproducibility/supplementary_s3_4_repetitive_words/README.md) |
| SI Table S9 | [kernel_timing_summary.csv](../benchmark_results/supplementary_s3_5_alu/kernel_timing_summary.csv) | [read_mapper_four.cpp](../reproducibility/supplementary_s3_5_alu/read_mapper_four.cpp) |
| SI Table S10 | [table3_indexing_summary.csv](../benchmark_results/table3_minimap2_indexing/table3_indexing_summary.csv) | [README.md](../reproducibility/supplementary_s4_minimap2/inline_indexing/README.md) |
| SI Table S11 | [supplementary_s2_corrected_counts.csv](../benchmark_results/supplementary_s4_minimap2/mapping_accuracy/supplementary_s2_corrected_counts.csv) | [run_accuracy.py](../reproducibility/supplementary_s4_minimap2/run_accuracy.py) |
| SI Table S12 | [summary.tsv](../benchmark_results/supplementary_s4_minimap2/human_multithread/summary.tsv) | [README.md](../reproducibility/supplementary_s4_minimap2/human_multithreading/README.md) |
