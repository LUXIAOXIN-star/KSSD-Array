# Supplementary Table S2 method definition

This file documents the metric implementation used for the accepted numerical
results in this directory. It does not change or recompute those results.

## Inputs and read counts

Single-end reads were generated with ART_Illumina 2.5.8, its built-in HS25
profile, and seed 42. The actual truth/read counts are:

| Dataset | Read length | Reads |
|---|---:|---:|
| Human GRCh38.p14 | 100 bp | 523,688 |
| Human GRCh38.p14 | 150 bp | 522,254 |
| Zea mays B73 RefGen_v5 | 100 bp | 511,569 |
| Zea mays B73 RefGen_v5 | 150 bp | 512,303 |

## Alignment records included

Each read set was aligned with `-ax sr -t 1`. Metric evaluation excludes
records whose SAM flag has any of `0x4` (unmapped), `0x100` (secondary), or
`0x800` (supplementary) set; this is the historical `-F 2308` primary-mapped
definition. Secondary and supplementary record counts are reported separately.

## Global truth-position accuracy

For each method and condition:

`global accuracy = correct truth-matched primary alignments / truth-matched primary alignments`

A primary alignment is correct when its reported reference name equals the
truth reference and its reported position is within 5 bp of either the stored
forward truth coordinate or the historical reverse-offset coordinate
`truth_position - (read_length - 1)`. Unmapped reads are therefore not in this
denominator. The raw file also reports `correct / total truth reads` separately
as `global_correct_over_total_truth`; that field is not the Table S2 global
accuracy.

## Repetitive-region accuracy

For each method independently, `bedtools intersect -a METHOD.bam -b REPEAT.bed
-u` selects alignments by their reported BAM coordinates. The method's
repeat-subset BAM is then evaluated with the same primary-record and ±5 bp truth
rules. Thus:

`repeat accuracy = correct truth-matched primary alignments in that method's repeat subset / truth-matched primary alignments in that method's repeat subset`

Repeat membership is not assigned from the simulator's truth coordinate, and
the Original and KSSD-Array subsets and denominators may differ.

## MAPQ=60 rate

For each method and condition:

`MAPQ=60 rate = MAPQ-60 truth-matched primary alignments / truth-matched primary alignments`

It does not divide by all simulated reads or all SAM records.

## Table deltas and interpretation

Table S2 reports `(KSSD-Array - Original Minimap2) * 100` in percentage points.
The metric called `identity_value` in the raw file is explicitly
`truth_position_accuracy`. It is a read-mapping correctness measure and is not
nucleotide alignment identity, sequence identity, or percent identity from an
alignment CIGAR/MD calculation.

