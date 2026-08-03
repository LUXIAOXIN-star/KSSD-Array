# Corrected Supplementary Table S2 truth-origin workflow

This workflow recalculates Supplementary Table S2 from the accepted Original
Minimap2 and KSSD-Array BAM files. It does not run Minimap2. It preserves the
historical evaluator under `../alignment_consistency/` and first proves that
the historical parser definitions reproduce all 12 accepted displayed
deltas.

## Why this workflow exists

The historical table conditioned global accuracy and MAPQ on truth-matched
mapped primary records. It selected repeat alignments independently for each
method from reported BAM coordinates. Its reduced truth TSV also omitted ART
strand and interpreted the retained coordinate with a forward/reverse-offset
shortcut.

The corrected primary analysis instead:

- keeps every simulated truth read in the global denominator;
- counts an unmapped or missing primary assignment as incorrect;
- excludes secondary and supplementary records from primary assignment;
- reconstructs genomic truth from the retained ART `.aln` strand, reference
  length, and ungapped aligned-reference span using ART's bundled official
  `aln2bed.pl` conversion;
- requires truth reference and strand plus a SAM position within 5 bp;
- assigns repeat membership once from truth-origin interval overlap of at
  least one base and uses the same IDs for both methods;
- computes paired read-level differences, 10,000 seed-42 bootstrap resamples,
  and exact two-sided McNemar tests.

The Human repeat BED annotates the 25 assembled chromosomes. ART also sampled
alternate and unlocalized scaffolds that are absent from that BED; those reads
are counted explicitly and receive no repeat annotation. Zea mays reference
names have complete BED coverage.

## Inputs

`config.json` pins the two references, two repeat BEDs, four FASTQs, four
reduced truth TSVs, four ART ALN truth files, and the ART semantics sources by
size and SHA-256. The accepted historical directory supplies eight global and
eight historical reported-repeat BAMs. Every BAM must match the historical
hash inventory and pass `samtools quickcheck`.

The seven-read FASTQ and two-row BED used only by the unit tests are generated
from `tests/fixture_generators/fixture_generator.c` in a temporary directory and
verified against the public expected-hash manifest. They are not formal S2
inputs and are not committed as generated data.

## Run

Use a new empty or dedicated result directory; do not point this workflow at
the historical accepted directory.

```sh
WORKFLOW=reproducibility/minimap2/alignment_consistency_truth_origin
ACCEPTED=/external/KSSD-Array-formal-results/minimap2-alignment-s2-20260728-v1
OUTPUT=/external/KSSD-Array-formal-results/minimap2-alignment-s2-corrected-TIMESTAMP

python3 "$WORKFLOW/audit_truth_schema.py" \
  --config "$WORKFLOW/config.json" \
  --data-root /external/data-root \
  --accepted-dir "$ACCEPTED" \
  --output-dir "$OUTPUT"

python3 "$WORKFLOW/run_corrected_s2_metrics.py" \
  --config "$WORKFLOW/config.json" \
  --data-root /external/data-root \
  --accepted-dir "$ACCEPTED" \
  --output-dir "$OUTPUT"

python3 "$WORKFLOW/summarize_corrected_s2.py" \
  --config "$WORKFLOW/config.json" \
  --data-root /external/data-root \
  --accepted-dir "$ACCEPTED" \
  --output-dir "$OUTPUT"

python3 "$WORKFLOW/package_corrected_s2.py" \
  --workflow-dir "$WORKFLOW" \
  --output-dir "$OUTPUT"
```

The packaging command automatically materializes
`SOURCE_REPOSITORY_STATE.md` from the validated, path-sanitized public template
under `provenance/`. If the output already contains that file, it must be
byte-identical to the template. No undocumented manual copy is needed, and the
template deliberately does not depend on a pending release commit hash.

## Large and compact outputs

`paired_read_outcomes.tsv.gz` and
`truth_origin_repeat_membership.tsv.gz` are per-read diagnostics stored only
outside Git. The compact corrected CSV tables, audits, validation reports,
manuscript-ready text, review archive, and hashes are also written to the
external result directory. No BAM, FASTQ, FASTA, or per-read diagnostic is
placed in the compact review archive.

## Stop conditions

The workflow raises an error before accepting corrected results if a pin or
BAM integrity check fails, TSV/ALN/FASTQ names or counts disagree, ART
intervals cannot be reconstructed, historical values are not reproduced,
reference naming has no exact overlap, a truth ID is unknown, a mapped primary
is duplicated, a repeat subset is empty or method-dependent, a contingency
table does not close, bootstrap replay differs, or a unit test fails.
