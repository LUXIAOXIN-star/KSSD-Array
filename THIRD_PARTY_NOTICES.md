# Third-party notices

KSSD-Array itself is licensed under `LICENSE`. Benchmark and integration
workflows interoperate with the following third-party projects; their licenses
remain controlling for their code.

## xxHash

Source: <https://github.com/Cyan4973/xxHash>. Historical rescan and scaling
workflows use the system-provided XXH64/XXH3 library; header and runtime
versions must be taken from each run's metadata. Current Figure 2a independent
scoring and the separate gxhash comparison use pinned xxHash v0.8.3 inline.
The independent-scoring package vendors that source and its license under
`reproducibility/figure2a_independent_scoring/third_party/xxhash-v0.8.3/`.
An identical header and license accompany the gxhash driver under
`reproducibility/supplementary_s1_2_gxhash/historical_source/original_phase1/third_party/xxhash-v0.8.3/`.
Copyright Yann Collet and contributors; BSD-2-Clause. Retain the bundled copyright notice,
conditions and disclaimer when redistributing the source.

Figure 2a's historical driver uses the vendored v0.8.3 header with
`XXH_INLINE_ALL` for its primary XXH3 and XXH64 curves. The same program
separately includes shared-library anchor methods; those anchors are not the
primary inline curves. Figure 2b and Figure 4 call a shared xxHash library;
their historical runs recorded runtime `XXH_versionNumber() == 703` (0.7.3).
The exact historical shared-library binary and system header hashes were not
recorded. A current runtime version must not be presented as their historical
binary identity. The v0.8.3 header's upstream commit is
`e626a72bc2321cd320e953a0ccf1584cad60f363`; its BSD 2-Clause notice and
license apply to distributions of the header. The Figure 2a driver is in
`reproducibility/figure2a_independent_scoring/`; its v0.8.3 header and license
are under that directory in `third_party/xxhash-v0.8.3/`.

For the locally installed Debian `libxxhash0` 0.7.3-1 package, the unmodified
[Debian copyright and license record](reproducibility/figure2/third_party/xxhash-runtime-0.7.3/debian-copyright)
includes the BSD-2-Clause notice for the library. This documents the local
package, not the exact file identity of the original historical installation.

## MurmurHash3

Source: <https://github.com/aappleby/smhasher>. Written by Austin Appleby and
placed in the public domain by its author. The MurmurHash3 benchmark
implementation is a local eight-byte specialization adapted from Austin
Appleby's MurmurHash3_x64_128 algorithm. In the historical rescan and thread
throughput benchmarks, the configuration is `seed = 0`, and the first 64-bit
output word is used for ordering. Figure 4 instead uses the low 32 bits of its
documented condition seed for the bucket-balance analysis. These routines are
not part of the KSSD-Array library API.

This specialization is a local rewrite, not a call to a complete upstream
MurmurHash3 library. Earlier preserved programs instead used Peter Scott's
C port, exactly matching `murmur3.c` at commit
`eb902900fc5f4cb1923727b3b5395157d17c14f9` of
<https://github.com/PeterScott/murmur3>. See the
[Figure 2a implementation notes](reproducibility/figure2a_independent_scoring/README.md)
for original-algorithm, C-port and local fixed-eight-byte source identities.
Do not assign one external implementation version to all experiment batches.

The original `MurmurHash3.cpp` contains the following author declaration:

> MurmurHash3 was written by Austin Appleby, and is placed in the public
> domain. The author hereby disclaims copyright to this source code.

Peter Scott's C port has its own upstream source and public-domain declaration;
it is cited as source evidence, not as the complete implementation used by
these three historical benchmarks. Their local fixed-eight-byte routines
implement the x64_128 algorithm's first finalized 64-bit `h1` word, on the
historical x86-64 little-endian platform. Figure 2a and Figure 2b use seed 0;
Figure 4 passes the low 32 bits of the condition seed. Their direct historical
derivation from any particular port revision is not established.

## SplitMix64 in the historical Figure 2a driver

