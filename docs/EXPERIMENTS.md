# Experiment and reproducibility guide

This guide maps the manuscript figures and tables to the retained source,
inputs and saved measurements. The protocols are distinct experiments: their
preprocessing, timer, output and statistical units must not be combined. A
saved measurement, a command in a build record, and a newly verified complete
replay are different kinds of evidence. Full performance campaigns were not
rerun while preparing this guide.

Start by checking [dataset identities and acquisition](datasets.md), [software
dependencies](dependencies.md), [third-party notices](../THIRD_PARTY_NOTICES.md),
and the experiment-specific records linked below. Full inputs and indexes are
external. Use a new output location and keep the frozen measurements unchanged.
The historical commands in manifests preserve their original working paths and
should be treated as execution evidence; their presence does not prove that
the commands will work unmodified on another machine.

The 300-Mb synthetic FASTA can be reconstructed using the [fixed-seed input
recipe](../reproducibility/data_generation/synthetic_300M/README.md). Its legacy
header is retained for byte identity and is not a claim of biological origin.
For several Figure 2 and ntHash workflows the first chr1 record is uppercased,
non-ACGT characters are deleted and the remaining bases are concatenated; this
can create k-mers across deleted intervals. The streaming workflow instead
retains ambiguous-base boundaries. Minimap2 processes separate reference
records and resets at ambiguous bases. Individual input manifests define the
accepted checksums and coordinates.

## Independent preencoded scoring — Figure 2a

This experiment compares KSSD-Array with inline XXH3/XXH64 0.8.3,
MurmurHash3 and wyhash on synthetic 300 Mb and processed GRCh38.p14 chr1.
For k=16,19,21,24,31, five measurements per method condition generate the
250 saved records. Timing traverses preencoded uint64 k-mers, computes a
score and accumulates a checksum; it excludes sequence encoding and window
selection. Throughput is million scores/s; arithmetic means and sample SDs
are calculated from individual rates.

The [independent-scoring workflow](../reproducibility/figure2a_independent_scoring/README.md) describes the historical driver identity, dependencies, compiler and a separately isolated launcher. The historical driver and its licensed third-party components are present in that workflow; the launcher checks the historical source SHA. [Saved measurements](../benchmark_results/figure2a_independent_scoring/README.md) include all retained observations. A k=21 small input was validated; the full experiment has not been replayed. The k=31 results in which other methods are faster remain in the data.

## Scoring and per-window minimum — Figure 2b

The same five families are compared on the two preencoded inputs, at k=16,
19,21,24,31 and w=10,20,50, with five recorded repeats. The timer includes
scoring and the original per-window minimum/rescan implementation, not DNA
encoding. Every window contributes a result; adjacent winners are not
deduplicated. It is not a read-mapping or common-deque experiment.

The [score-and-window workflow](../reproducibility/figure2b_window_selection/README.md) documents the historical source identity, shared xxHash dependency and separately isolated launcher; the published historical benchmark source is checked against its recorded SHA. [Saved measurements](../benchmark_results/figure2b_window_selection/README.md) are available. A small condition was checked without running the full grid.

## Thread scaling — Supplementary Figure S1

The [OpenMP source and workflow](../reproducibility/figure3/README.md) and
[saved measurements](../benchmark_results/figure3_multithread/) use both
inputs, k=21, w=10,20,50, and requested threads 1,2,4,8,16. There are five
measurements for each input/parameter/method condition. The original score
and window rescan timer excludes encoding and includes the threaded work and
its recorded checksum reduction. The GCC 9.4 manifest records `-O3
-march=native -fopenmp`; actual worker-count checks are saved with the raw
data. The exact release of the thread experiment's dynamic xxHash library is
not established by its own record. Do not replace these data with Figure 3's
speed-density experiment or Minimap2 thread timings. Historical complete
performance replay is not newly verified.

## Runtime and density — Figure 3 and Supplementary Table S5

The [saved figure](../benchmark_results/figure3_runtime_density/README.md) and
[reproduction workflow](../reproducibility/figure3_runtime_density/README.md)
compare KSSD-Array, seq-hash and GreedyMini-derived prefix12 with the same
forward-only leftmost selector on two 10-Mb inputs at k=21/31, w=20. The human
input is NC_000001.11 `[2746290,12746290)`; the synthetic 10-Mb input uses its
own fixed SplitMix64 seed and is not a prefix of the 300-Mb input. Input
hashes and the generation recipe are in the experiment package.

