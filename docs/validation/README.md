# Validation

The library's reproducible correctness checks are under [`tests/`](../../tests/).
Run `make test` after building the library. The minimal C example under
[`examples/`](../../examples/) demonstrates initialization, mapping, and
resource cleanup. An external C consumer can include the public headers and link the
static library without benchmark dependencies.

Benchmark results and the scope of any available small-input checks are
documented separately in [`benchmark_results/`](../../benchmark_results/) and
[`reproducibility/`](../../reproducibility/). Saved benchmark measurements are
not new runs.
