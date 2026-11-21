# Historical external-call mapping accuracy

Supplementary Section S4.2 and Table S11 evaluate simulated reads against original ground truth using the earlier external-call integration. Reference FASTA, simulated FASTQ, ART truth, BAM and associated identities are external; these are not the current inline indexing files. See the [dataset guide](../../../docs/datasets.md).

The historical exact McNemar test requires `scipy.stats.binom_test`: the small tests passed with Python 3.8.13 and SciPy 1.8.1. Newer SciPy can produce tiny floating-point differences and is not claimed bit-identical. The following independent wrapper performs preflight by default, does not run mapping, requires explicit input directories and refuses an existing output:

```sh
python3 -B reproducibility/supplementary_s4_minimap2/run_accuracy.py --data-root /path/to/inputs --accepted-dir /path/to/accepted-alignments --output /path/to/new-output
```

Inspect the wrapper and input identities before adding `--execute`. The external data and required `samtools` are not supplied; output includes truth-origin counts and correctness statistics. Full BAM/truth processing was not rerun. Historical configuration names use an older table identifier; final manuscript numbering is S11.

**Status: PARTIAL for earlier isolated unit/preflight checks; NOT_FULLY_REPLAYED for complete accuracy analysis.**