Each condition has a warm-up and five independent measured processes. The
timer begins with loaded DNA and includes conversion, scoring, window selection
and retained position output. Counts are selected positions, and density is
positions divided by valid k-mer starts. The package records GCC/G++ 9.4,
`-O3 -march=native`, Rust/Cargo 1.98.1 and its actual link settings. The
package includes partial historical sources and a plotting script. The complete
benchmark runner and some external dependencies are not included. Historical
saved-data redraw checks do not establish a complete cross-machine benchmark. GreedyMini
prefix12 is a derived order, not a target-k native trained order.

## Bucket balance — Figure 4

The [bucket workflow](../reproducibility/figure4_bucket_balance/README.md), [raw data and
build/command records](../benchmark_results/figure4_bucket_balance/) cover
4-Mb and 8-Mb deterministic random sequences, k=6–14, B=101/199/499 and
100 generated sequences per condition. The 27,000 individual tests yield
270 summaries; the displayed value is the percentage with p>0.05, not proof
of uniformity. The historical C build used GCC 9.4 with `-O3 -march=native`
and a shared xxHash link; its exact historical source identity and commands
are documented in the workflow; the archived source and current public source have different SHA values.

The current C source differs from the archived built source in attribution
comments and `Wyhash`/`wyhash` label capitalization; the RNG, scoring, bucket
and test loops do not differ in the checked source. The archived source and the compiled binary have separate identities. The isolated workflow requires the original source SHA; a small input was checked, but a fresh full performance campaign has not been performed here.

## Segment-cap comparison — main methods and results

The [segment-cap source and build guide](../reproducibility/supplementary_s2_nthash/c_parameter_scan/README.md)
and [saved C-scan results](../benchmark_results/c_segment_scan/) compare C=4–8
at k=16,19,21,24,31 on the two full inputs. The score-only, common-window and
initialization records are separate; window settings are w=10,20,50. The
25 structural configurations are additional diagnostic data and are not
assigned a Supplementary Information table number. Table S10 instead covers
Minimap2 indexing. The recorded build uses GCC 9.4, `-O3 -march=native`, and fixed KSSD permutation
seed 42. Run ordering, stage boundaries, repetitions and exact compiler
commands are specified in the frozen package. Geometric means across input or
window conditions are not replicate mean±SD. A complete portable C-scan runner
is not included, and no fresh complete campaign is claimed.

## gxhash64 — Supplementary Table S2

The [gxhash package](../reproducibility/supplementary_s1_2_gxhash/README.md)
compares KSSD, inline XXH3 0.8.3 and gxhash64 3.5.0 on the same preencoded
uint64 arrays from the two full inputs, at k=16,19,21,24,31. Five independent
measured processes follow a separate warm-up for each method/condition.
Each 8-byte key is scored once per pass and incorporated in a checksum;
DNA encoding, file I/O and window selection are excluded. Historical GCC 9.4
and Rust/Cargo 1.98.1 were recorded in the historical build; the complete fixed source and dependency package is not distributed in this directory. The result package contains all formal measurements, including slower repeats, in a path-tokenized derived table.
The historical implementation made one cross-language call per array, not per key. Complete
replay requires exact inputs and locked dependencies; a saved-data check is not
a fresh performance result.

## ntHash comparison — main Table 2 and Supplementary Table S3

The [frozen source and portable-interface guide](../reproducibility/table2_nthash/README.md)
documents KSSD and ntHash 2.4.0 (`c26bd457...`), both full inputs, k=15,19,
21,24,31 and w=5,10,20,50. Each of the 40 conditions uses five **paired
technical repeats within a process**. The score stage starts from cleaned
DNA and includes rolling scoring and score-array writes; the common leftmost
deque selection is a second timed stage. Parsing, initialization and allocation
are outside the corresponding timers. Its output is per-window winners rather
than deduplicated density.

The package records GCC 9.4 `-O3 -march=native`, the original build commands,
source hashes and external input identities; [saved measurements and
tables](../benchmark_results/supplementary_s2_nthash/primary/)
and the existing table-checking script retain five individual throughput
rates. A paired-ratio confidence interval is not a throughput SD. The earlier
k=w scan is a different experiment. A k=21/w=20 small input passed an independent oracle check; the full 40-condition replay has not been performed.

