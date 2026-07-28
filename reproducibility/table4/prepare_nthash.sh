#!/usr/bin/env bash
set -euo pipefail

readonly NTHASH_VERSION="2.4.0"
readonly NTHASH_COMMIT="c26bd4572a19de81e30d55042dbd33c1fd21d4b6"
readonly NTHASH_REPOSITORY="https://github.com/BirolLab/ntHash.git"
readonly VERIFIED_HEADER_SHA="7ce43aded7fae6446578994ce91d0e65df889916e6ce556ce90945493f5b2099"
readonly VERIFIED_LIBRARY_SHA="cdf6d9ba2b7b7fbda6b1d4d3e06628b23aeadd7b96f586b13f0b7e15fd565d4a"
readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly DEFAULT_PREFIX="${REPOSITORY_ROOT}/third_party/ntHash/install"

source_prefix=""
install_prefix="${DEFAULT_PREFIX}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source-prefix)
            source_prefix="$2"
            shift 2
            ;;
        --prefix)
            install_prefix="$2"
            shift 2
            ;;
        --help)
            echo "usage: $0 [--source-prefix INSTALLED_PREFIX] [--prefix OUTPUT_PREFIX]"
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

mkdir -p "${install_prefix}/include/nthash" "${install_prefix}/lib"

if [[ -n "${source_prefix}" ]]; then
    test -f "${source_prefix}/include/nthash/nthash.hpp"
    test -f "${source_prefix}/lib/libnthash.a"
    source_header_sha="$(sha256sum "${source_prefix}/include/nthash/nthash.hpp" | awk '{print $1}')"
    source_library_sha="$(sha256sum "${source_prefix}/lib/libnthash.a" | awk '{print $1}')"
    if [[ "${source_header_sha}" != "${VERIFIED_HEADER_SHA}" || \
          "${source_library_sha}" != "${VERIFIED_LIBRARY_SHA}" ]]; then
        echo "source prefix does not match the audited historical ntHash installation" >&2
        exit 1
    fi
    install -m 0644 "${source_prefix}/include/nthash/nthash.hpp" \
        "${install_prefix}/include/nthash/nthash.hpp"
    install -m 0644 "${source_prefix}/lib/libnthash.a" \
        "${install_prefix}/lib/libnthash.a"
else
    readonly source_dir="${REPOSITORY_ROOT}/third_party/ntHash/source"
    readonly build_dir="${REPOSITORY_ROOT}/third_party/ntHash/build"
    if [[ ! -d "${source_dir}/.git" ]]; then
        git clone "${NTHASH_REPOSITORY}" "${source_dir}"
    fi
    git -C "${source_dir}" fetch --tags origin
    git -C "${source_dir}" checkout --detach "${NTHASH_COMMIT}"
    if command -v meson >/dev/null 2>&1; then
        if [[ -f "${build_dir}/meson-private/coredata.dat" ]]; then
            meson setup --wipe --buildtype=release --prefix="${install_prefix}" \
                "${build_dir}" "${source_dir}"
        else
            meson setup --buildtype=release --prefix="${install_prefix}" \
                "${build_dir}" "${source_dir}"
        fi
        meson compile -C "${build_dir}"
        meson install -C "${build_dir}"
    else
        readonly cxx="${CXX:-c++}"
        readonly archive_tool="${AR:-ar}"
        readonly index_tool="${RANLIB:-ranlib}"
        mkdir -p "${build_dir}"
        "${cxx}" -std=c++17 -O3 -Wall -Wextra -Wpedantic \
            -I"${source_dir}/include" -c "${source_dir}/src/kmer.cpp" \
            -o "${build_dir}/kmer.o"
        "${cxx}" -std=c++17 -O3 -Wall -Wextra -Wpedantic \
            -I"${source_dir}/include" -c "${source_dir}/src/seed.cpp" \
            -o "${build_dir}/seed.o"
        "${archive_tool}" rcs "${install_prefix}/lib/libnthash.a" \
            "${build_dir}/kmer.o" "${build_dir}/seed.o"
        "${index_tool}" "${install_prefix}/lib/libnthash.a"
        install -m 0644 "${source_dir}/include/nthash/nthash.hpp" \
            "${install_prefix}/include/nthash/nthash.hpp"
    fi
fi

actual_header_sha="$(sha256sum "${install_prefix}/include/nthash/nthash.hpp" | awk '{print $1}')"
actual_library_sha="$(sha256sum "${install_prefix}/lib/libnthash.a" | awk '{print $1}')"
echo "Prepared ntHash ${NTHASH_VERSION} (${NTHASH_COMMIT})"
echo "Prefix: ${install_prefix}"
echo "Header SHA256: ${actual_header_sha}"
echo "Library SHA256: ${actual_library_sha}"
