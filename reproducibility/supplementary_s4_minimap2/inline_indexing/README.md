# Minimap2 inline single-thread indexing

Main Table 3 and Supplementary Table S10 report full reference indexing on Arabidopsis, Human GRCh38.p14 and maize B73. Use the exact external FASTA files and their compression formats specified in the [dataset guide](../../../docs/datasets.md).

Minimap2 2.30-r1287 commit `79c9cc186b95f50bd899f69b48eba995ced810c6`, the corresponding KSSD inline integration, k=15, w=10, no homopolymer compression and one requested thread are fixed. The full process includes file read, initialization, scoring, window selection, index construction and writing; five paired process measurements are retained. Historical Minimap2 flags were `-g -Wall -O2 -Wc++-compat`; the KSSD library and link flags require their own build record.

A fully portable complete build/execute launcher has not been verified; do not execute frozen commands against their historical output paths. Check reference hashes, binary and patch identities, each exit code and index statistics. The earlier external-call accuracy and separate Human multithread experiment are different workloads.

**Status: HISTORICAL_DATA_AVAILABLE / NOT_FULLY_REPLAYED.** [Results](../../../benchmark_results/table3_minimap2_indexing/README.md).
