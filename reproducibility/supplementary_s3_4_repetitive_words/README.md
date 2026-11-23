# Repetitive-word selection on yeast and Arabidopsis

## Manuscript reference and objective

Supplementary Section S3.4 and Table S8 evaluate whether the selected k-mer in a mixed-frequency window is high-copy. The [saved historical results](../../benchmark_results/supplementary_s3_4_repetitive_words/README.md) remain unchanged.

## Inputs and checksums

Supply the exact historical reference FASTA files, either the recorded gzip files or their uncompressed contents. The accession alone does not guarantee identical bytes.

| Input | Reference | gzip SHA-256 | Uncompressed FASTA SHA-256 |
| --- | --- | --- | --- |
| Yeast | Saccharomyces cerevisiae S288C R64, NCBI `GCF_000146045.2` | `1ec41f951b35f2752d5065edeafe6972455609d4383fb36dae12519a60b27a73` | `fe42735d3e6242f8c40b457a232940e34ef15eb4502717e54a34ed118face4c1` |
| Arabidopsis | Arabidopsis thaliana TAIR10.1, NCBI `GCF_000001735.4` | `a182f3c71662973dc636cacd7722588c9bbe3c8ea6ce62b1bae7dac940545d47` | `de99316d1d5597e9a5d40d943ff919c17d59b77116354a5d388b183b6f21075f` |

The historical byte identities and record metadata are in `historical_source/input_manifest.json`; the inputs are not distributed here. Obtain the reference assemblies from NCBI and check the actual bytes; a matching accession is not a guarantee that another download has the same file SHA-256. The runner verifies the gzip and decompressed identities before calculation.

## Parameters and interpretation

The primary condition uses k=21, w=20, strict canonical k-mers, leftmost ties, threshold τ=50 and frozen seed 42. The four methods are KSSD-Array (`kssd_repo`), XOR (`xor`), odd multiplication modulo 2^42 (`mul`), and odd multiplication modulo 2^64 (`mul64`). Global canonical k-mer frequencies are calculated from all records in each reference, including organelles; the eight Table S8 rows sum only nuclear records. The numerator is `n_avoidable_highfreq`, the number of mixed-frequency windows whose selected k-mer has frequency greater than 50; the denominator is `n_mixed_windows`. The reported percentage is 100 times the ratio of those integer counts.

## Build and run the primary condition

Requires Python 3.8 or newer, a C11 compiler, a C++17 compiler, GNU-compatible `ar`, and enough memory and disk to process the full references. The original program uses `-O3` and C11/C++17. All outputs, including compiled binaries, logs and intermediate reference-derived caches, are created below a new output directory outside the repository. Existing paths are never overwritten. Example from the repository root:

```sh
python3 reproducibility/supplementary_s3_4_repetitive_words/run_primary.py \
  --yeast /path/to/GCF_000146045.2_R64_genomic.fna.gz \
  --arabidopsis /path/to/GCF_000001735.4_TAIR10.1_genomic.fna.gz \
  --out /path/to/new-s8-output
```

The runner verifies input and frozen-source SHA-256, builds the unchanged historical `prepare.cpp` and `analyze.cpp`, checks that the generated seed-42 table is identical to the recorded k21 table, prepares global frequencies, and analyzes each reference record. It writes `results/primary_per_record.csv`, `results/table_s8_comparison.csv`, `run_manifest.json` and detailed logs. It checks every generated primary per-record row for the four methods, including all four original frequency thresholds, against the saved records, and checks the eight nuclear τ=50 results against the historical summary. `run_manifest.json` reports PASS only after all comparisons succeed. Timings, if present in logs, are diagnostic and are not benchmark results.

The runner invokes the following compiler and archive commands. In these
commands, `SRC` is `reproducibility/supplementary_s3_4_repetitive_words/historical_source`,
and `BUILD` is the output directory's `build` subdirectory:

```sh
gcc -O3 -std=c11 -Wall -Wextra -I"$SRC/production/include" -I"$SRC/production/src" -c "$SRC/production/src/kssd_array.c" -o "$BUILD/kssd_array.o"
gcc -O3 -std=c11 -Wall -Wextra -I"$SRC/production/include" -I"$SRC/production/src" -c "$SRC/production/src/permutation.c" -o "$BUILD/permutation.o"
ar rcs "$BUILD/libkssd_array.a" "$BUILD/kssd_array.o" "$BUILD/permutation.o"
for program in prepare analyze freeze; do
  g++ -O3 -std=c++17 -Wall -Wextra -I"$SRC/production/include" "$SRC/scripts/$program.cpp" "$BUILD/libkssd_array.a" -o "$BUILD/$program"
done
```

The primary condition has been rerun with the exact historical references in
an independent output directory. All 384 primary per-record rows and the eight
reported nuclear results matched the retained historical tables. This is not a
replay of the additional window-sensitivity phases.

`historical_source/` retains the original scientific sources and the actual historical `run_fixed.py`, `summarize_fixed.py`, and `reproduce.sh` byte-for-byte. The original scripts cover additional methods and w=10/50 sensitivity phases; their original summary requires the entire 2,016-row dataset. They write inside their working tree and should not be run directly in this repository. The separate `run_primary.py` is the path-portable primary-condition orchestrator and aggregator; it does not alter the original scientific source or recalculate historical results in place. Source hashes are recorded in `historical_source/SOURCE_SHA256.tsv`.

## Source and third-party notice

The retained production KSSD-Array source uses the included MIT license. The historical `common.hpp` also retains an unused Minimap2-style hash control and SplitMix64-style generator; see [third-party notices](../../THIRD_PARTY_NOTICES.md) for sources and license text, including Minimap2 v2.30 `sketch.c`. These controls are retained unchanged even though the four-method primary comparison does not call the Minimap2-style hash. The exact source package is not a claim of a fresh full sensitivity or performance replay.
