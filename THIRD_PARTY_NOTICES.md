# Third-party notices

KSSD-Array itself is licensed under `LICENSE`. Benchmark and integration
workflows interoperate with the following third-party projects; their licenses
remain controlling for their code.

## xxHash

Source: <https://github.com/Cyan4973/xxHash>. Figures 2--4 link the system
library and call XXH64/XXH3. Copyright Yann Collet and contributors. The
library source is BSD-2-Clause. Redistributed source or binaries must retain
the copyright notice, conditions, and disclaimer. No xxHash source or binary
is committed here.

## MurmurHash3

Source: <https://github.com/aappleby/smhasher>. Written by Austin Appleby and
placed in the public domain by its author. Benchmark-local fixed-width routines
are adapted from the x64 algorithm for an eight-byte input. They are not part
of the KSSD-Array library API.

## Wyhash

Source: <https://github.com/wangyi-fudan/wyhash>. Copyright Wang Yi and
contributors; distributed under The Unlicense. Benchmark-local fixed-width
routines are adapted for an eight-byte input. They are not part of the
KSSD-Array library API.

## ntHash

Source: <https://github.com/bcgsc/ntHash>. Version 2.4.0, commit
`c26bd4572a19de81e30d55042dbd33c1fd21d4b6`. ntHash is MIT-licensed. Table 4
links a separately prepared installation; its source, headers, and binary are
not tracked by this repository. Distributions that bundle ntHash must retain
its copyright and permission notice.

## Minimap2

Source: <https://github.com/lh3/minimap2>. Version 2.30-r1287, commit
`79c9cc186b95f50bd899f69b48eba995ced810c6`. Minimap2 is MIT-licensed,
copyright Dana-Farber Cancer Institute, Broad Institute, Inc., and
contributors. The committed patch contains modifications against that
upstream work. Upstream source and binaries are not redistributed here; users
must retain Minimap2's license notice when distributing a patched build.

## Runtime and plotting tools

zlib, OpenMP runtimes, Python packages, R, ggplot2, samtools, bedtools, and
ART_Illumina are external tools and are not vendored. Their own licenses apply
when installed or redistributed. The repository's scripts contain no copied
source from these packages.
