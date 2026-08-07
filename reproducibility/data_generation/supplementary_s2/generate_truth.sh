#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: generate_truth.sh --aln2bed PATH --data-root DIRECTORY [--verify-only]

Checks the four authoritative ART ALN files and creates the reduced historical
truth TSV compatibility views beside them. Corrected S2 uses ART ALN directly;
the TSVs intentionally do not replace strand-aware ALN truth.
EOF
}

ALN2BED=""
DATA_ROOT=""
VERIFY_ONLY=0
while (($#)); do
    case "$1" in
        --aln2bed) ALN2BED=${2:?missing value for --aln2bed}; shift 2 ;;
        --data-root) DATA_ROOT=${2:?missing value for --data-root}; shift 2 ;;
        --verify-only) VERIFY_ONLY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done
[[ -n "$ALN2BED" && -n "$DATA_ROOT" ]] || { usage >&2; exit 2; }
ALN2BED=$(readlink -f "$ALN2BED")
DATA_ROOT=$(readlink -f "$DATA_ROOT")

sha256_file() {
    sha256sum "$1" | awk '{print $1}'
}

verify_file() {
    local path=$1 expected_size=$2 expected_hash=$3 label=$4 observed_size observed_hash
    [[ -f "$path" ]] || { printf '%s is missing: %s\n' "$label" "$path" >&2; exit 1; }
    observed_size=$(wc -c < "$path")
    [[ "$observed_size" == "$expected_size" ]] || {
        printf '%s size mismatch: expected %s, observed %s\n' "$label" "$expected_size" "$observed_size" >&2
        exit 1
    }
    observed_hash=$(sha256_file "$path")
    [[ "$observed_hash" == "$expected_hash" ]] || {
        printf '%s SHA-256 mismatch: expected %s, observed %s\n' "$label" "$expected_hash" "$observed_hash" >&2
        exit 1
    }
    printf 'VERIFIED\t%s\t%s\n' "$label" "$observed_hash"
}

verify_file "$ALN2BED" 1462 \
    00b3af7203a615626c1eed7645b319c8825c1b92e52507434f4ce309bf24efe3 \
    'official ART aln2bed.pl'

HUMAN_DIR="$DATA_ROOT/seq/human"
ZEA_DIR="$DATA_ROOT/seq/Zea_mays"
HUMAN_100_ALN="$HUMAN_DIR/sim_se_100bp_500K.aln"
HUMAN_150_ALN="$HUMAN_DIR/sim_se_150bp_500K.aln"
ZEA_100_ALN="$ZEA_DIR/sim_zeamays_se_100bp_500K.aln"
ZEA_150_ALN="$ZEA_DIR/sim_zeamays_se_150bp_500K.aln"
verify_file "$HUMAN_100_ALN" 128617844 \
    0c53a3bec23d8bda9f09d66a1969e24ada536e7d01942ad0aaaf8ec962291ea0 'Human 100 bp ART ALN'
verify_file "$HUMAN_150_ALN" 180490902 \
    d202ca09f443853855d9bf767143790dc3eaf2fb9ab895be845e0c44a487a359 'Human 150 bp ART ALN'
verify_file "$ZEA_100_ALN" 117884478 \
    0cebb41ff8d4eb325bd5bde9a4f22b9413e86d0766c55878007d35105ac3f9d2 'Zea 100 bp ART ALN'
verify_file "$ZEA_150_ALN" 169284912 \
    9da15aee88ead6e46d4fb65bf49f4d9bf4a4abc81a62da7c781cce03745b1ac1 'Zea 150 bp ART ALN'

make_truth() {
    local mode=$1 input=$2 output=$3 temporary
    if ((VERIFY_ONLY == 1)); then
        return
    fi
    [[ ! -e "$output" ]] || { printf 'refusing existing truth output: %s\n' "$output" >&2; exit 1; }
    temporary=$(mktemp "${output}.tmp.XXXXXX")
    if [[ "$mode" == human ]]; then
        LC_ALL=C awk '/^>/ {gsub(/^>/, "", $1); print $2 "\t" $1 "\t" $3}' \
            "$input" > "$temporary"
    else
        LC_ALL=C awk '/^>/ {gsub(/^>/, "", $1); print $2 "\t" $1 ":" $3}' \
            "$input" > "$temporary"
    fi
    mv "$temporary" "$output"
}

HUMAN_100_TSV="$HUMAN_DIR/sim_se_100bp_500K_truth_qpos.tsv"
HUMAN_150_TSV="$HUMAN_DIR/sim_se_150bp_500K_truth_qpos.tsv"
ZEA_100_TSV="$ZEA_DIR/sim_zeamay_se_100bp_500K_truth_qpos.tsv"
ZEA_150_TSV="$ZEA_DIR/sim_zeamay_se_150bp_500K_truth_qpos.tsv"
make_truth human "$HUMAN_100_ALN" "$HUMAN_100_TSV"
make_truth human "$HUMAN_150_ALN" "$HUMAN_150_TSV"
make_truth zea "$ZEA_100_ALN" "$ZEA_100_TSV"
make_truth zea "$ZEA_150_ALN" "$ZEA_150_TSV"

verify_file "$HUMAN_100_TSV" 21176985 \
    7a7d45bedc95d396deeb33ef271d63eed31fcd956497a9931a2f04806e6aa8dd 'Human 100 bp reduced truth TSV'
verify_file "$HUMAN_150_TSV" 21118520 \
    362abd8bb5dd2a5478811958e40f9f99bb2e51ccd804fd6cac144d96aa20bae8 'Human 150 bp reduced truth TSV'
verify_file "$ZEA_100_TSV" 12999566 \
    4723ec0c7a088cf506fbadbe49cbea57e5ea11e3675a3f88d2be71539faa379d 'Zea 100 bp reduced truth TSV'
verify_file "$ZEA_150_TSV" 13019178 \
    6bec1b8b176c52a7daa5e88a8f109b2fadc4297fcc84c16a25a6c1244e833ee6 'Zea 150 bp reduced truth TSV'
printf 'S2_TRUTH_INPUTS=PASS\n'
