#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FETCH_SCRIPT="$SCRIPT_DIR/fetch_minimap2.sh"
APPLY_SCRIPT="$SCRIPT_DIR/patch/apply_patch.sh"

usage() {
    cat <<'USAGE'
Usage:
  build_minimap2.sh original SOURCE_CHECKOUT_OR_URL BUILD_DIRECTORY
  build_minimap2.sh integrated SOURCE_CHECKOUT_OR_URL BUILD_DIRECTORY KSSD_ARRAY_ROOT

Environment:
  JOBS=N  Parallel compiler jobs (default: 2)
USAGE
}

if [[ $# -lt 3 || $# -gt 4 ]]; then
    usage >&2
    exit 2
fi

mode="$1"
source_location="$2"
build_directory="$3"
jobs="${JOBS:-2}"
if [[ ! "$jobs" =~ ^[1-9][0-9]*$ ]]; then
    printf 'JOBS must be a positive integer: %s\n' "$jobs" >&2
    exit 2
fi
case "$mode" in
    original)
        [[ $# -eq 3 ]] || { usage >&2; exit 2; }
        ;;
    integrated)
        [[ $# -eq 4 ]] || { usage >&2; exit 2; }
        kssd_array_root="$(cd -- "$4" && pwd)"
        test -f "$kssd_array_root/include/kssd_array.h"
        make -C "$kssd_array_root" -j"$jobs" build/libkssd_array.a
        ;;
    *) usage >&2; exit 2 ;;
esac

if [[ -e "$build_directory" ]]; then
    printf 'build directory already exists: %s\n' "$build_directory" >&2
    exit 1
fi
mkdir -p -- "$build_directory"
build_directory="$(cd -- "$build_directory" && pwd)"
source_directory="$build_directory/source"
"$FETCH_SCRIPT" "$source_location" "$source_directory"

if [[ "$mode" == "integrated" ]]; then
    "$APPLY_SCRIPT" --apply "$source_directory"
    make -C "$source_directory" -j"$jobs" KSSD_ARRAY_ROOT="$kssd_array_root"
else
    make -C "$source_directory" -j"$jobs"
fi

test -x "$source_directory/minimap2"
printf 'BUILD_MODE=%s\n' "$mode"
printf 'BUILD_SOURCE=%s\n' "$source_directory"
printf 'EXECUTABLE=%s\n' "$source_directory/minimap2"
printf 'VERSION=%s\n' "$($source_directory/minimap2 --version)"
