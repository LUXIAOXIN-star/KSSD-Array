# Manuscript input-provenance recommendations

Status: wording recommendations only. No manuscript file was edited.

## Methods: Synthetic 300 Mb input

Recommended wording:

> The Synthetic 300 Mb benchmark input was a single-record FASTA containing
> exactly 300,000,000 bases. It was reconstructed with a portable deterministic
> generator using fixed seed 1781167332 and the historical low-two-bit mapping
> 0=A, 1=T, 2=C, and 3=G. The legacy FASTA header was retained solely for
> byte-exact identity with the accepted benchmark input. The resulting
> 300,000,057-byte file had SHA-256
> a7eca29bdfa06ff373048fffa7a90139afc98acfa938a8ec0a98459608045962.

Do not describe the legacy header as biological provenance. The file is
synthetic and is shared by Figure 2, Figure 3, and the matched-workload ntHash
comparison.

## Methods: Supplementary Table S2 simulation and truth

Recommended wording:

> Single-end reads of 100 bp and 150 bp were simulated from GRCh38.p14 and
> Zea mays B73 RefGen_v5 with ART_Illumina Q 2.5.8, the built-in HS25 profile,
> and seed 42. The Human coverage factors were 0.0167 and 0.025; the Zea mays
> factors were 0.0235 and 0.0353. The retained ART ALN files were the
> authoritative truth. Strand-aware 0-based half-open truth intervals followed
> ART's bundled `aln2bed.pl` semantics. Global correctness used every ART truth
> read as its denominator; a missing or unmapped primary assignment was counted
> as incorrect, and secondary and supplementary records were excluded from
> primary assignment. Repeat membership was assigned once from truth-origin
> intervals and reused for both methods.

If command-level detail is appropriate for the Methods or Supplement, cite the
four exact commands in
`reproducibility/data_generation/supplementary_s2/README.md`. State explicitly
that the reduced historical truth TSVs omit strand and are compatibility views,
not the primary corrected truth.

## Methods: Repeat annotations

Recommended wording:

> Human repeat intervals were derived from a recovered six-column BED export
> of the UCSC hg38 `rmsk` table, restricted to the 25 assembled chromosomes,
> and translated from UCSC chromosome names to the corresponding GRCh38.p14
> RefSeq accessions. The recovered source and converted BED were verified by
> file size and SHA-256. The exact historical UCSC export command and record
> ordering were not preserved. The Zea mays repeat annotation was obtained
> from the MaizeGDB B73 RefGen_v5
> `Zm-B73-REFERENCE-NAM-5.0.TE.gff3.gz` release file. GFF3 1-based inclusive
> coordinates were converted to BED 0-based half-open coordinates by
> subtracting one from the start and retaining the end. Both conversion
> workflows reproduce the accepted BED identities recorded in the repository.

## Data Availability

The Data Availability statement should change. Recommended wording:

> The KSSD-Array source code, deterministic input-generation workflows,
> benchmark results, and associated metadata are publicly available at
> https://github.com/LUXIAOXIN-star/KSSD-Array under release tag
> `v1.1.0-paper`. Synthetic benchmark inputs can be regenerated using the
> provided fixed-seed workflow and verified by SHA-256 checksums. Large
> external inputs, including reference genomes, simulated reads, alignments,
> indexes, and repeat annotations, are documented through accession
> information, generation commands, conversion workflows, and file checksums.
