# Historical metric reproduction

Status: **PASS — all 12 historical deltas were reproduced from the accepted BAMs.**

The compatibility parser applies the historical `-F 2308` primary-mapped filter, ±5 bp test against the stored strand-relative offset or `offset-(read_length-1)`, method-specific reported-alignment repeat BAMs, and mapped-primary MAPQ denominator. Every method-level absolute metric matches the accepted raw CSV to better than `1e-15`; every displayed delta matches to the `1e-12` requirement used here.

This successful reproduction validates parser compatibility only. It does not validate the old truth-coordinate interpretation; the ART audit shows why the corrected analysis must reconstruct genomic intervals from `.aln` strand and reference length.
