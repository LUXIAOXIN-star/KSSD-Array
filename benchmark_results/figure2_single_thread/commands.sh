#!/usr/bin/env bash
set -euo pipefail

# Exact formal Figure 2 command:
taskset -c 15 python3 $KSSD_RELEASE_HOST/KSSD-Array-public-final/reproducibility/figure2/run_figure2_single_thread.py --datasets $KSSD_RELEASE_HOST/AEEE.fasta $KSSD_RELEASE_HOST/seq/human/GCF_000001405.40_GRCh38.p14_genomic.fna --dataset-names Synthetic_300_Mb GRCh38.p14_chr1 --k-values 16 19 21 24 31 --w-values 10 20 50 --repeats 5 --seed 42 --output-dir $KSSD_RELEASE_HOST/KSSD-Array-formal-results/final-validation-20260731-162115/02_figure2_final
