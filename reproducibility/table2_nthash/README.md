# Practical ntHash and KSSD comparison

Main Table 2 and Supplementary Section S2 / Table S3. [Results](../../benchmark_results/table2_nthash/README.md); input identities are in the [dataset guide](../../docs/datasets.md).

This package preserves the historical Phase3 scientific driver and fixed KSSD
and ntHash 2.4.0 sources byte-for-byte. ntHash's MIT license is in
`third_party/nthash/LICENSE`; its source commit is
`c26bd4572a19de81e30d55042dbd33c1fd21d4b6`. Source file checksums are in
`SOURCE_IDENTITIES.json`. The scientific driver, timer, seed, common selector and
output format are unchanged. The new `run_portable.py` is a separate launcher;
`oracle_small.cpp` is an independent, deliberately slow smoke-check oracle.

This is continuous DNA scoring followed by the same per-window selector, not a
preencoded scoring benchmark. The historical FASTA reader uses the first record,
removes non-ACGT characters and concatenates the remaining bases. It does not
implement the boundary-breaking streaming protocol. Scores are materialized;
selector output is one value for every window, without consecutive deduplication.

A small input check, with an expected SHA-256 supplied by the caller, builds the
k=21 program and the oracle in a **new external directory**, validates the
original program's fixture, and compares score counts, window counts and all
three KSSD and ntHash checksums with the independent per-k-mer/brute-window
oracle. It is not a formal performance experiment:

```sh
python3 -B reproducibility/table2_nthash/run_portable.py \
  --mode smoke --input /path/to/small.fa --input-sha256 <sha256> \
  --cpu <allowed-logical-cpu> --out /path/to/new-output
```

Use different directories for input and output. Existing outputs, an invalid
hash, an output in the input directory or source tree, or an unavailable CPU
are rejected before building. Failed builds leave their partial logs in place.
For every run, `run_manifest.json` records input/source hashes, compiler version,
flags, actual commands and exit codes; `logs/` retains stdout and stderr.
The KSSD and ntHash sources, C/C++17 compiler, `ar`, zlib development library,
Python 3 and `taskset` are required. The recorded build uses
`-O3 -march=native -DNDEBUG` with C11 or C++17; native CPU compatibility is a
prerequisite. The original build used GCC 9.4.0; a different local compiler is
recorded and can affect performance.

The explicit `--mode formal` processes the two exact original FASTA files in
40 conditions (k 15/19/21/24/31 and w 5/10/20/50, random order seed 42). Each
condition is one process with five paired **technical repeats**, not five
independent processes. It checks the exact historical FASTA SHA values, builds
five binaries in the new output, executes the original per-k validation, and
preserves raw method records, checksums and logs. It does not run automatically:

```sh
python3 -B reproducibility/table2_nthash/run_portable.py \
  --mode formal --synthetic /path/to/exact-300Mb.fa \
  --human /path/to/exact-GRCh38.p14-genomic.fa \
  --cpu <allowed-logical-cpu> --out /path/to/new-formal-output
```

**Status:** the relocated package passed an isolated k21/w20 small-input test against its direct-score and naive-window oracle; it has not been fully replayed;
the complete 40-condition grid was not rerun here and remains
`NOT_FULLY_REPLAYED`. This wrapper does not reproduce the accompanying separate
C-sensitivity campaign or its full historical resource scheduler.
