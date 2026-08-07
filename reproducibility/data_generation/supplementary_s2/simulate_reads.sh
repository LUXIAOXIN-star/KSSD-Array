#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: simulate_reads.sh --art PATH --data-root DIRECTORY [--verify-only]

DIRECTORY must contain:
  seq/human/GCF_000001405.40_GRCh38.p14_genomic.fna
  seq/Zea_mays/Zm-B73-REFERENCE-NAM-5.0.fa

Without --verify-only, the four exact ART_Illumina 2.5.8 simulations are
written beside their reference. Existing FASTQ or ALN outputs are refused.
EOF
}

ART=""
DATA_ROOT=""
VERIFY_ONLY=0
while (($#)); do
    case "$1" in
        --art) ART=${2:?missing value for --art}; shift 2 ;;
        --data-root) DATA_ROOT=${2:?missing value for --data-root}; shift 2 ;;
        --verify-only) VERIFY_ONLY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n "$ART" && -n "$DATA_ROOT" ]] || { usage >&2; exit 2; }
ART=$(readlink -f "$ART")
DATA_ROOT=$(readlink -f "$DATA_ROOT")
[[ -x "$ART" ]] || { printf 'ART executable is missing or not executable: %s\n' "$ART" >&2; exit 1; }
[[ -d "$DATA_ROOT" ]] || { printf 'data root is not a directory: %s\n' "$DATA_ROOT" >&2; exit 1; }

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

verify_fastq_count() {
    local path=$1 expected=$2 label=$3 lines
    lines=$(wc -l < "$path")
    ((lines % 4 == 0)) || { printf '%s FASTQ line count is not divisible by four\n' "$label" >&2; exit 1; }
    [[ "$((lines / 4))" == "$expected" ]] || {
        printf '%s read-count mismatch: expected %s, observed %s\n' "$label" "$expected" "$((lines / 4))" >&2
        exit 1
    }
}

verify_file "$ART" 14730772 \
    279c6dfbde61500df632cd7970b3bd6ea6b02b69d35d15970019ab09eb55d6df \
    'ART_Illumina Q 2.5.8 binary'
ART_VERSION_OUTPUT=$("$ART" -h 2>&1 || true)
grep -Fq '2.5.8' <<<"$ART_VERSION_OUTPUT" || {
    printf 'ART version check failed; expected output containing 2.5.8\n' >&2
    exit 1
}
printf 'ART_VERSION=2.5.8\nART_PROFILE=HS25\nART_SEED=42\n'

HUMAN_DIR="$DATA_ROOT/seq/human"
ZEA_DIR="$DATA_ROOT/seq/Zea_mays"
HUMAN_REFERENCE="$HUMAN_DIR/GCF_000001405.40_GRCh38.p14_genomic.fna"
ZEA_REFERENCE="$ZEA_DIR/Zm-B73-REFERENCE-NAM-5.0.fa"
verify_file "$HUMAN_REFERENCE" 3339739109 \
    df6e4918316e05a9cc1fd29c352841d3678b607d7a436819cd43371b52c814c0 \
    'Human GRCh38.p14 reference'
verify_file "$ZEA_REFERENCE" 2209359010 \
    52f0663221e46f562eb0923c6dfa1bb43537abb7f13e0f637b5def2571de2c11 \
    'Zea mays B73 RefGen_v5 reference'

run_art() {
    local directory=$1 reference=$2 length=$3 coverage=$4 prefix=$5
    if ((VERIFY_ONLY == 0)); then
        [[ ! -e "$directory/$prefix.fq" && ! -e "$directory/$prefix.aln" ]] || {
            printf 'refusing existing ART output for prefix: %s/%s\n' "$directory" "$prefix" >&2
            exit 1
        }
        (
            cd "$directory"
            "$ART" -ss HS25 -i "$reference" -l "$length" -f "$coverage" \
                -rs 42 -o "$prefix"
        )
    fi
}

run_art "$HUMAN_DIR" "$(basename "$HUMAN_REFERENCE")" 100 0.0167 sim_se_100bp_500K
run_art "$HUMAN_DIR" "$(basename "$HUMAN_REFERENCE")" 150 0.025 sim_se_150bp_500K
run_art "$ZEA_DIR" "$(basename "$ZEA_REFERENCE")" 100 0.0235 sim_zeamays_se_100bp_500K
run_art "$ZEA_DIR" "$(basename "$ZEA_REFERENCE")" 150 0.0353 sim_zeamays_se_150bp_500K

verify_file "$HUMAN_DIR/sim_se_100bp_500K.fq" 116966621 \
    7464f8a449d5f6c3fde97346e74445ad01fb6e6aff0fef82e274853d0f2ae548 'Human 100 bp FASTQ'
verify_file "$HUMAN_DIR/sim_se_100bp_500K.aln" 128617844 \
    0c53a3bec23d8bda9f09d66a1969e24ada536e7d01942ad0aaaf8ec962291ea0 'Human 100 bp ART ALN'
verify_fastq_count "$HUMAN_DIR/sim_se_100bp_500K.fq" 523688 'Human 100 bp'
verify_file "$HUMAN_DIR/sim_se_150bp_500K.fq" 168871174 \
    d21279c25f734f8ddcb7cad2f453ab0db8c018d77582e97d922255c8c56b089c 'Human 150 bp FASTQ'
verify_file "$HUMAN_DIR/sim_se_150bp_500K.aln" 180490902 \
    d202ca09f443853855d9bf767143790dc3eaf2fb9ab895be845e0c44a487a359 'Human 150 bp ART ALN'
verify_fastq_count "$HUMAN_DIR/sim_se_150bp_500K.fq" 522254 'Human 150 bp'
verify_file "$ZEA_DIR/sim_zeamays_se_100bp_500K.fq" 110426369 \
    cb7600c3610f09bb529be32e0bdf20b57eb1111efb866e40790da50ed92ea10c 'Zea 100 bp FASTQ'
verify_file "$ZEA_DIR/sim_zeamays_se_100bp_500K.aln" 117884478 \
    0cebb41ff8d4eb325bd5bde9a4f22b9413e86d0766c55878007d35105ac3f9d2 'Zea 100 bp ART ALN'
verify_fastq_count "$ZEA_DIR/sim_zeamays_se_100bp_500K.fq" 511569 'Zea 100 bp'
verify_file "$ZEA_DIR/sim_zeamays_se_150bp_500K.fq" 161815255 \
    a2a6ae1b7a2b574632bcc7f8fabb65807fce3705beae5e241845009c4d72f3f4 'Zea 150 bp FASTQ'
verify_file "$ZEA_DIR/sim_zeamays_se_150bp_500K.aln" 169284912 \
    9da15aee88ead6e46d4fb65bf49f4d9bf4a4abc81a62da7c781cce03745b1ac1 'Zea 150 bp ART ALN'
verify_fastq_count "$ZEA_DIR/sim_zeamays_se_150bp_500K.fq" 512303 'Zea 150 bp'
printf 'S2_ART_INPUTS=PASS\n'
