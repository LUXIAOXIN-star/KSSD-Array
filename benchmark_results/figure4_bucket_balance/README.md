# Main-text Figure 4 bucket-balance results

This directory contains the accepted **main-text Figure 4** bucket-balance
result. It is not a Supplementary result.

The exact accepted result source is
`$KSSD_RELEASE_HOST/KSSD-Array-formal-results/figure4-20260727-phase4d`.
The tracked public workflow is
[`../../reproducibility/figure4/`](../../reproducibility/figure4/).
No benchmark or experiment was rerun while assembling this directory.

## Accepted files and verification

- `figure4_bucket_balance_raw.csv`: 27,000 rows, comprising 5,400 complete
  condition/repeat groups with five methods per group.
- `figure4_bucket_balance_summary.csv`: 270 complete summary rows.
- `figure4_bucket_balance.png` and `figure4_bucket_balance.pdf`: byte-identical
  copies of the accepted raster and vector plots.
- `build_manifest.txt` and `run_manifest.txt`: accepted manifests with only
  developer-local path prefixes mechanically replaced by
  `$KSSD_RELEASE_HOST` for the public package.
- `plot_figure4_bucket_balance.py`: the tracked public plotting script. It
  accepts the accepted legacy `Wyhash` rows and normalizes only their display
  label to `wyhash`; it does not change numeric columns.
- `output_sha256.tsv`: package-time SHA-256 inventory of the public files.
  The accepted source directory did not contain an output hash inventory, so
  this file is release metadata rather than a historical experiment output.

The accepted run manifest reports `status=complete`, 5,400 conditions,
27,000 raw rows, and 270 summary rows. Its embedded raw and summary SHA-256
values match the files:

| File | Accepted SHA-256 |
|---|---|
| `figure4_bucket_balance_raw.csv` | `9b44faf7486931058f72154afa9c8cda59eedf26572864459268573faa1d4bc6` |
| `figure4_bucket_balance_summary.csv` | `bd657e4c3bcae1d8d67bd85b5bb47fac932f41f0da31acab1eb1ecc1732967f1` |
| `figure4_bucket_balance.png` | `625359beac7c6ffcbf506ecad0c7b92d1ad490a2af1c58e651adcfc7cbf13897` |
| `figure4_bucket_balance.pdf` | `68b8ccf8e9ae19f51b63db39e66433d8230e2fc91b451711f95ebd031f4a07f1` |

Independent read-only checks confirmed the full k, sequence-length, bin, and
repeat grid; mapped-count and bucket-count identities; degrees of freedom;
the `p_value > 0.05` non-rejection rule; and all summary grouping/count
fields. Floating-point summary recomputation agreed within at most
`1.17e-10`, consistent with CSV parsing and aggregation roundoff.

## Workflow-to-result source binding

The accepted build manifest records benchmark source SHA-256
`253b2876d153c4fad3f9c42d198400b4ad2e929c6490c0e1f59261998ebf3828`.
That exact source is recoverable from the Figure 4 workflow-introduction
history. A source diff against the current public benchmark finds no numeric
or executable-logic change: the current file adds one attribution comment and
normalizes the emitted display name from `Wyhash` to `wyhash`. The public
runner additionally reflects the workflow directory move and the same display
normalization. Thus the current public workflow matches the accepted result's
computational source; it is not byte-identical only because of these
documented non-numeric portability and label changes.

The accepted build binary is also present in the formal source directory and
matches the build manifest SHA-256
`2e956dc574826f1c34cbc4e93c2073bc7db7c86d8b529a7eb1f212d9d1bc18ed`.
