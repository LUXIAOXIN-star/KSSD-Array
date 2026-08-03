# Deterministic smoke-fixture generator

The six tiny FASTA, FASTQ, and BED smoke fixtures are generated from the public
C source in this directory. They are test inputs only; they are not manuscript
benchmark datasets and do not affect accepted scientific result values.

The historical shell history contains several `./a.out` invocations. The
recoverable source associated with the synthetic FASTA is `random.c`, which
generated the 300 Mb `AEEE.fasta` using wall-clock-seeded `rand()`. It did not
generate these six fixtures. Historical session records show that the four
original smoke FASTAs and the two corrected-S2 records were instead introduced
as explicit test data while their workflows were constructed. This generator is
therefore a documented deterministic reconstruction, not a claim that the
historical `a.out` was recovered as their source.

The C source expresses the accepted design as repeated motifs, named sequence
blocks, a substring probe, homopolymer runs, fixed S2 read names, and BED points
derived five bases inside the accepted truth intervals. The fixed seed `42` is
an interface/version guard; no runtime randomness is used. Keeping the design in
readable source avoids storing serialized fixture files or opaque binary data.

Generate into a clean directory outside the repository:

```sh
tests/fixture_generators/generate_test_fixtures.sh \
  --output-dir /path/to/empty/output --seed 42
```

The wrapper compiles a named temporary executable with
`cc -O2 -std=c11 -Wall -Wextra -Wpedantic`, deletes the temporary build on exit,
and verifies all six outputs against `expected_sha256.tsv`. `CC` may select a
different C11 compiler. Existing generated paths are never overwritten.

Run the generator unit tests with:

```sh
make fixture-generator-test
```

The tests cover clean generation, repeated byte identity, missing compiler,
invalid seed/arguments, and a deliberate expected-hash mismatch.
