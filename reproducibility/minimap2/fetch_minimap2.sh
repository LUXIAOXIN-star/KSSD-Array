#!/usr/bin/env bash
set -euo pipefail

EXPECTED_COMMIT=79c9cc186b95f50bd899f69b48eba995ced810c6

usage() {
    printf '%s\n' 'Usage: fetch_minimap2.sh SOURCE_CHECKOUT_OR_URL OUTPUT_DIRECTORY'
}

if [[ $# -ne 2 ]]; then
    usage >&2
    exit 2
fi

source_location="$1"
output_directory="$2"
if [[ -e "$output_directory" ]]; then
    printf 'output already exists: %s\n' "$output_directory" >&2
    exit 1
fi

git clone --quiet --no-checkout --no-hardlinks -- "$source_location" "$output_directory"
git -C "$output_directory" checkout --quiet --detach "$EXPECTED_COMMIT"

actual_commit="$(git -C "$output_directory" rev-parse --verify HEAD)"
if [[ "$actual_commit" != "$EXPECTED_COMMIT" ]]; then
    printf 'unexpected minimap2 commit: %s\n' "$actual_commit" >&2
    exit 1
fi
if [[ -n "$(git -C "$output_directory" status --porcelain --untracked-files=all)" ]]; then
    printf 'new minimap2 checkout is not clean: %s\n' "$output_directory" >&2
    exit 1
fi

printf 'MINIMAP2_SOURCE_DIR=%s\n' "$(cd -- "$output_directory" && pwd)"
printf 'MINIMAP2_COMMIT=%s\n' "$actual_commit"
