# Historical S2 metric definitions

These definitions document the superseded evaluation only.

- Primary records were selected using the historical `samtools view -F 2308`
  equivalent, which excludes unmapped, secondary, and supplementary records.
- Global accuracy was correct mapped primary records divided by truth-matched
  mapped primary records. Unmapped/no-primary truth reads were absent from the
  denominator.
- Correctness required the stored truth reference and a position within ±5 bp
  of the reduced truth TSV offset. The historical reverse shortcut compared
  against `offset-(read_length-1)`; the TSV did not include ART strand or
  aligned-reference span.
- Repeat accuracy was computed from separate Original and KSSD repeat BAMs
  selected using each method's reported alignment coordinates. The two methods
  therefore did not necessarily use the same read-ID subset.
- MAPQ=60 fraction used mapped primary records as its denominator.
- Reported differences were 100 × (KSSD-Array proportion − Original Minimap2
  proportion), in percentage points.

The corrected analysis replaces these with an all-truth-read denominator,
official ART strand-aware genomic intervals, and one method-independent
truth-origin repeat subset.
