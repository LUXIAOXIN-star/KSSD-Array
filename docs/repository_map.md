# Repository map

## Choose your path

1. **Library users** should begin with the [main README](../README.md), then
   use the public headers and runnable examples. The complete API contract is
   in [`api.md`](api.md).
2. **Paper readers and reproducibility users** can inspect the
   [accepted-result index](../benchmark_results/README.md) or follow the
   [experiment workflow index](../reproducibility/README.md).
3. **Release and provenance auditors** can review the
   [validation index](validation/README.md), then follow the source and result
   records under [`provenance/`](provenance/).

## Top-level directories

- **`include/`** — Public headers and APIs that library users include.
- **`src/`** — Internal implementation of the KSSD-Array library.
- **`examples/`** — Minimal working examples for the context API and rolling
  minimizer construction.
- **`tests/`** — Library correctness tests and deterministic fixture
  generators used by smoke workflows.
- **`docs/`** — Algorithm, API, dataset, validation, and provenance
  documentation.
- **`benchmark_results/`** — Accepted numerical results, final figures and
  tables, summaries, raw measurements, and integrity evidence. It contains
  results, not the primary experiment-running code.
- **`reproducibility/`** — Workflows and scripts used to reproduce the paper
  experiments. Ordinary library users do not need to run these workflows.
- **`tools/`** — Repository release-quality, documentation, integrity, and
  policy checks.

Build-system support is kept in `.github/`, `cmake/`, and `pkgconfig/`. The
root `CMakeLists.txt` and `Makefile` build only the requested components; a
normal library build does not run manuscript workflows.

## Common file types in result packages

| File type | Purpose |
| --- | --- |
| `README.md` and `*_REPORT.md` | Start here for scope and interpretation |
| `*.png` and `*.pdf` | Manuscript figures |
| `*_summary.csv` | Compact summary results |
| `*_raw.csv` | Accepted raw measurements |
| `commands.sh` | Executed command sequence |
| `build_manifest.txt` | Build identity |
| `run_manifest.txt` | Run protocol |
| `environment.txt` | Hardware and software environment |
| `*_sha256.tsv` | File integrity and source binding |

## Files most users can ignore

Ordinary library users normally do not need the full benchmark manifests,
output inventories, provenance hashes, corrected-S2 audit reports, or release
validation reports. These are not unnecessary files: they are retained as
evidence for reviewers, reproducibility checks, and release audits. Use the
[result index](../benchmark_results/README.md) to find the three recommended
entry files for each paper result.