## LTO OFF/ON validation — Supplementary Table S4

The [saved LTO package](../reproducibility/supplementary_s2_nthash/lto/README.md)
retains a separate 80-process campaign over the same two inputs, 40 k/w
conditions and five within-process paired technical repeats. Historical GCC
11.4 builds use `-O3 -march=native -DNDEBUG`, OFF `-fno-lto`, ON `-flto` on
the scientific translation units and final links. Path-redacted historical raw data are retained separately in the [result directory](../benchmark_results/supplementary_s2_nthash/lto/). The complete public runner and dependencies are not assembled; it is not a self-contained cross-machine replay. Small correctness validation and a full performance
replay are separate operations; a full grid must not be started implicitly.

## Full-length streaming — Supplementary Table S6

The [streaming package](../benchmark_results/supplementary_s3_2_streaming/README.md)
retains KSSD, GreedyMini-derived prefix orders and mod-minimizer on synthetic
300 Mb and full chr1. Human input retains ambiguous characters as boundaries:
each contiguous A/C/G/T run is handled separately. Ten unique k/w points per
input are measured, with a duplicate `(31,20)` confirmation retained as a
separate slot. One warm-up and five technical traversals occur within each
process; 330 raw timings include the confirmation. `LOW_DENSITY_RESULTS.tsv`
reports median time, selected positions and density per valid start. The
recorded mod-minimizer fallback conditions remain identified.

GCC 9.4 C, G++ 11.4 C++20, Rust/Cargo 1.98.1, source versions, locks,
original build commands and inputs are documented with the package. Scoring,
streaming window selection and position writes are timed; input reading and
reusable setup are excluded. The complete historical launcher and dependencies are not included. Any
saved-data redraw or reaggregation is a separate operation, not a new
performance run.

## External SIMD A/B/C — Supplementary Tables S7a–S7c

The [external SIMD package](../benchmark_results/supplementary_s3_3_external_simd/README.md)
retains two fixed 10-Mb A/C/G/T inputs and 200 measurements. A compares
DNA-to-score generation for k=21/31 with no window; B adds a common selector
for w=20/50; C compares complete implementations for the same k/w. Each
condition has five independently measured processes. The historical parser
rejects non-ACGT input; the two actual inputs contain none. A, B and C have
different output and timing scopes and must be interpreted separately.

The recorded build uses GCC 9.4 `-O3 -march=native` and Rust/Cargo 1.98.1
release settings. KSSD uses full 2k-bit scores; A/B standalone seq-hash uses
full 32-bit scores; native simd-minimizers C ranks with the upper 16 bits.
B/C use the recorded weak-canonical configuration. Partial author source and Cargo lockfiles are retained in the [reproduction materials](../reproducibility/supplementary_s3_3_external_simd/README.md); some exact dependencies and source provenance remain unresolved. The actual 200-measurement
campaign used the historical launcher `execute.py --phase measure`; its SHA-256 is
`69424a197727c108233f7a140dd165abded6daf539d1c6d2fd8baa6cad45dfb6`.
The historical launcher is not distributed here, and a portable full-run
command has not been verified. The tables report
median with sample SD, while some saved plots report mean with SD. Source
subsets have outstanding version-specific third-party license checks, and
full cross-machine replay remains unverified.

## Reversible score controls — Supplementary Table S1

The [score-control package](../benchmark_results/supplementary_s1_1_xor_odd/README.md)
contains KSSD, XOR and odd multiplication modulo 2^42/2^64 on the 79,246,416
valid canonical 21-mer occurrences of UCSC hg38 chromosomes 21 and 22. It
retains full-stream and separate scalar/private-cache diagnostics. The
historical Xeon GCC 9.4 C++17 build and CPU settings are recorded with the
package. The principal reported values are median/min/max CPU time across 24
technical observations, not independent biological samples. Full stream
output writes are timed and checksum work is outside that interval. The
original input, executable and orchestration records are distinct from the
five-method Figure 2 scoring program; exact external input/replay material is
required for a full reproduction.

## Repetitive-word selection — Supplementary Table S8

