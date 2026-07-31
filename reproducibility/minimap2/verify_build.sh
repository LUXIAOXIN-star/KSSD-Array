#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FETCH_SCRIPT="$SCRIPT_DIR/fetch_minimap2.sh"
APPLY_SCRIPT="$SCRIPT_DIR/patch/apply_patch.sh"
PATCH_FILE="$SCRIPT_DIR/patch/minimap2-v2.30-kssd-array.patch"
EXPECTED_COMMIT=79c9cc186b95f50bd899f69b48eba995ced810c6

usage() {
    cat <<'USAGE'
Usage:
  verify_build.sh --build-only MINIMAP2_SOURCE KSSD_ARRAY_ROOT OUTPUT_DIRECTORY
  verify_build.sh --smoke      MINIMAP2_SOURCE KSSD_ARRAY_ROOT OUTPUT_DIRECTORY

The output directory must not already exist and must be outside KSSD_ARRAY_ROOT.
MINIMAP2_SOURCE may be a local checkout or an explicitly selected Git URL.

Environment:
  JOBS=N  Parallel compiler jobs (default: 2)
USAGE
}

if [[ $# -ne 4 ]]; then
    usage >&2
    exit 2
fi

mode="$1"
source_location="$2"
kssd_array_root="$(cd -- "$3" && pwd)"
requested_output="$4"
jobs="${JOBS:-2}"
case "$mode" in
    --build-only|--smoke) ;;
    *) usage >&2; exit 2 ;;
esac
if [[ ! "$jobs" =~ ^[1-9][0-9]*$ ]]; then
    printf 'JOBS must be a positive integer: %s\n' "$jobs" >&2
    exit 2
fi
test -f "$kssd_array_root/include/kssd_array.h"

output_parent="$(dirname -- "$requested_output")"
output_name="$(basename -- "$requested_output")"
mkdir -p -- "$output_parent"
output_parent="$(cd -- "$output_parent" && pwd)"
output_directory="$output_parent/$output_name"
if [[ -e "$output_directory" ]]; then
    printf 'output directory already exists: %s\n' "$output_directory" >&2
    exit 1
fi
case "$output_directory/" in
    "$kssd_array_root/"*)
        printf 'verification output must be outside KSSD_ARRAY_ROOT\n' >&2
        exit 1
        ;;
esac

mkdir -p -- "$output_directory/logs" "$output_directory/results"
upstream="$output_directory/upstream"
patched="$output_directory/patched"
"$FETCH_SCRIPT" "$source_location" "$upstream" \
    >"$output_directory/logs/fetch-upstream.log" 2>&1
"$FETCH_SCRIPT" "$source_location" "$patched" \
    >"$output_directory/logs/fetch-patched.log" 2>&1
"$APPLY_SCRIPT" --apply "$patched" \
    >"$output_directory/logs/apply-patch.log" 2>&1
git -C "$patched" diff --check

make -C "$kssd_array_root" -j"$jobs" build/libkssd_array.a \
    >"$output_directory/logs/build-kssd-array.log" 2>&1
make -C "$upstream" -j"$jobs" \
    >"$output_directory/logs/build-upstream.log" 2>&1
make -C "$patched" -j"$jobs" KSSD_ARRAY_ROOT="$kssd_array_root" \
    >"$output_directory/logs/build-integrated.log" 2>&1

test -x "$upstream/minimap2"
test -x "$patched/minimap2"
upstream_version="$($upstream/minimap2 --version)"
integrated_version="$($patched/minimap2 --version)"
[[ "$upstream_version" == "2.30-r1287" ]]
[[ "$integrated_version" == "2.30-r1287+KSSD-Array" ]]

nm -g "$patched/minimap2" >"$output_directory/results/integrated-nm.txt"
ldd "$patched/minimap2" >"$output_directory/results/integrated-ldd.txt"
readelf -Ws "$patched/minimap2" \
    >"$output_directory/results/integrated-readelf-symbols.txt"
objdump -d --disassemble=mm_sketch "$patched/minimap2" \
    >"$output_directory/results/integrated-mm-sketch-objdump.txt"
grep -Eq ' [Tt] kssd_array_init_with_rng$' \
    "$output_directory/results/integrated-nm.txt"
grep -Eq ' [Tt] kssd_array_map_unchecked$' \
    "$output_directory/results/integrated-nm.txt"
grep -Eq ' [Tt] kssd_array_inline_plan_init$' \
    "$output_directory/results/integrated-nm.txt"
grep -Eq ' [Tt] kssd_array_destroy$' \
    "$output_directory/results/integrated-nm.txt"
if grep -Fq 'libkssd_array.so' "$output_directory/results/integrated-ldd.txt"; then
    printf 'integrated executable has a dynamic KSSD-Array dependency\n' >&2
    exit 1
fi
if grep -Eq ' [Tt] mm_kssd_array_map_unchecked$' \
        "$output_directory/results/integrated-nm.txt"; then
    printf 'obsolete Minimap2 KSSD mapping adapter remains in executable\n' >&2
    exit 1
