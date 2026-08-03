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

| Dataset | Accession/version | SHA-256 |
|---|---|---|
| Arabidopsis thaliana | GCF_000001735.4, TAIR10.1 | `a182f3c71662973dc636cacd7722588c9bbe3c8ea6ce62b1bae7dac940545d47` |
| Human | GCF_000001405.40, GRCh38.p14 | `df6e4918316e05a9cc1fd29c352841d3678b607d7a436819cd43371b52c814c0` |
| Zea mays | Zm-B73-REFERENCE-NAM-5.0, B73 RefGen_v5 | `52f0663221e46f562eb0923c6dfa1bb43537abb7f13e0f637b5def2571de2c11` |

The historical 300,000,000-base synthetic FASTA has SHA-256
`a7eca29bdfa06ff373048fffa7a90139afc98acfa938a8ec0a98459608045962`.
Its deterministic generator was not recovered, so its generation provenance
is unresolved and the file is not redistributed.

## Supplementary indexing references

Supplementary Figure S1 and Table S1 require exactly the Arabidopsis,
GRCh38, and Zea mays identities listed above. Supply them using repeated
`--dataset KEY=PATH` arguments, beneath `KSSD_DATA_DIR` at the configured
relative paths, or beneath `reproducibility/data/external/`.

## Supplementary Table S2 reads

The four accepted single-end read hashes are listed in
`reproducibility/minimap2/alignment_consistency_truth_origin/config.json`:
Human 100/150 bp and Zea mays 100/150 bp. ART_Illumina 2.5.8 used its HS25
empirical profile and seed 42.
Coverage factors were 0.0167, 0.025, 0.0235, and 0.0353, respectively. The
configuration also records read counts, truth tables, repeat BED hashes, and
the complete simulation commands.

The repository does not store those reads, indexes, SAM/BAM/PAF outputs,
repeat BEDs, or full per-read diagnostics. It does publish the compact
corrected tables and reports under
`benchmark_results/supplementary_s2_mapping/`. Validate every external input
against its configured SHA-256 before a corrected analysis.
