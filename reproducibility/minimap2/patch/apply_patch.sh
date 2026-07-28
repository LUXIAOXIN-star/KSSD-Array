#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PATCH_FILE="$SCRIPT_DIR/minimap2-v2.30-kssd-array.patch"
EXPECTED_COMMIT=79c9cc186b95f50bd899f69b48eba995ced810c6

usage() {
    cat <<'USAGE'
Usage:
  apply_patch.sh --check MINIMAP2_SOURCE_DIR
  apply_patch.sh --apply MINIMAP2_SOURCE_DIR
USAGE
}

if [[ $# -ne 2 ]]; then
    usage >&2
    exit 2
fi

mode="$1"
target="$2"
case "$mode" in
    --check|--apply) ;;
    *) usage >&2; exit 2 ;;
esac

if [[ ! -d "$target/.git" && ! -f "$target/.git" ]]; then
    printf 'not a Git checkout: %s\n' "$target" >&2
    exit 1
fi
actual_commit="$(git -C "$target" rev-parse --verify HEAD)"
if [[ "$actual_commit" != "$EXPECTED_COMMIT" ]]; then
    printf 'unsupported minimap2 commit: %s (expected %s)\n' \
        "$actual_commit" "$EXPECTED_COMMIT" >&2
    exit 1
fi
if [[ -n "$(git -C "$target" status --porcelain --untracked-files=all)" ]]; then
    printf 'refusing to patch a non-clean checkout: %s\n' "$target" >&2
    exit 1
fi

git -C "$target" apply --check "$PATCH_FILE"
if [[ "$mode" == "--apply" ]]; then
    git -C "$target" apply "$PATCH_FILE"
    printf 'PATCH_APPLIED=%s\n' "$PATCH_FILE"
else
    printf 'PATCH_CHECK=PASS\n'
fi
