# Truth-origin repeat audit

Status: **PASS**. Repeat membership is calculated once from the ART genomic truth interval using overlap of at least one base with the pinned repeat BED. The identical read-ID set is used for Original Minimap2 and KSSD-Array; `bedtools intersect -u` ensures one count per read.

| Reference | Read length | Total truth | Repeat origin | Non-repeat origin | Repeat proportion | Shared refs | Truth reads on unannotated refs | Unmatched truth-ref names |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Human GRCh38.p14 | 100 bp | 523688 | 302232 | 221456 | 57.712% | 25 | 32955 | 595 |
| Human GRCh38.p14 | 150 bp | 522254 | 320208 | 202046 | 61.313% | 25 | 32857 | 596 |
| Zea mays B73 RefGen_v5 | 100 bp | 511569 | 446511 | 65058 | 87.283% | 685 | 0 | 0 |
| Zea mays B73 RefGen_v5 | 150 bp | 512303 | 450469 | 61834 | 87.930% | 685 | 0 | 0 |

Reference names are compared exactly; no `chr`/accession rewriting is performed. The Human repeat BED provides annotations for the 25 assembled chromosomes, all of which match truth and BAM accessions exactly. ART also sampled alternate/unlocalized scaffolds absent from that BED; those reads are explicitly counted above and conservatively receive no repeat annotation. This is annotation absence, not a correctable naming-prefix mismatch. Zea mays has complete 685/685 reference-name coverage.

The complete unmatched-name lists are retained in `TRUTH_ORIGIN_REPEAT_AUDIT.tsv`; per-read assignments are in `truth_origin_repeat_membership.tsv.gz`.
