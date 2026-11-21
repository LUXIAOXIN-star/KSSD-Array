# Actual Phase3 practical ntHash and segmentation-cap experiments

This source package corresponds to the completed run
`reviewer-phase3-20260819-160839`.
The two scientific source files and original runner are copied unchanged from
that run's frozen `source_support/`; the core KSSD and ntHash source hashes match
the actual historical build manifest. Supporting headers/licenses are additionally
checked against the recorded upstream commits. No old binary is reused.

The new files `phase3_adapter.py`, `build_local.py` and `run_benchmark.py` only
wire local source/input/output locations. They do not change the C/C++ algorithms,
scientific loops, compiler flags, samples, seeds, constants, tie rules or timers.
`FROZEN_SOURCES.json` binds every copied scientific source to its original path
and SHA256; `ADAPTER_SHA256.json` identifies the new interface separately.

## Fixed experiment

- Practical ntHash: two inputs×k15/19/21/24/31×w5/10/20/50 =40 input/parameter
  points, two methods and five paired repetitions =400 raw method records.
- C scan: k16/19/21/24/31 and C4/5/6/7/8;250 mapping records,750 score+window
  records(w10/20/50),250 initialization records(ten per k,C), and25 structural
  configurations.
- KSSD RankDerived, seed42, SplitMix64, descending Fisher–Yates with modulo
  bounded sampling; ntHash2.4.0 commit
  `c26bd4572a19de81e30d55042dbd33c1fd21d4b6`.
- One thread on the original fixed CPU15; task-order seeds42 and4242; all
  original warmups/repetitions, strict resource checks and timing logic retained.
- Synthetic input retains300,000,000 bases. The human FASTA container uses the
  original first-record loader with230,481,012 retained A/C/G/T bases. Full input
  SHA256 values remain fixed; non-ACGT handling follows the original programs.

The practical score interval includes rolling encoding, score generation and
score materialization. Its total interval adds the shared window stage. This is
not a mapping-only encoded-key comparison, and every-window outputs are not
adjacent-deduplicated minimizer density. Score/s and window/s use their respective
original denominators. C-scan stages and memory/init accounting remain as defined
by the frozen C program. Repetitions are timing repetitions on fixed inputs.

## Prepare and build

Requires Python3.9+, a GNU-compatible C/C++17 toolchain, ar, zlib development
headers/library, taskset, vmstat and standard Linux inspection commands. Historical
cc/c++ were GCC9.4.0; actual commands are preserved in
`historical_provenance/build_manifest.json`. New builds retain-O3/-march=native
and the original language/debug/warning flags. Native binaries require a suitable
local CPU. Dependencies are local source files; no download is performed.

```bash
python3 build_local.py --out /absolute/path/to/new-phase3-build
```

The output directory must not exist and must be outside this frozen source
package. The helper verifies bundled SHA256 values, then calls the original
runner's `build()` function. It generates30 local binaries and a new build/log
manifest. The generated manifest's `head`/`branch` labels are original runner
constants; `REPLAY_ADAPTER.json` explicitly distinguishes them from actual Git
metadata. No private branch or tag is required.

## Validate and run the unchanged finite matrix

```bash
python3 run_benchmark.py \
  --build-root /absolute/path/to/new-phase3-build \
  --out /absolute/path/to/new-phase3-results \
  --synthetic /path/to/the/frozen/AEEE.fasta \
  --human /path/to/the/frozen/GCF_000001405.40_GRCh38.p14_genomic.fna
```

Input path overrides only relocate the same files: their complete FASTA SHA256
values must match. Omitting these two arguments uses the original recorded
paths. Inputs are not distributed in this lightweight source package. New output
must not exist and must be outside the source package. The build source location
must remain unchanged after building.

The helper checks source/binary/input identities, calls the **unchanged**
`validate()`, `formal()`, `parse_formal()` and `summarize()` functions and records
every command/log under the new output. Original correctness checks include the
five practical score/window validations,25 component-table checks, C8/public
seed42 agreement, and the included small Phase2 checksum table. Original private
Git-branch/tag checks and prior-report existence checks are replaced by the
bundled content identities; scientific validation is retained.

CPU15 must be in the assigned CPU set. The original preflight requires at least
40GiB available memory, low load, no active swapping and no heavy competing
process. These checks are intentionally not weakened for portability. The
original fixed CPU governor inspection path is retained. If prerequisites or
correctness fail, preserve the new output/logs and report the error; this wrapper
has no retry/recovery interface that changes samples or replaces timings.

## Scope of packaging validation

During publication packaging, only static source/AST checks, local link checks
and the two helpers' `--help` interfaces were exercised. No compilation,
validation binary, full experiment, bootstrap analysis or new timing was run.
Consequently this is a source-complete, statically checked location adapter,
**not a claim of a completed cross-machine replay**. Current saved experimental
values remain the historical measurements. New timing can only be claimed after
an explicit execution of the commands above and its successful new validation.

KSSD's license is in `frozen_worktree/LICENSE`; ntHash's official MIT license is
in `third_party/nthash/LICENSE`. Official primary source and licenses are included;
compiled objects, dependency caches, full inputs and old binaries are omitted.
