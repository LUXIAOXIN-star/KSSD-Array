#!/bin/sh
set -eu

binary=${1:?usage: test_build_minimizers.sh PATH_TO_EXAMPLE}
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/kssd-minimizers-test.XXXXXX")
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM

cat >"$tmpdir/expected" <<'EOF'
sequence: ACGTACGTTGCAACGT
window 0: position=2 value=259
window 1: position=2 value=259
window 2: position=2 value=259
window 3: position=3 value=289
window 4: position=7 value=90
window 5: position=7 value=90
window 6: position=7 value=90
window 7: position=7 value=90
window 8: position=11 value=57
EOF

"$binary" >"$tmpdir/default" 2>"$tmpdir/stderr"
test ! -s "$tmpdir/stderr"
cmp "$tmpdir/expected" "$tmpdir/default"
"$binary" ACGTACGTTGCAACGT >"$tmpdir/explicit" 2>"$tmpdir/stderr"
test ! -s "$tmpdir/stderr"
cmp "$tmpdir/expected" "$tmpdir/explicit"

check_invalid() {
    sequence=$1
    offset=$2
    if "$binary" "$sequence" >"$tmpdir/stdout" 2>"$tmpdir/stderr"; then
        echo "invalid sequence unexpectedly succeeded: $sequence" >&2
        exit 1
    fi
    test ! -s "$tmpdir/stdout"
    grep -F "invalid DNA base at offset $offset: expected A/C/G/T" "$tmpdir/stderr" >/dev/null
}

check_invalid NACGTACGTTGCAACGT 0
check_invalid ACGTACGNTGCAACGT 7
check_invalid ACGTACGTTGCAACGN 15
check_invalid N 0

if "$binary" ACGT >"$tmpdir/stdout" 2>"$tmpdir/stderr"; then
    echo "short sequence unexpectedly succeeded" >&2
    exit 1
fi
test ! -s "$tmpdir/stdout"
grep -F 'sequence must contain at least 5 bases' "$tmpdir/stderr" >/dev/null
echo 'PASS: minimizer example validates its complete input before output'
