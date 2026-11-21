#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/fixture_generator.c"
DEFAULT_MANIFEST="$SCRIPT_DIR/expected_sha256.tsv"

usage() {
    cat <<'USAGE'
Usage: generate_test_fixtures.sh --output-dir DIRECTORY [--seed 42] [--manifest FILE]

Compile the public C generator in a temporary build directory, generate all six
fixtures below DIRECTORY, and verify their SHA-256 values. The output directory
must not already contain any generated fixture path.
USAGE
}

output_directory=
seed=42
manifest="$DEFAULT_MANIFEST"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir)
            [[ $# -ge 2 ]] || { usage >&2; exit 2; }
            output_directory="$2"
            shift 2
            ;;
        --seed)
            [[ $# -ge 2 ]] || { usage >&2; exit 2; }
            seed="$2"
            shift 2
            ;;
        --manifest)
            [[ $# -ge 2 ]] || { usage >&2; exit 2; }
            manifest="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

[[ -n "$output_directory" ]] || { usage >&2; exit 2; }
[[ -f "$SOURCE" ]] || { printf 'missing generator source: %s\n' "$SOURCE" >&2; exit 1; }
[[ -f "$manifest" ]] || { printf 'missing expected-hash manifest: %s\n' "$manifest" >&2; exit 1; }

compiler="${CC:-cc}"
if ! command -v -- "$compiler" >/dev/null 2>&1; then
    printf 'C compiler is unavailable: %s\n' "$compiler" >&2
    exit 1
fi

output_directory="$(realpath -m -- "$output_directory")"
while IFS=$'\t' read -r expected relative; do
    [[ -n "$expected" && -n "$relative" ]] || continue
    if [[ -e "$output_directory/$relative" ]]; then
        printf 'refusing to overwrite generated fixture: %s\n' \
            "$output_directory/$relative" >&2
        exit 1
    fi
    mkdir -p -- "$(dirname -- "$output_directory/$relative")"
done <"$manifest"

build_directory="$(mktemp -d "${TMPDIR:-/tmp}/kssd-fixture-generator.XXXXXX")"
cleanup() {
    rm -rf -- "$build_directory"
}
trap cleanup EXIT HUP INT TERM
binary="$build_directory/fixture_generator"

LC_ALL=C "$compiler" -O2 -std=c11 -Wall -Wextra -Wpedantic \
    "$SOURCE" -o "$binary"
LC_ALL=C TZ=UTC "$binary" "$output_directory" "$seed"

verification_manifest="$build_directory/expected.sha256"
while IFS=$'\t' read -r expected relative; do
    [[ -n "$expected" && -n "$relative" ]] || continue
    printf '%s  %s\n' "$expected" "$relative" >>"$verification_manifest"
done <"$manifest"
(
    cd -- "$output_directory"
    LC_ALL=C sha256sum --check --strict "$verification_manifest"
)
printf 'FIXTURE_HASHES=PASS\n'
printf 'OUTPUT_DIRECTORY=%s\n' "$output_directory"
