# Supplementary Table S2 input workflow

This directory records how the four accepted single-end read sets, retained
truth inputs, repeat annotations, and regenerated Minimap2 BAMs are obtained.
It does not store the large FASTA, FASTQ, ALN, BED, BAM, or index files. Every
accepted external input is pinned in `expected_sha256.tsv`.

The scripts are publication recipes, not CI tasks. They refuse existing
outputs and must not be used to overwrite accepted data. The repository's
corrected S2 results reused accepted BAMs; no alignment rerun was performed for
that correction.

## External data layout

The examples use a data root with these paths:

```text
DATA_ROOT/
  seq/human/GCF_000001405.40_GRCh38.p14_genomic.fna
  seq/human/sim_se_{100,150}bp_500K.{fq,aln}
  seq/human/sim_se_{100,150}bp_500K_truth_qpos.tsv
  seq/human/hg38_repeats_refseq.bed
  seq/Zea_mays/Zm-B73-REFERENCE-NAM-5.0.fa
  seq/Zea_mays/sim_zeamays_se_{100,150}bp_500K.{fq,aln}
  seq/Zea_mays/sim_zeamay_se_{100,150}bp_500K_truth_qpos.tsv
  seq/Zea_mays/maize_repeats_raw.bed
```

Reference sources and checksums are documented in
[`../../../docs/datasets.md`](../../../docs/datasets.md). Repeat-source details
and the transparent Human historical-export limitation are in
[`../repeat_annotations/README.md`](../repeat_annotations/README.md).

## 1. Simulate the reads

The accepted executable was ART_Illumina Q 2.5.8, using the built-in `HS25`
profile, single-end mode, and seed 42. `simulate_reads.sh` first checks the
exact ART executable identity and version plus both input reference hashes.
It then runs these commands from the directory containing each reference:

```sh
art_illumina -ss HS25 -i GCF_000001405.40_GRCh38.p14_genomic.fna -l 100 -f 0.0167 -rs 42 -o sim_se_100bp_500K
art_illumina -ss HS25 -i GCF_000001405.40_GRCh38.p14_genomic.fna -l 150 -f 0.025 -rs 42 -o sim_se_150bp_500K
art_illumina -ss HS25 -i Zm-B73-REFERENCE-NAM-5.0.fa -l 100 -f 0.0235 -rs 42 -o sim_zeamays_se_100bp_500K
art_illumina -ss HS25 -i Zm-B73-REFERENCE-NAM-5.0.fa -l 150 -f 0.0353 -rs 42 -o sim_zeamays_se_150bp_500K
```

Run only when intentional regeneration is required:

```sh
reproducibility/data_generation/supplementary_s2/simulate_reads.sh \
  --art /opt/art_bin_MountRainier/art_illumina \
  --data-root /external/data-root
```

The script checks the generated FASTQ and ALN byte sizes, SHA-256 values, and
FASTQ read counts. `--verify-only` checks an existing exact set without
starting ART. The executable hash is for the accepted Linux distribution; a
different ART 2.5.8 build is not asserted to be byte-identical.

## 2. Retain and interpret truth

The ART `.aln` file is the authoritative truth because it retains reference,
query ID, raw offset, strand, gapped reference alignment, and reference
length. ART's bundled official `aln2bed.pl` defines a 0-based, half-open
interval as follows:

- `+` strand: `start = raw_offset`, `end = start + ungapped_reference_span`;
- `-` strand: `end = reference_length - raw_offset`,
  `start = end - ungapped_reference_span`.

The corrected evaluator implements and validates those strand-aware semantics.
The reduced `*_truth_qpos.tsv` files omit strand and are retained only to prove
historical compatibility; they are not a substitute for ART ALN truth.
`generate_truth.sh` checks the official converter and all four ALNs, recreates
the four exact reduced views, and verifies their hashes:

```sh
reproducibility/data_generation/supplementary_s2/generate_truth.sh \
  --aln2bed /opt/art_bin_MountRainier/aln2bed.pl \
  --data-root /external/data-root
```

For the corrected primary analysis, the denominator is every ART truth record,
which is also every FASTQ read after ID/count validation. A missing or unmapped
primary assignment remains in the denominator and is counted as incorrect;
secondary and supplementary records are excluded from primary assignment.
Truth reference, truth strand, and a reported start within 5 bp are required
for correctness. Truth-origin repeat membership is computed once and reused
for both methods.

## 3. Generate repeat annotations

After obtaining the two exact sources described in the repeat-provenance
README, run:

```sh
reproducibility/data_generation/supplementary_s2/generate_repeat_annotations.sh \
  --data-root /external/data-root \
  --human-source /external/archive/hg38_repeats.bed \
  --zea-gff /external/archive/Zm-B73-REFERENCE-NAM-5.0.TE.gff3
```

The Human conversion retains only the 25 assembled chromosomes and translates
UCSC names to the GRCh38.p14 RefSeq accessions. The Zea conversion changes
GFF3 1-based inclusive coordinates to BED 0-based half-open coordinates.

## 4. Regenerate alignments only if required

`run_alignment.sh` delegates to the existing pinned S2 alignment runner. For
each method/condition the effective pipeline is:

```text
minimap2 -ax sr -t 1 COMPATIBLE_INDEX READS | samtools sort -o OUTPUT.bam -
```

The Original executable consumes its `MMI2` index and the integrated
KSSD-Array executable consumes its `KSA1` index. The wrapper requires the
accepted Phase 5B build/index directory and a new output directory:

```sh
reproducibility/data_generation/supplementary_s2/run_alignment.sh \
  --data-root /external/data-root \
  --phase5b-output /external/results/minimap2-indexing-s1 \
  --output-dir /external/results/minimap2-alignment-s2-new
```

This is a full alignment workflow and is not run by `make check` or CI. BAMs,
indexes, logs, and per-read diagnostics are regenerated external artifacts and
are not stored in Git.
