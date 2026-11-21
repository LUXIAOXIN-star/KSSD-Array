# Forty-condition continuous DNA ntHash comparison

## Manuscript reference

Supplementary Section S2 and Table S3. [Results](../../benchmark_results/supplementary_s2_nthash/README.md).

## Experimental objective

Forty-condition continuous DNA ntHash comparison.

## Required inputs

Synthetic 300 Mb and GRCh38.p14 chr1 first record. See the [dataset guide](../../docs/datasets.md) for identities and availability.

## Input preparation

Delete non-ACGT characters and join; encode/roll under the historical timer.

## Parameters

k=15,19,21,24,31; w=5,10,20,50; five paired technical repeats within each process.

## Software dependencies

Frozen ntHash 2.4.0 MIT source and KSSD, C++17, zlib. See [dependencies](../../docs/dependencies.md).

## Compiler and build options

`-O3 -march=native -DNDEBUG` for the practical workflow.

## Build command

The source and portable entry are shared with `reproducibility/table2_nthash/`.

## Execution command

```sh
python3 reproducibility/table2_nthash/run_portable.py --mode smoke --input /path/to/small.fa --input-sha256 SHA256 --cpu CPU --out /path/to/new-output
```

## Output description

Per-method score, window counts, checksums and throughput.

## Result verification

Small-input direct-score and naive-window oracle comparison checks both methods.

## Current validation status

PARTIAL: the relocated entry passed a new isolated small-input oracle check; complete 40-condition grid was not rerun.