fi
if grep -Eq 'call[^<]*<(mm_kssd_array_map_unchecked|kssd_array_map_unchecked)>' \
        "$output_directory/results/integrated-mm-sketch-objdump.txt"; then
    printf 'mm_sketch still calls an out-of-line KSSD mapper\n' >&2
    exit 1
fi
if rg -n 'src/kssd_array\.c|src/permutation\.c' "$patched/Makefile"; then
    printf 'patched build compiles KSSD core sources directly\n' >&2
    exit 1
fi

patch_sha256="$(sha256sum "$PATCH_FILE" | awk '{print $1}')"
library_sha256="$(sha256sum "$kssd_array_root/build/libkssd_array.a" | awk '{print $1}')"
upstream_binary_sha256="$(sha256sum "$upstream/minimap2" | awk '{print $1}')"
integrated_binary_sha256="$(sha256sum "$patched/minimap2" | awk '{print $1}')"
cat >"$output_directory/build_manifest.txt" <<EOF
UPSTREAM_COMMIT=$EXPECTED_COMMIT
UPSTREAM_VERSION=$upstream_version
INTEGRATED_VERSION=$integrated_version
PATCH_SHA256=$patch_sha256
LIBKSSD_ARRAY_SHA256=$library_sha256
UPSTREAM_BINARY_SHA256=$upstream_binary_sha256
INTEGRATED_BINARY_SHA256=$integrated_binary_sha256
KSSD_INCLUDE_FLAG=-I${kssd_array_root}/include
KSSD_LINK_FLAGS=-L${kssd_array_root}/build -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic
JOBS=$jobs
EOF

printf 'ORIGINAL_BUILD=PASS\n'
printf 'INTEGRATED_BUILD=PASS\n'
printf 'INTEGRATED_VERSION=%s\n' "$integrated_version"
printf 'PUBLIC_LIBRARY_LINK=PASS\n'
printf 'INLINE_HOT_PATH=PASS\n'
if [[ "$mode" == "--build-only" ]]; then
    printf 'BUILD_VERIFICATION=PASS\n'
    printf 'OUTPUT_DIRECTORY=%s\n' "$output_directory"
    exit 0
fi

reference="$SCRIPT_DIR/fixtures/reference.fa"
query="$SCRIPT_DIR/fixtures/query.fa"
probe_source="$SCRIPT_DIR/fixtures/ambiguous_reset_probe.c"
grep -Eq '[Nn]' "$reference"
grep -Eq '[Nn]' "$query"
grep -Eq 'A{10}|C{10}|G{10}|T{10}' "$reference"

standard_index="$output_directory/results/standard.mmi"
index_t1="$output_directory/results/kssd-array-t1.mmi"
index_t4="$output_directory/results/kssd-array-t4.mmi"
"$upstream/minimap2" -k9 -w5 -t1 -d "$standard_index" "$reference" \
    >"$output_directory/logs/standard-index.stdout" \
    2>"$output_directory/logs/standard-index.stderr"
"$patched/minimap2" -k9 -w5 -t1 -d "$index_t1" "$reference" \
    >"$output_directory/logs/index-t1.stdout" \
    2>"$output_directory/logs/index-t1.stderr"
"$patched/minimap2" -k9 -w5 -t4 -d "$index_t4" "$reference" \
    >"$output_directory/logs/index-t4.stdout" \
    2>"$output_directory/logs/index-t4.stderr"
test -s "$standard_index"
test -s "$index_t1"
test -s "$index_t4"
cmp "$index_t1" "$index_t4"

index_t1_sha256="$(sha256sum "$index_t1" | awk '{print $1}')"
index_t4_sha256="$(sha256sum "$index_t4" | awk '{print $1}')"
[[ "$index_t1_sha256" == "$index_t4_sha256" ]]
magic="$(od -An -tx1 -N4 "$index_t1" | tr -d '[:space:]')"
[[ "$magic" == "4b534101" ]]

paf_t1_i1="$output_directory/results/index-t1-align-t1.paf"
paf_t1_i4="$output_directory/results/index-t1-align-t4.paf"
paf_t4_i1="$output_directory/results/index-t4-align-t1.paf"
paf_t4_i4="$output_directory/results/index-t4-align-t4.paf"
"$patched/minimap2" -t1 "$index_t1" "$query" >"$paf_t1_i1" \
    2>"$output_directory/logs/index-t1-align-t1.stderr"
"$patched/minimap2" -t4 "$index_t1" "$query" >"$paf_t1_i4" \
    2>"$output_directory/logs/index-t1-align-t4.stderr"
"$patched/minimap2" -t1 "$index_t4" "$query" >"$paf_t4_i1" \
    2>"$output_directory/logs/index-t4-align-t1.stderr"
"$patched/minimap2" -t4 "$index_t4" "$query" >"$paf_t4_i4" \
    2>"$output_directory/logs/index-t4-align-t4.stderr"
test -s "$paf_t1_i1"
cmp "$paf_t1_i1" "$paf_t1_i4"
cmp "$paf_t1_i1" "$paf_t4_i1"
cmp "$paf_t1_i1" "$paf_t4_i4"
paf_sha256="$(sha256sum "$paf_t1_i1" | awk '{print $1}')"

