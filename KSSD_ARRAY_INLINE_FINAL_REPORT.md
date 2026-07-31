# KSSD-Array public runtime-inline final report

Date: 2026-07-31 (Asia/Shanghai)

## Outcome

The historical inline extraction/lookup/recombination idea was ported into the
current public KSSD-Array ownership and table model without importing the
historical global-state or initialization design.  The resulting API supports
all current `k=1..32`, and the pinned Minimap2 integration uses it directly in
`mm_sketch`.

- Development worktree: the isolated `KSSD-Array-inline-development`
  checkout.
- Branch: `feature/public-runtime-inline-api`.
- Baseline: `8922a3031a7ad327cbcac6f1e80748dff654537b`.
- Proposed release tag: `v1.1.0`.
- Original worktree status/diff record: `ORIGINAL_WORKTREE_STATE.md`.
- Manuscript edits: none.
- Historical result deletion/overwrite: none.

## Acceptance results

1. Library equivalence: **PASS**.  Generic and runtime-inline mapping matched
   for both RNG modes and every k, including exhaustive `k=1..9`, fixed and
   boundary vectors, and 100,000 deterministic random values per k/RNG.
   ASan and UBSan passed.  See `INLINE_API_EQUIVALENCE_REPORT.md`.
2. Final executable assembly: **INLINE PATH CONFIRMED**.  The formal S1
   executable's `mm_sketch` has direct `uint16_t` table loads and no call to
   `mm_kssd_array_map_unchecked` or `kssd_array_map_unchecked`; LTO was not
   enabled or claimed.  See `MINIMAP2_INLINE_ASSEMBLY_REPORT.md`.
3. Output equivalence: **PASS**.  Small-fixture index and PAF outputs were
   byte-identical between the preserved external-call executable and the
   public-inline executable.  The GRCh38.p14 index was fully byte-identical at
   `k=15,w=10`: 7,432,760,197 bytes, SHA-256
   `34e4769552d1640604936a8db244fc1a3e7e4eae0f8a36a7c80bcf6a08d1e964`.
   See `MINIMAP2_INLINE_OUTPUT_EQUIVALENCE.md`.
4. Existing benchmark impact: Figure 2, matched-workload Table 4, and Figure 3
   timed sources are unchanged from the baseline.  No rerun is required.  See
   `EXISTING_BENCHMARK_IMPACT.md`.

## Completed Supplementary S1 run

Result directory:

`$KSSD_FORMAL_RESULTS/minimap2-indexing-s1-inline-final-20260731-214500`

The package contains 6 discarded warm-ups, 30 accepted measured runs, and 15
complete pairs across Arabidopsis, Human GRCh38.p14, and maize.  The method
order alternated, runs were sequential and single-threaded on the configured
CPU, and every method/dataset repeat produced a deterministic within-method
index hash.  Eight attempts rejected by the preset swap-activity gate are
retained in `INVALID_MEASURED_ATTEMPTS.tsv`; they are not hidden or counted as
accepted measurements.

| Dataset | Original mean +/- sample SD (s) | Inline KSSD mean +/- sample SD (s) | Median paired KSSD/Original | Direction | Formal classification |
|---|---:|---:|---:|---:|---|
| Arabidopsis thaliana | 8.730301 +/- 0.047865 | 8.245624 +/- 0.073533 | 0.942250 | faster 5/5 | KSSD faster |
| Human GRCh38.p14 | 173.975028 +/- 0.101788 | 175.828929 +/- 0.083927 | 1.010775 | slower 5/5 | Inconclusive/comparable |
| Zea mays | 131.287672 +/- 0.049634 | 129.625545 +/- 0.047048 | 0.987150 | faster 5/5 | Inconclusive/comparable |

The final report, raw/summary/paired CSV files, final table and PNG/PDF figure,
input/executable/output hashes, environment, commands, and build/run manifests
are all present in that result directory.  The final integrated executable
SHA-256 is
`29da38889c244e97a902e476d1957172b9a0f726c5cb56285f6d49745b714b54`.

## Release recommendation

After the final repository checks and commit pass, tag that validated commit
as `v1.1.0`.  The tag is recommended here but is not created automatically.
