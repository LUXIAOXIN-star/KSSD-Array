# Benchmark input generation

This directory documents formal manuscript inputs that are generated or
derived outside Git. Generated FASTA, FASTQ, ALN, BED, BAM, and index files
remain external; the repository stores source, commands, provenance, and
expected cryptographic identities.

## Shared Synthetic 300 Mb input

The exact `AEEE.fasta` input is shared by:

- Figure 2 single-thread benchmarking;
- Figure 3 multithread benchmarking;
- the matched-workload KSSD-Array/ntHash comparison.

Generate it once with the deterministic workflow under
[`synthetic_300M/`](synthetic_300M/README.md), verify its reported identity,
and pass the same path to all three formal runners. Do not commit the generated
300 MB file.

## Supplementary S2

[`supplementary_s2/`](supplementary_s2/README.md) connects the four pinned
ART_Illumina simulations, retained ART ALN truth, historical compatibility
truth tables, repeat-annotation conversion, and the existing formal Minimap2
alignment runner. BAMs are regenerated artifacts and are not stored in Git.

Repeat-source provenance, exact conversions, checksums, and the documented
Human historical-export limitation are described under
[`repeat_annotations/`](repeat_annotations/README.md).

## Policy

Formal inputs must match the size and SHA-256 recorded by their workflow.
A semantically similar or newly simulated input is not interchangeable with
an accepted manuscript input. Scripts refuse existing outputs and stop on
identity mismatches.
