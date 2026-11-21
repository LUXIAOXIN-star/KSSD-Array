# Human multithread indexing

Supplementary Section S4.3 and Table S12 report complete Human reference indexing using the current inline integration and the corresponding unmodified Minimap2 control. The original complete uncompressed GRCh38.p14 FASTA and its SHA are specified in the [dataset guide](../../../docs/datasets.md).

The original experiment fixed k=15, w=10, no homopolymer compression and requested 1/4/8/16 threads. It performed eight separate warmups and 24 independent measured processes; each process includes reading, initialization, index construction and `.mmi` write. The requested thread count should not be claimed as an observed worker count if not recorded.

A complete portable build/execute command has not been verified; historical scripts assume the original output/build layout. Check matched version, exact input SHA, process exit and same-method index statistics. Warmup data and formal measurements remain separate.

**Status: HISTORICAL_DATA_AVAILABLE / NOT_FULLY_REPLAYED.** [Results](../../../benchmark_results/supplementary_s4_minimap2/README.md).
