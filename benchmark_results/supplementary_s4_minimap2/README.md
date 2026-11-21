# Supplementary section S4 and Tables S10–S12

Minimap2 indexing and simulated-read accuracy.

Single-thread indexing uses three references; accuracy uses historical external-call integration; Human threading uses the current inline index implementation.

`inline_indexing/`, `mapping_accuracy/`, and `human_multithread/` are separate experiments with distinct inputs, executable versions and timing. Human thread warmups and formal runs are in separate path-tokenized tables.

These are saved historical results, not a new performance run. The experiment-specific reproduction materials and validation limitations are documented in `reproducibility/supplementary_s4_minimap2/` when available; see the [results index](../README.md) and [dataset guide](../../docs/datasets.md).
