# Manuscript reproducibility environment

This document records the manuscript environment information that is known
for the public reproducibility workflows. It does not infer unrecorded tool
versions from the machine on which the repository is later inspected.

## Manuscript and repository identity

- Manuscript version: `KSSD-Array_Wiley_Manuscript_V5`
- Historical environment baseline commit:
  `0e0a64b3f97595c6ae2395f740f18d177324c41d`
- Historical release: `v1.0.0-paper`

This identity is retained only to describe the historical environment. Current
accepted result/source bindings are authoritative in
`../benchmark_results/source_binding.tsv`.

## Benchmark host

- OS: Ubuntu 20.04 LTS
- CPU: Intel Xeon Silver 4216

## Compilers

Compiler identities are recorded separately in the build manifests where available. The original score/window and bucket-balance builds record GCC/cc 9.4.0; other experiments use their own recorded compiler and settings. The workflows select the
C compiler through `CC` (default `cc`) and the C++ compiler through `CXX`
(default `c++`). Workflow-generated build manifests record the selected
compiler's `--version` output when a run is performed.

The core library requires C11. Table 4 requires C++17. The historical multithread workload (Supplementary Figure S1) requires compiler-supported OpenMP.

## Compiler flags

- Core Make build: `-Iinclude -O2 -std=c11 -Wall -Wextra -Wpedantic`.
- Historical Figure 2b: `-O3 -march=native -std=c11 -Wall -Wextra -Wpedantic`, plus
  compile-time `K` and `W`; system `libxxhash` is dynamically linked.
- Supplementary Figure S1: the historical Figure 2b flags plus `-fopenmp`; system `libxxhash`, zlib, and
  the OpenMP runtime are dynamically linked.
- Legacy matched-workload ntHash program: `-O3 -march=native -std=c++17 -Wall -Wextra -Wpedantic`, plus
  compile-time `K` and `W`; the prepared ntHash library and zlib are linked.
- Figure 4: `-O3 -march=native -std=c11 -Wall -Wextra -Wpedantic`; system
  `libxxhash` is dynamically linked.
- Supplementary Minimap2 workflow: the recorded integration build flags are
  `-g -Wall -O2 -Wc++-compat`.

The main Figure 3 runtime/density experiment and current Table 2 ntHash comparison use separate implementations and build records. The LTO OFF/ON sensitivity experiment is a separate GCC 11.4.0 campaign. The benchmark flags above are taken from the corresponding Makefile and
workflow runner commands. Generated manifests retain the complete compiler
command for each run.

## Pinned and system dependencies

- ntHash: version 2.4.0, commit
  `c26bd4572a19de81e30d55042dbd33c1fd21d4b6`.
- Minimap2: version 2.30-r1287, commit
  `79c9cc186b95f50bd899f69b48eba995ced810c6`.
- xxHash: system-provided xxHash library. The historic Figure 2b and Figure 4 runtime records identify 0.7.3 in the checked experiments; do not assign that version to a different experiment without its own build record.

## Result and artifact scope

Only small deterministic fixtures are committed with workflow source. Compact
accepted CSVs, figures, reports, and manifests are included under
`benchmark_results/`. Large reference datasets, generated binaries, full
logs, indexes, alignments, and per-read diagnostics remain external. Formal
workflows require caller-provided inputs and an explicit output directory
outside the repository.
