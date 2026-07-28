# Dependencies

Ordinary builds never download dependencies. Run `python3
tools/check_dependencies.py` for an actionable local report.

| Dependency | Version | Classification | Used by |
|---|---|---|---|
| C compiler | C11-capable | core build | library, tests |
| CMake | 3.16 or newer | core build | configure, install, CTest |
| Python | 3.8 or newer | benchmark | workflow runners and checks |
| zlib | system development package | benchmark/integration | compressed FASTA, Minimap2 |
| xxHash | system `libxxhash` development package | benchmark | Figures 2--4 |
| OpenMP | compiler-supported | benchmark | Figure 3 |
| R | 3.6 or newer | plotting | Figures 2 and 3 |
| ggplot2 | compatible with installed R | plotting | Figures 2 and 3 |
| ntHash | 2.4.0, commit `c26bd4572a19de81e30d55042dbd33c1fd21d4b6` | benchmark | Table 4 |
| Minimap2 | 2.30-r1287, commit `79c9cc186b95f50bd899f69b48eba995ced810c6` | integration | Supplementary workflows |
| samtools | installed command-line version | formal data reproduction | Table S2 filtering and metrics |
| bedtools | installed command-line version | formal data reproduction | repeat-region intersections |
| ART_Illumina | 2.5.8 | formal data reproduction | Table S2 read simulation |
| Address/UndefinedBehavior sanitizers | compiler runtime | optional | `make sanitize` |
| pkg-config | installed command-line version | optional | installed consumer validation |

Prepare the pinned ntHash dependency explicitly with
`reproducibility/table4/prepare_nthash.sh`, or set `NTHASH_ROOT` to a verified installed
prefix. Select an existing pinned Minimap2 checkout with
`MINIMAP2_SOURCE_DIR`. Ordinary `make`, `make test`, and `make check` do not
fetch either project.

The ntHash preparation script uses Meson when available. On minimal systems it
can build the same two pinned upstream source files directly with a C++17
compiler and the system archive tools; no generated or private installation is
used by that fallback.

Exact version output varies by platform. Formal result manifests record the
versions actually used; this document distinguishes fixed protocol versions
from minimum interface requirements.