The [saved records](../benchmark_results/supplementary_s3_4_repetitive_words/README.md)
cover yeast S288C R64 and Arabidopsis TAIR10.1, k=21, w=20 and a high-copy
threshold greater than 50. Frequency counting uses every reference FASTA
record, including organelles; the reported mixed-window denominators use
nuclear records only. The [reproduction notes](../reproducibility/supplementary_s3_4_repetitive_words/README.md) identify the historical workflow and external reference requirements. Per-record counts and denominators are retained in the result directory; they are not timing repeats. The standalone counting program is not distributed.

## Controlled Alu placement — Supplementary Table S9

The [controlled placement results](../benchmark_results/supplementary_s3_5_alu/README.md)
and the [historical mapper](../reproducibility/supplementary_s3_5_alu/read_mapper_four.cpp) preserve
KSSD, XOR, Bare42 and Bare64 on 3,349 AluSx and 2,929 AluJb 150-bp unmutated
reads from UCSC hg38 chr21/22, with k=21/w=20 and no substitutions. Table S9
uses the `unfiltered` frequency policy; `copycap1000` is a separate control.
Candidates require two distinct
seed words and full-read Hamming checks. The exact source locus is excluded
from alternative candidate counts, whereas off-target seed pairs use a source
interval rule. The original 2026-10 Xeon timing comprises eight technical
cycles of four sweeps; it is not the separate later SIMD/1% substitution
experiment or a full Minimap2 mapping result.

Saved timing and aggregate workload tables and the original C++ source are retained; complete external build and input dependencies remain to be assembled. Exact references, reads, index arrays and
the frozen external evidence bundle must be obtained and verified for a full
replay; their availability and redistribution terms are not established by a
local pathname. Preserve all ordinary-sequence, other-repeat and filtering
controls, including less favorable measurements.

## Single-thread Minimap2 indexing — main Table 3 and Supplementary Table S10

The [indexing workflow](../reproducibility/minimap2/indexing/README.md) and
[saved indexing package](../benchmark_results/supplementary_s4_minimap2/inline_indexing/README.md)
compare unmodified Minimap2 2.30-r1287, commit `79c9cc1...`, with the
KSSD-inline integration on complete Arabidopsis, GRCh38.p14 and maize B73
references. The historical k=15, w=10, homopolymer compression off, one-thread
campaign used one warm-up pair followed by five paired measurements per
reference. The process-level timer includes reading, parsing, initialization,
index construction and writing. The Minimap2 program recorded GCC 9.4 `-O2`;
the complete historical KSSD library flags are not independently recovered.

Raw wall/CPU records, RSS and index sizes are retained in the linked results; inputs, the exact patch and the complete build environment must be verified separately. Distinct minimizer keys
are not selected-position counts; mean spacing is defined as reference length
divided by occurrence count. Exact full references and tools must be supplied
externally. Current-machine complete performance replay is not claimed.

## Simulated-read accuracy — Supplementary Table S11

The [truth-origin evaluation guide](../reproducibility/minimap2/alignment_consistency_truth_origin/README.md),
[input-generation guide](../reproducibility/data_generation/supplementary_s2/README.md)
and [saved accuracy records](../benchmark_results/supplementary_s4_minimap2/mapping_accuracy/README.md)
use human and maize single-end 100/150-bp ART 2.5.8 reads, HS25, seed 42, and
an older external-call KSSD integration. The retained corrected analysis uses
existing BAMs and strand-aware ART truth; a primary mapping must match the
truth reference, strand and position within 5 bp. All reads form the all-read
denominator; paired bootstrap confidence intervals are retained separately.
Input references, reads, truth and BAMs are external. The existing evaluation
does not constitute a new alignment with the later inline indexing version.

## Multithreaded Minimap2 indexing — Supplementary Table S12

The [independent Human indexing package](../benchmark_results/supplementary_s4_minimap2/human_multithread/README.md)
compares original Minimap2 with the inline integration on the complete Human
reference, k=15/w=10 and homopolymer compression disabled. Requested threads
are 1,4,8,16; one warm-up and three independent process measurements per
method/thread setting are retained. Original and KSSD builds recorded GCC 9.4 `-O2`; all 24 formal and eight warm-up records are retained as path-tokenized derived tables. The process timer includes input, indexing and MMI writing;
actual active worker counts were not recorded. It is not an isolated-score
scaling or read-mapping benchmark. Full external references and sufficient
workspace are needed for a new execution, which has not been performed here.