The Figure 2a driver also contains a SplitMix64 generator whose state increment
and mixing constants correspond to Sebastiano Vigna's
[reference implementation](https://prng.di.unimi.it/splitmix.c). Its author
dedicates the work to the public domain to the extent possible and explicitly
permits use, copying, modification and distribution, with an AS-IS disclaimer.
The upstream [permission and disclaimer excerpt](reproducibility/figure2a_independent_scoring/third_party/splitmix64/UPSTREAM_PERMISSION_EXCERPT.txt)
is retained with its source attribution. The direct historical copying path is
not established; the generator is not a separate hash method in the Figure 2a primary five-method comparison.

## gxhash and its Rust dependency

Source: <https://github.com/ogxd/gxhash>. The separate eight-byte scoring
comparison uses official gxhash 3.5.0, crate SHA256
`f3ce1bab7aa741d4e7042b2aae415b78741f267a98a7271ea226cd5ba6c43d7d`,
with crate VCS identity `6438a7bc2a78d9426bea7671a044f82d3f767dc2`.
This crate identity does not imply independent verification of a GitHub tag.
gxhash is MIT-licensed. Its Rust source, license file, full adapter, lockfile,
prebuilt libraries and dependency cache are not distributed in this package.
Obtain the fixed source and its applicable license independently from upstream.
The historical build recorded `rustversion` 1.0.23 (MIT OR Apache-2.0); the
complete locked build is not provided as a self-contained replay.

## wyhash

Source: <https://github.com/wangyi-fudan/wyhash>. Copyright Wang Yi and
contributors; distributed under The Unlicense. The benchmark uses a wyhash
final4-style fixed-width adaptation for an eight-byte input. Its secret is
generated by `wy_make_secret` from the recorded run seed. The default recorded
seed for the historical rescan and thread workflows is 42; Figure 4 uses its
documented deterministic condition seed. The hash adaptation uses zero input
seed semantics. These routines are not part of the KSSD-Array library API.

The corresponding final4 reference is upstream commit
`ea3b25e1aef55d90f707c3a292eeb9162e2615d8`, distributed with The Unlicense.
The local benchmark code specializes the 8-byte input path and uses the
`__uint128_t` multiplication path; other upstream input lengths, platform and
configuration branches are omitted. It is not the complete upstream
`wyhash.h`. Figure 2a/2b use 42 to generate the secret and 0 as the hash input
seed; Figure 4 uses the condition seed to generate the secret and 0 as the
hash input seed. The matching [The Unlicense text](reproducibility/figure2a_independent_scoring/third_party/wyhash-final4/LICENSE)
is retained with the historical driver; retain it when redistributing the
specialization.

## ntHash

Source: <https://github.com/bcgsc/ntHash>. Version 2.4.0, commit
`c26bd4572a19de81e30d55042dbd33c1fd21d4b6`. ntHash is MIT-licensed. Current Table 2 and Supplementary Table S3 use the independent canonical
rolling/common-selector protocol. The source subset required by that protocol,
including its upstream LICENSE, is included under
`reproducibility/table2_nthash/third_party/nthash/`. Legacy Table 4 workflows
have separate setup rules.
Distributions must retain ntHash copyright and permission notices.

## Minimap2

Source: <https://github.com/lh3/minimap2>. Version 2.30-r1287, commit
`79c9cc186b95f50bd899f69b48eba995ced810c6`. Minimap2 is MIT-licensed,
copyright Dana-Farber Cancer Institute, Broad Institute, Inc., and
contributors. The committed patch contains modifications against that
upstream work. Upstream source and binaries are not redistributed here; users
must retain Minimap2's license notice when distributing a patched build.

### Minimap2 2.30 upstream license

```text
The MIT License

Copyright (c) 2018-     Dana-Farber Cancer Institute
              2017-2018 Broad Institute, Inc.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Runtime and plotting tools

zlib, OpenMP runtimes, Python packages, R, ggplot2, samtools, bedtools, and
ART_Illumina are external tools and are not vendored. Their own licenses apply
when installed or redistributed. The repository's scripts contain no copied
source from these packages.

## seq-hash and simd-minimizers

Official sources: <https://github.com/RagnarGrootKoerkamp/seq-hash> and
<https://github.com/RagnarGrootKoerkamp/simd-minimizers>. The ten-megabase
comparison pins seq-hash `4cd7eed354923f908e8d284a93a359a899199d2c` for
A/B and simd-minimizers `3fcb28b40f9939f783ed0351c748e1529d298579` for C.
C uses a separately pinned registry seq-hash dependency. The relevant historical
Cargo metadata declared MIT, but the exact-version license evidence remains
unresolved. These third-party source snapshots are not distributed here; obtain
the fixed versions independently and check their applicable terms. The saved
results do not constitute a complete executable replay.

## GreedyMini and low-density reference methods

GreedyMini source: <https://github.com/OrensteinLab/GreedyMini>, commit
`a67eb90dc278ea78111a76d5813cf2ac7662b0ae`. Obtain the corresponding upstream
source, license and precomputed orders independently; they are not included
here. Prefix extensions are local adapters; they are not native orders
optimized for the target k. mod-minimizer source:
<https://github.com/RagnarGrootKoerkamp/minimizers>, commit
`61517a33b5f6b6eac7d7fd2d2ac39b1c27d28692`. The frozen Cargo metadata
declares MIT, without a standalone LICENSE in that preserved source portion.
The streaming and materialized-score comparisons use separate dependency
identities and local adapters; their complete external dependency sets are not
bundled.
