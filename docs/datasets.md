# Datasets and data policy

Only source and specifications for small functional fixtures are committed. Full references, simulated
reads, indexes, alignments, raw performance tables, and figures belong outside
the repository. `reproducibility/data/external/` is ignored except for its policy marker.

Dataset resolution is: an explicit runner argument, then `KSSD_DATA_DIR`, then
`reproducibility/data/external`. Before a formal run, validate every input with `sha256sum` and
compare it to `reproducibility/data/datasets.json` or the workflow-specific configuration.

Formal run manifests record the resolved path, accession and version, byte
size, SHA-256, FASTA record count, and total base count where applicable. The
Supplementary indexing runner refuses reference size, checksum,
sequence-count, or total-base mismatches and never downloads or decompresses
data implicitly.

## Source-generated fixtures

The wrapper `tests/fixture_generators/generate_test_fixtures.sh` compiles the
public C source in a temporary directory, writes these paths below a requested
output root, and verifies their SHA-256 values. The generated files themselves
are not committed.

| Generated path | SHA-256 |
|---|---|
| `reproducibility/table4/fixtures/table4_smoke.fa` | `912298feebce09f926f9424567b4312f980e2989c60465719c8458e8ad920a6c` |
| `reproducibility/figure3/fixtures/figure3_smoke.fa` | `b91c3f75695966fc2ea88fbba80a0876a34a805aa0d091554da4fb0b73c106d3` |
| `reproducibility/minimap2/fixtures/reference.fa` | `7e778a63b2c946644d5b61fa82606f9cf78ed8025e613f32d05b50e7967d7946` |
| `reproducibility/minimap2/fixtures/query.fa` | `4b53c67adb9fc9af64228675aba6592f8eb3a46977ffcacda95911167ac98706` |
| `reproducibility/minimap2/alignment_consistency_truth_origin/fixtures/reads.fq` | `bb003e9774486cfe5aa984e76fdb7bb572396c15f37f0a96a9f1f0d4f71d4d1c` |
| `reproducibility/minimap2/alignment_consistency_truth_origin/fixtures/repeats.bed` | `ef97de5a281634ab890e02a09f673598fb4ac13212b9cb2b5e8d87f3e6f99eb4` |

The corrected-S2 truth/SAM fixtures below remain committed because they are
human-readable evaluator specifications rather than generated sequence or BED
inputs.

| Committed specification | SHA-256 |
|---|---|
| `reproducibility/minimap2/alignment_consistency_truth_origin/fixtures/truth.aln` | `2a0c9050bb762b96096c13e3fa503ee23e8762521c76e8642aae2a25f0d2c35e` |
| `reproducibility/minimap2/alignment_consistency_truth_origin/fixtures/truth.tsv` | `58ccfb62d04b80635596f8a976f8a57212ce25e8352c7db765c3178c255a42f9` |

The generated Table 4 fixture contains two records and intentionally reads only the
first, preserving the historical protocol. It includes a short ambiguous
region that the Table 4 workflow removes without reset. It is a functional
fixture, not a performance dataset.

The generated Figure 3 fixture contains 400 valid bases, 12 skipped ambiguous symbols,
and an ignored second record. At `k=21`, `w=20`, both workers receive non-empty
window ranges in the two-thread smoke condition.

## Formal references

| Dataset | Accession/version and source | Accepted SHA-256 |
|---|---|---|
| Arabidopsis thaliana | [NCBI RefSeq GCF_000001735.4, TAIR10.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000001735.4/) | `a182f3c71662973dc636cacd7722588c9bbe3c8ea6ce62b1bae7dac940545d47` |
| Human | [NCBI RefSeq GCF_000001405.40, GRCh38.p14](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000001405.40/) | `df6e4918316e05a9cc1fd29c352841d3678b607d7a436819cd43371b52c814c0` |
| Zea mays | [MaizeGDB Zm-B73-REFERENCE-NAM-5.0, B73 RefGen_v5](https://download.maizegdb.org/Zm-B73-REFERENCE-NAM-5.0/) | `52f0663221e46f562eb0923c6dfa1bb43537abb7f13e0f637b5def2571de2c11` |

## Synthetic 300 Mb benchmark input

The synthetic input is one FASTA record containing exactly 300,000,000 bases.
The `AEEE.fasta` used by Figure 2, Figure 3, and the matched-workload ntHash
comparison is reconstructed by
[`reproducibility/data_generation/synthetic_300M/`](../reproducibility/data_generation/synthetic_300M/README.md).
The publication generator fixes seed `1781167332`, explicitly reproduces the
historical glibc stream and `A,T,C,G` mapping, retains the legacy header needed
for exact identity, and verifies the final 300,000,057-byte file against
SHA-256 `a7eca29bdfa06ff373048fffa7a90139afc98acfa938a8ec0a98459608045962`.
The generator reproduces the accepted benchmark identity. The generated FASTA
is synthetic, remains external, and is not committed.

## Supplementary indexing references

Supplementary Figure S1 and Table S1 require exactly the Arabidopsis,
GRCh38, and Zea mays identities listed above. Supply them using repeated
`--dataset KEY=PATH` arguments, beneath `KSSD_DATA_DIR` at the configured
relative paths, or beneath `reproducibility/data/external/`.

## Supplementary S2 simulated reads

The complete input recipe is under
[`reproducibility/data_generation/supplementary_s2/`](../reproducibility/data_generation/supplementary_s2/README.md).
The four accepted single-end read sets are Human 100/150 bp and Zea mays
100/150 bp. ART_Illumina Q 2.5.8 used its HS25 empirical profile and seed 42;
coverage factors were 0.0167, 0.025, 0.0235, and 0.0353, respectively. The
recipe checks reference, executable, FASTQ, and ART ALN identities. ART ALN is
the authoritative strand-aware truth, while the reduced truth TSVs are
historical compatibility views.

The corrected primary denominator is all ART truth reads, including reads
without a mapped primary assignment. Repeat membership is determined from the
truth-origin interval and is therefore method-independent.

The repository does not store those reads, ART ALNs, indexes, SAM/BAM/PAF outputs,
or full per-read diagnostics. It does publish the compact
corrected tables and reports under
`benchmark_results/supplementary_s2_mapping/`. Validate every external input
against its configured SHA-256 before a corrected analysis.

## Repeat annotations

Exact repeat-source identities and coordinate-conversion records are under
[`reproducibility/data_generation/repeat_annotations/`](../reproducibility/data_generation/repeat_annotations/README.md).

The Human annotation was derived from the UCSC hg38 `rmsk` table. The recovered
six-column source BED and accepted GRCh38.p14 RefSeq-name BED are verified by
row count, byte size, and SHA-256. The workflow retains the 25 assembled
chromosomes, maps their UCSC names to RefSeq accessions, and reproduces the
accepted converted identity. The exact historical UCSC export command and
record ordering were not preserved and are not claimed.

The Zea annotation uses the MaizeGDB B73 RefGen_v5
`Zm-B73-REFERENCE-NAM-5.0.TE.gff3.gz` source. Its compressed and uncompressed
checksums are recorded. The workflow converts GFF3 1-based inclusive intervals
to BED 0-based half-open intervals and verifies the accepted BED SHA-256.
Repeat sources and generated BED files remain external rather than stored in
Git.