hpc_t1="$output_directory/results/hpc-t1.paf"
hpc_t4="$output_directory/results/hpc-t4.paf"
"$patched/minimap2" -H -k9 -w5 -t1 "$reference" "$query" >"$hpc_t1" \
    2>"$output_directory/logs/hpc-t1.stderr"
"$patched/minimap2" -H -k9 -w5 -t4 "$reference" "$query" >"$hpc_t4" \
    2>"$output_directory/logs/hpc-t4.stderr"
test -s "$hpc_t1"
cmp "$hpc_t1" "$hpc_t4"
hpc_sha256="$(sha256sum "$hpc_t1" | awk '{print $1}')"

probe="$output_directory/results/ambiguous-reset-probe"
cc -O2 -std=c11 -Wall -Wextra -Wpedantic \
    -I"$patched" -I"$kssd_array_root/include" "$probe_source" \
    -L"$patched" -lminimap2 \
    -L"$kssd_array_root/build" -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic \
    -lm -lz -lpthread -o "$probe"
"$probe" >"$output_directory/results/ambiguous-reset.txt"
grep -Fxq 'AMBIGUOUS_MINIMIZERS=0' \
    "$output_directory/results/ambiguous-reset.txt"
awk -F= '$1 == "JOINED_MINIMIZERS" && $2 > 0 { found=1 } END { exit !found }' \
    "$output_directory/results/ambiguous-reset.txt"

if "$patched/minimap2" "$standard_index" "$query" \
    >"$output_directory/results/standard-with-integrated.paf" \
    2>"$output_directory/logs/standard-with-integrated.stderr"; then
    printf 'integrated executable accepted a standard index\n' >&2
    exit 1
fi
grep -Fq 'standard minimap2 index is incompatible with KSSD-Array' \
    "$output_directory/logs/standard-with-integrated.stderr"

invalid_version="$output_directory/results/kssd-array-version2.mmi"
cp -- "$index_t1" "$invalid_version"
printf '\002' | dd of="$invalid_version" bs=1 seek=3 conv=notrunc status=none
if "$patched/minimap2" "$invalid_version" "$query" \
    >"$output_directory/results/version2-with-integrated.paf" \
    2>"$output_directory/logs/version2-with-integrated.stderr"; then
    printf 'integrated executable accepted an unsupported index version\n' >&2
    exit 1
fi
grep -Fq 'unsupported KSSD-Array index version 2' \
    "$output_directory/logs/version2-with-integrated.stderr"

set +e
"$upstream/minimap2" "$index_t1" "$query" \
    >"$output_directory/results/kssd-with-upstream.paf" \
    2>"$output_directory/logs/kssd-with-upstream.stderr"
reverse_upstream_status=$?
set -e
if [[ -s "$output_directory/results/kssd-with-upstream.paf" ]]; then
    printf 'upstream executable produced alignments from a KSSD-Array index\n' >&2
    exit 1
fi
test -s "$output_directory/logs/kssd-with-upstream.stderr"

reference_sha256="$(sha256sum "$reference" | awk '{print $1}')"
query_sha256="$(sha256sum "$query" | awk '{print $1}')"
cat >"$output_directory/smoke_manifest.txt" <<EOF
REFERENCE_SHA256=$reference_sha256
QUERY_SHA256=$query_sha256
INDEX_T1_SHA256=$index_t1_sha256
INDEX_T4_SHA256=$index_t4_sha256
PAF_SHA256=$paf_sha256
HPC_PAF_SHA256=$hpc_sha256
INDEX_THREADS_REQUESTED=1,4
INDEX_THREADS_OBSERVED=not_exposed_by_minimap2_cli
ALIGNMENT_THREADS_REQUESTED=1,4
ALIGNMENT_THREADS_OBSERVED=not_exposed_by_minimap2_cli
INDEX_THREAD_CONSISTENCY=PASS
ALIGNMENT_THREAD_CONSISTENCY=PASS
AMBIGUOUS_BASE_HANDLING=PASS
HPC_SMOKE=PASS
INDEX_COMPATIBILITY_CHECK=PASS
REVERSE_UPSTREAM_EXIT_STATUS=$reverse_upstream_status
REVERSE_UPSTREAM_PAF_BYTES=0
REVERSE_COMPATIBILITY_NOTE=upstream_does_not_recognize_KSA_magic_and_may_parse_it_as_sequence_input
EOF

printf 'INDEX_T1_SHA256=%s\n' "$index_t1_sha256"
printf 'INDEX_T4_SHA256=%s\n' "$index_t4_sha256"
printf 'PAF_SHA256=%s\n' "$paf_sha256"
printf 'INDEX_THREAD_CONSISTENCY=PASS\n'
printf 'ALIGNMENT_THREAD_CONSISTENCY=PASS\n'
printf 'AMBIGUOUS_BASE_HANDLING=PASS\n'
printf 'HPC_SMOKE=PASS\n'
printf 'INDEX_COMPATIBILITY_CHECK=PASS\n'
printf 'OUTPUT_DIRECTORY=%s\n' "$output_directory"
