#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
binary_relative=build/reproducibility/table2/test_exhaustive_9mer
binary="$repo_root/$binary_relative"
library="$repo_root/build/libkssd_array.a"
source_file="$script_dir/test_exhaustive_9mer.c"
output_dir=
mode=full
input_limit=262144

usage() {
    printf 'usage: %s [--output-dir DIR] [--smoke]\n' "$0"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir)
            if [[ $# -lt 2 ]]; then
                usage >&2
                exit 2
            fi
            output_dir=$2
            shift 2
            ;;
        --smoke)
            mode=smoke
            input_limit=4096
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "$output_dir" ]]; then
    output_dir=$(mktemp -d "${TMPDIR:-/tmp}/kssd-table2-validation.XXXXXX")
else
    mkdir -p -- "$output_dir"
fi

csv="$output_dir/exhaustive_9mer.csv"
log="$output_dir/exhaustive_9mer.log"
manifest="$output_dir/run_manifest.txt"
for target in "$csv" "$log" "$manifest"; do
    if [[ -e "$target" ]]; then
        printf 'refusing to overwrite output: %s\n' "$target" >&2
        exit 1
    fi
done

make -C "$repo_root" "$binary_relative"

command=("$binary" --csv "$csv")
if [[ "$mode" == smoke ]]; then
    command+=(--limit "$input_limit")
fi

{
    printf 'mode: %s\n' "$mode"
    printf 'command:'
    printf ' %q' "${command[@]}"
    printf '\n'
    "${command[@]}"
} 2>&1 | tee "$log"

{
    printf 'validation=table2_exhaustive_9mer\n'
    printf 'mode=%s\n' "$mode"
    printf 'input_limit=%s\n' "$input_limit"
    printf 'k=9\n'
    printf 'seed=42\n'
    printf 'rank_derived_api=kssd_array_init,kssd_array_map_unchecked,kssd_array_destroy\n'
    printf 'library=%s\n' "$library"
    printf 'source_sha256='
    sha256sum "$source_file" | awk '{print $1}'
    printf 'library_sha256='
    sha256sum "$library" | awk '{print $1}'
    printf 'binary_sha256='
    sha256sum "$binary" | awk '{print $1}'
    printf 'csv_sha256='
    sha256sum "$csv" | awk '{print $1}'
    printf 'log_sha256='
    sha256sum "$log" | awk '{print $1}'
} > "$manifest"

printf 'output directory: %s\n' "$output_dir"
