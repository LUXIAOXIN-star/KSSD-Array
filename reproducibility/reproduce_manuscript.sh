#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPOSITORY_ROOT}"

print_command() {
    printf '+'
    printf ' %q' "$@"
    printf '\n'
}

run() {
    print_command "$@"
    "$@"
}

require_env() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        printf 'error: environment variable %s is required\n' "${name}" >&2
        exit 2
    fi
}

require_option() {
    local wanted="$1"
    shift
    local value
    for value in "$@"; do
        [[ "${value}" == "${wanted}" || "${value}" == "${wanted}="* ]] && return 0
    done
    printf 'error: formal command requires %s\n' "${wanted}" >&2
    exit 2
}

temporary_output() {
    local parent
    parent="$(mktemp -d "${TMPDIR:-/tmp}/kssd-array-reproduction.XXXXXX")"
    printf '%s/output\n' "${parent}"
}

show_help() {
    sed -n '/^Commands:/,$p' <<'EOF'
KSSD-Array manuscript reproduction interface

Commands:
  help                              Show this help.
  status                            Show the validated-result status matrix.
  core-tests                        Run deterministic library tests.
  table2                            Run exhaustive 9-mer validation.
  figure2-smoke                     Run the Figure 2 functional smoke test.
  table4-smoke                      Run the Table 4 functional smoke test.
  figure3-smoke                     Run the Figure 3 functional smoke test.
  figure4-preflight                 Run the small Figure 4 preflight.
  minimap2-smoke                    Verify the patched Minimap2 fixture.
  minimap2-indexing-preflight       Run indexing preflight fixtures.
  minimap2-alignment-preflight      Run alignment preflight fixtures.
  all-smoke                         Run every command above.

Formal commands accept the underlying runner arguments and never run from
all-smoke. figure2-formal, table4-formal, figure3-formal, and figure4-formal
require --output-dir plus explicit dataset/condition arguments. Minimap2
formal commands require --output-dir plus the documented environment inputs.

Environment:
  NTHASH_ROOT             Installed ntHash 2.4.0 prefix for Table 4.
  MINIMAP2_SOURCE_DIR     Clean pinned Minimap2 source tree.
  PHASE5B_OUTPUT          Accepted indexing result directory for alignment.
EOF
}

command_name="${1:-help}"
shift || true

case "${command_name}" in
    help|-h|--help)
        show_help
        ;;
    status)
        run sed -n '1,260p' reproducibility/README.md
        ;;
    core-tests)
        run make test
        ;;
    table2)
        run make table2-validation
        ;;
    figure2-smoke)
        run make figure2-smoke
        ;;
    table4-smoke)
        run make table4-smoke
        ;;
    figure3-smoke)
        run make figure3-smoke
        ;;
    figure4-preflight)
        output_dir="${OUTPUT_DIR:-$(temporary_output)}"
        run make figure4-preflight FIGURE4_PREFLIGHT_OUTPUT="${output_dir}"
        ;;
    minimap2-smoke)
        require_env MINIMAP2_SOURCE_DIR
        output_dir="${MINIMAP2_SMOKE_DIR:-$(temporary_output)}"
        run make minimap2-smoke MINIMAP2_SOURCE_DIR="${MINIMAP2_SOURCE_DIR}" \
            MINIMAP2_SMOKE_DIR="${output_dir}"
        ;;
    minimap2-indexing-preflight)
        require_env MINIMAP2_SOURCE_DIR
        output_dir="${MINIMAP2_INDEXING_PREFLIGHT_DIR:-$(temporary_output)}"
        run make minimap2-indexing-preflight \
            MINIMAP2_SOURCE_DIR="${MINIMAP2_SOURCE_DIR}" \
            MINIMAP2_INDEXING_PREFLIGHT_DIR="${output_dir}"
        ;;
    minimap2-alignment-preflight)
        require_env PHASE5B_OUTPUT
        output_dir="${MINIMAP2_ALIGNMENT_PREFLIGHT_DIR:-$(temporary_output)}"
        run make minimap2-alignment-preflight PHASE5B_OUTPUT="${PHASE5B_OUTPUT}" \
            MINIMAP2_ALIGNMENT_PREFLIGHT_DIR="${output_dir}"
        ;;
    all-smoke)
        run "$0" core-tests
        run "$0" table2
        run "$0" figure2-smoke
        run "$0" table4-smoke
        run "$0" figure3-smoke
        run "$0" figure4-preflight
        run "$0" minimap2-smoke
        run "$0" minimap2-indexing-preflight
        run "$0" minimap2-alignment-preflight
        ;;
    figure2-formal)
        require_option --output-dir "$@"
        require_option --datasets "$@"
        run python3 reproducibility/figure2/run_figure2_single_thread.py "$@"
        ;;
    table4-formal)
        require_option --output-dir "$@"
        require_option --datasets "$@"
        run python3 reproducibility/table4/run_table4_nthash.py "$@"
        ;;
    figure3-formal)
        require_option --output-dir "$@"
        require_option --datasets "$@"
        run python3 reproducibility/figure3/run_figure3_multithread.py "$@"
        ;;
    figure4-formal)
        require_option --output-dir "$@"
        require_option --k-values "$@"
        require_option --sequence-lengths "$@"
        require_option --bins "$@"
        run python3 reproducibility/figure4/run_figure4_bucket_balance.py "$@"
        ;;
    minimap2-indexing-formal)
        require_env MINIMAP2_SOURCE_DIR
        require_option --output-dir "$@"
        require_option --dataset "$@"
        run python3 reproducibility/minimap2/indexing/run_supplementary_indexing.py \
            --upstream-source "${MINIMAP2_SOURCE_DIR}" "$@"
        ;;
    minimap2-alignment-formal)
        require_env PHASE5B_OUTPUT
        require_option --output-dir "$@"
        require_option --reference "$@"
        require_option --reads "$@"
        require_option --truth "$@"
        require_option --bed "$@"
        run python3 reproducibility/minimap2/alignment_consistency/run_alignment_consistency.py \
            --phase5b-output "${PHASE5B_OUTPUT}" "$@"
        ;;
    *)
        printf 'error: unknown command: %s\n' "${command_name}" >&2
        show_help >&2
        exit 2
        ;;
esac
