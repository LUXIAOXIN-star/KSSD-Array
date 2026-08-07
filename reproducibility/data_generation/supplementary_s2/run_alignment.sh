#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: run_alignment.sh --data-root DIRECTORY --phase5b-output DIRECTORY \
                        --output-dir NEW_DIRECTORY

Regenerate the historical Original Minimap2 and KSSD-Array S2 BAMs through
the repository's pinned alignment-consistency runner. This is a full alignment
workflow and is never run by CI or by input-provenance validation.
EOF
}

DATA_ROOT=""
PHASE5B_OUTPUT=""
OUTPUT_DIR=""
while (($#)); do
    case "$1" in
        --data-root) DATA_ROOT=${2:?missing value for --data-root}; shift 2 ;;
        --phase5b-output) PHASE5B_OUTPUT=${2:?missing value for --phase5b-output}; shift 2 ;;
        --output-dir) OUTPUT_DIR=${2:?missing value for --output-dir}; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n "$DATA_ROOT" && -n "$PHASE5B_OUTPUT" && -n "$OUTPUT_DIR" ]] || {
    usage >&2
    exit 2
}

DATA_ROOT=$(readlink -f "$DATA_ROOT")
PHASE5B_OUTPUT=$(readlink -f "$PHASE5B_OUTPUT")
[[ -d "$DATA_ROOT" ]] || { printf 'data root is not a directory: %s\n' "$DATA_ROOT" >&2; exit 1; }
[[ -d "$PHASE5B_OUTPUT" ]] || {
    printf 'Phase 5B output is not a directory: %s\n' "$PHASE5B_OUTPUT" >&2
    exit 1
}
[[ ! -e "$OUTPUT_DIR" ]] || {
    printf 'refusing existing output path: %s\n' "$OUTPUT_DIR" >&2
    exit 1
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
RUNNER="$REPO_ROOT/reproducibility/minimap2/alignment_consistency/run_alignment_consistency.py"
CONFIG="$REPO_ROOT/reproducibility/minimap2/alignment_consistency/config.json"

printf 'This command runs the full S2 alignment workflow; outputs remain external.\n'
KSSD_DATA_DIR="$DATA_ROOT" python3 "$RUNNER" \
    --config "$CONFIG" \
    --phase5b-output "$PHASE5B_OUTPUT" \
    --output-dir "$OUTPUT_DIR"
