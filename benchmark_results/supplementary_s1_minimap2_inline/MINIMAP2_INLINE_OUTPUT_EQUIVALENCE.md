# Minimap2 public-inline output equivalence

Date: 2026-07-31 (Asia/Shanghai)

## Small fixtures

The public smoke suite passed index thread consistency, alignment thread
consistency, ambiguous-base reset, HPC behavior, and index compatibility in:

`$KSSD_FORMAL_RESULTS/minimap2-inline-smoke-20260731-214000`

The preserved external-call executable was then run against the same `k=9`,
`w=5`, single-thread fixture and compared with the new public-inline
executable.  Results are under:

`$KSSD_FORMAL_RESULTS/minimap2-inline-output-equivalence-20260731-214500`

- Serialized KSSD index: byte-identical,  SHA-256
  `8847e57566826919ccf49238131c46fcdab88f696f9ceb885441f79f58da6796`.
- Alignment PAF: byte-identical, SHA-256
  `59291b69d0bd038d94e2ee4cdac7e5d14db96b07333b4ef9957d062235119d56`.
- Deterministic statistics: 51 distinct minimizers, 17.65% singletons,
  4.745 average occurrences, 2.525 average spacing, total length 611.

Library-level value parity establishes equality of mapped values.  The
byte-identical serialized index establishes equality of the minimizer records
(including positions), counts, index size, and payload.  The identical PAF
establishes equal downstream alignment output.

## Human GRCh38.p14

The preserved current KSSD index was:

`$KSSD_FORMAL_RESULTS/minimap2-indexing-s1-20260728-v3/indexes/Human_GRCh38.mmi`

The validated public-inline executable built a new index with exactly the
preserved parameters (`k=15`, `w=10`, HPC disabled, one thread) in:

`$KSSD_FORMAL_RESULTS/minimap2-inline-human-equivalence-20260731-215000/results/Human_GRCh38.k15w10.inline.mmi`

Both files are 7,432,760,197 bytes.  Full-file `cmp` and payload `cmp -i 4`
both succeeded; no magic-header exception was needed.  Both SHA-256 values
are:

`34e4769552d1640604936a8db244fc1a3e7e4eae0f8a36a7c80bcf6a08d1e964`

The new run reported exactly 90,357,686 distinct minimizers, 35.37%
singletons, 6.354 average occurrences, 5.745 average spacing, 705 sequences,
and total length 3,298,430,636, matching the preserved result.

An earlier validation-only attempt in the same result directory explicitly
used `k=19`; it is retained and is not a mismatch at equal parameters, nor is
it part of any formal timing table.

## Result

**PASS — external-call and public-inline outputs are semantically and
byte-for-byte equivalent at equal parameters.**
