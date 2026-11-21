# Figure 4 reproduction provenance

The deterministic formal workflow generated 27,000 raw rows and 270 summary
rows using the public library. All keys, seeds, mapped counts, bucket totals,
degrees of freedom, non-rejection decisions, summary values, and plotted data
matched. The regenerated PNG matched the accepted manuscript PNG byte for
byte.

There were 596 raw chi-square text values outside the strict `1e-12`
diagnostic; the maximum absolute difference was
`1.1641532182693481e-10`. These are numerical last-bit effects: summary
mismatches were zero, plotted-value correlation was 1.0, and plotted
percentage-point difference was 0.0.

Formal raw CSV SHA-256:
`9b44faf7486931058f72154afa9c8cda59eedf26572864459268573faa1d4bc6`.
Formal summary CSV SHA-256:
`bd657e4c3bcae1d8d67bd85b5bb47fac932f41f0da31acab1eb1ecc1732967f1`.
Status: `fully_reproduced` at the summary and plotted-data layers.
