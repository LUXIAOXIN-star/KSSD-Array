# Dependencies

Ordinary builds never download dependencies. Run `python3
tools/check_dependencies.py` for an actionable local report.

| Dependency | Version | Classification | Used by |
|---|---|---|---|
| C compiler | C11-capable | core build | library, tests |
| CMake | 3.16 or newer | core build | configure, install, CTest |
| Python | 3.8 or newer | benchmark | workflow runners and checks |
| zlib | system development package | benchmark/integration | compressed FASTA, Minimap2 |
| xxHash v0.8.3 | fixed header, `XXH_INLINE_ALL`, BSD 2-Clause | benchmark | Figure 2a primary scoring curves |
| xxHash shared runtime | historical runtime 0.7.3; exact historical shared object/header hashes not recorded | benchmark | Figure 2b, Figure 4, and Figure 2a shared anchors; not Figure 2a's primary inline curves |
| OpenMP | compiler-supported | benchmark | Supplementary Figure S1 |
| R | 3.6 or newer | plotting | historical rescan and thread plots |
| ggplot2 | compatible with installed R | plotting | historical rescan and thread plots |
| ntHash | 2.4.0, commit `c26bd4572a19de81e30d55042dbd33c1fd21d4b6` | benchmark | current Table 2 and separate LTO comparison |
| Rust and Cargo | exact recorded version and lockfile vary by experiment | benchmark | seq-hash, SIMD, GreedyMini adapters and gxhash; see each build record |
| Minimap2 | 2.30-r1287, commit `79c9cc186b95f50bd899f69b48eba995ced810c6` | integration | Supplementary workflows |
| samtools | installed command-line version | formal data reproduction | simulated-read filtering and metrics |
| bedtools | installed command-line version | formal data reproduction | repeat-region intersections |
| ART_Illumina | 2.5.8 | formal data reproduction | simulated-read generation |
| Address/UndefinedBehavior sanitizers | compiler runtime | optional | `make sanitize` |
| pkg-config | installed command-line version | optional | installed consumer validation |

Prepare the pinned ntHash dependency explicitly with
`reproducibility/_shared/prepare_nthash.sh`, or set `NTHASH_ROOT` to a verified installed
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


## Fixed optional comparison implementations

The following dependencies are not part of the core library. Use the particular version for each experiment; a source identity or a Cargo lockfile does not by itself verify permission to redistribute a specific historical snapshot.

| Optional dependency | Recorded identity | Access and license status |
| --- | --- | --- |
| seq-hash 0.2.0 path | `4cd7eed354923f908e8d284a93a359a899199d2c` | [Upstream](https://github.com/rust-seq/seq-hash); exact-version license text remains to be confirmed. |
| seq-hash 0.2.0 registry | `d8d210d3aa3c4accccf92bbf80b26eba53ad3243`; archive SHA-256 `51964cd37dd62e0376ecfec7b08e221bb02c37faad1ffc46ad304d30f551721b` | [crates.io](https://crates.io/crates/seq-hash); distinct from the path version. |
| seq-hash 0.2.1 | `39cb76b597a7a664c124deeee3fe68cdfb96a55a`; archive SHA-256 `530c0c667503dfc7da0b0de24d54c1538ea4df976832f68551591959ec6306ec` | Exact-version license review pending. |
| simd-minimizers | 3.0.0 `3fcb28b40f9939f783ed0351c748e1529d298579`; 3.1.0 `551220f37f91dc1f57787a6c955b8883b77798b7` | [Upstream](https://github.com/rust-seq/simd-minimizers); exact-version license review pending. |
| mod-minimizer | `61517a33b5f6b6eac7d7fd2d2ac39b1c27d28692` | [Upstream](https://github.com/RagnarGrootKoerkamp/minimizers); exact-version license review pending. |
| ensure_simd | 0.1.0 / 0.1.1 | Fixed registry checksums and dependency roles are recorded with the applicable workflows; license review pending. |
| mem_dbg / mem_dbg-derive | 0.4.3 / 0.3.3; later 0.4.4 / 0.3.4 | Earlier declarations are Apache-2.0 OR LGPL-2.1-or-later; do not substitute later license declarations. |

### Obtaining fixed optional dependencies

Use the upstream Git repository links and recorded commit identities above for
path dependencies; a path entry in `Cargo.lock` does not provide a crate
checksum. For registry dependencies, the lockfile SHA-256 applies to the exact
`.crate` archive downloaded from crates.io. Compare it before use. A lockfile
can contain optional or development packages and does not alone prove that a
particular executable used them. With an appropriate Rust toolchain and the
matching manifest available, Cargo's `--locked` mode preserves dependency
resolution; a full fresh acquisition and replay is not claimed here.

| Registry package | Version | Cargo archive SHA-256 | Source |
| --- | --- | --- | --- |
| ensure_simd | 0.1.0 | `c45a25613230d2ee8b1b68510f44ed8d765b6ef9a597d9ad5489e3d0ddfdc61d` | [crates.io](https://crates.io/crates/ensure_simd) / [upstream](https://github.com/RagnarGrootKoerkamp/ensure_simd) |
| ensure_simd | 0.1.1 | `07ba1ccb27fabd1a216eaf244833cf064337e24e2d20b5e49c52a217e1d2edeb` | [crates.io](https://crates.io/crates/ensure_simd) |
| mem_dbg | 0.4.3 | `f4ef2d80bfa14894b6d5a3ff537e7e9a908dbf4c95de8a5b8ad2a473301676e6` | [crates.io](https://crates.io/crates/mem_dbg) / [upstream](https://github.com/zommiommy/mem_dbg-rs) |
| mem_dbg-derive | 0.3.3 | `73acd151c6ce84a41d8d6fb0958d9a3d5a18d649ad5a85ad5b719439af8ad257` | [crates.io](https://crates.io/crates/mem_dbg-derive) |
| mem_dbg | 0.4.4 | `b48a1086c746f4ee6ca5cb0acf856a14709bc4d2d20e03db150a12ddf2269e6d` | [crates.io](https://crates.io/crates/mem_dbg) |
| mem_dbg-derive | 0.3.4 | `eb910efe8da52f13da727170e352e50a1764579a6fb1065d00d9556da19c79ac` | [crates.io](https://crates.io/crates/mem_dbg-derive) |

The mod-minimizer reference is obtained from its [upstream repository](https://github.com/RagnarGrootKoerkamp/minimizers) at the commit above; the available path source records do not supply a Cargo archive checksum. Likewise, the stated simd-minimizers path commits are Git identities, not registry archive checksums. Exact-version redistribution licensing for the listed pending packages has not been resolved; acquire independently rather than assuming bundled source is authorized for redistribution.

The Figure 2a, Figure 2b and Figure 4 benchmarks contain local fixed-eight-byte
MurmurHash3 and final4-style wyhash specializations. The wyhash multiplication
path requires a compiler supporting `__uint128_t`; the historical build used
C11 on x86-64 little-endian Linux. The source and license evidence, local
specialization limits and seed differences are recorded in
[third-party notices](../THIRD_PARTY_NOTICES.md); their precise direct historical
import path is not established. These are benchmark code, not core-library
dependencies. For the historical mapping-accuracy analysis, the original `scipy.stats.binom_test` is available in the checked Python 3.8.13 / SciPy 1.8.1 environment. Newer `binomtest` values showed small floating-point differences on some inputs, so a modern-interface substitution is not presented as byte-identical.
