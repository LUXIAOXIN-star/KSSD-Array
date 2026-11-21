# Supplementary Figure S1 public-inline final report

Generated: `2026-07-31T23:43:28+08:00`

This is the completed three-dataset comparison of Original Minimap2 and the
optimized public runtime-inline KSSD-Array path.

Protocol: one discarded warm-up per method/dataset; five sequential paired repeats; Original first on odd repeats and KSSD first on even repeats; one thread pinned to the configured CPU; warm cache; no performance-based early stopping.

Environment-filtered attempts preserved outside the accepted raw table: `8`.

## Arabidopsis thaliana

- Original wall time: `8.730301 +/- 0.047865 s` (mean +/- sample SD).
- Public-inline KSSD wall time: `8.245624 +/- 0.073533 s` (mean +/- sample SD).
- Paired KSSD/Original ratios: `0.944520, 0.931203, 0.942006, 0.962618, 0.942250`.
- Median paired ratio: `0.942249969800`; direction: KSSD faster `5/5`, slower `0/5`; classification: **KSSD faster**.
- Maximum RSS (Original/KSSD/all): `1.178474` / `1.021988` / `1.178474 GiB`.
- Order-position check: Original-first mean ratio `0.942925`; KSSD-first mean ratio `0.946910`.
- Original/KSSD index sizes: `390598072` / `379345984` bytes; distinct minimizers: `15692971` / `14938268`; mean spacing: `5.338` / `5.500`.
- Distinct-minimizer density per base (Original/KSSD): `0.131136878` / `0.124830271`.
- Output equivalence across repeats within each method: **PASS**.

## Human GRCh38

- Original wall time: `173.975028 +/- 0.101788 s` (mean +/- sample SD).
- Public-inline KSSD wall time: `175.828929 +/- 0.083927 s` (mean +/- sample SD).
- Paired KSSD/Original ratios: `1.011283, 1.010880, 1.009705, 1.010775, 1.010638`.
- Median paired ratio: `1.010775375375`; direction: KSSD faster `0/5`, slower `5/5`; classification: **Inconclusive/comparable**.
- Maximum RSS (Original/KSSD/all): `12.093925` / `11.189190` / `12.093925 GiB`.
- Order-position check: Original-first mean ratio `1.010542`; KSSD-first mean ratio `1.010828`.
- Original/KSSD index sizes: `7682339709` / `7432760197` bytes; distinct minimizers: `100224366` / `90357686`; mean spacing: `5.582` / `5.745`.
- Distinct-minimizer density per base (Original/KSSD): `0.030385470` / `0.027394145`.
- Output equivalence across repeats within each method: **PASS**.

## Zea mays

- Original wall time: `131.287672 +/- 0.049634 s` (mean +/- sample SD).
- Public-inline KSSD wall time: `129.625545 +/- 0.047048 s` (mean +/- sample SD).
- Paired KSSD/Original ratios: `0.987748, 0.987993, 0.987009, 0.986799, 0.987150`.
- Median paired ratio: `0.987150304560`; direction: KSSD faster `5/5`, slower `0/5`; classification: **Inconclusive/comparable**.
- Maximum RSS (Original/KSSD/all): `9.019279` / `8.575523` / `9.019279 GiB`.
- Order-position check: Original-first mean ratio `0.987302`; KSSD-first mean ratio `0.987396`.
- Original/KSSD index sizes: `5059820643` / `4922046779` bytes; distinct minimizers: `60810863` / `56619609`; mean spacing: `5.348` / `5.510`.
- Distinct-minimizer density per base (Original/KSSD): `0.027868353` / `0.025947588`.
- Output equivalence across repeats within each method: **PASS**.
