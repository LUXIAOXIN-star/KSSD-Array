#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: generate_repeat_annotations.sh --data-root DIRECTORY \
       --human-source hg38_repeats.bed --zea-gff Zm-B73-REFERENCE-NAM-5.0.TE.gff3 \
       [--verify-only]

Create the exact Human RefSeq-name and Zea mays BED files used by corrected
Supplementary Table S2. Existing outputs are never overwritten.
EOF
}

DATA_ROOT=""
HUMAN_SOURCE=""
ZEA_GFF=""
VERIFY_ONLY=0
while (($#)); do
    case "$1" in
        --data-root) DATA_ROOT=${2:?missing value for --data-root}; shift 2 ;;
        --human-source) HUMAN_SOURCE=${2:?missing value for --human-source}; shift 2 ;;
        --zea-gff) ZEA_GFF=${2:?missing value for --zea-gff}; shift 2 ;;
        --verify-only) VERIFY_ONLY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n "$DATA_ROOT" && -n "$HUMAN_SOURCE" && -n "$ZEA_GFF" ]] || {
    usage >&2
    exit 2
}
DATA_ROOT=$(readlink -f "$DATA_ROOT")
HUMAN_SOURCE=$(readlink -f "$HUMAN_SOURCE")
ZEA_GFF=$(readlink -f "$ZEA_GFF")
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

verify_file "$HUMAN_SOURCE" 211063376 \
    fe9dd792d266a2ae2868da4993b6706ef257a7f8e41ae5f85731efcfbbf473dc \
    'Human hg38 rmsk-derived source BED'
verify_file "$ZEA_GFF" 342920266 \
    025c61d382dfc0355a09badd98c7197ad7a15eaf4c271cdea6ad3b53eccbbdc6 \
    'Zea mays B73 RefGen_v5 TE GFF3'

HUMAN_OUTPUT="$DATA_ROOT/seq/human/hg38_repeats_refseq.bed"
ZEA_OUTPUT="$DATA_ROOT/seq/Zea_mays/maize_repeats_raw.bed"
HUMAN_TEMP=""
ZEA_TEMP=""
cleanup() {
    [[ -z "$HUMAN_TEMP" ]] || rm -f -- "$HUMAN_TEMP"
    [[ -z "$ZEA_TEMP" ]] || rm -f -- "$ZEA_TEMP"
}
trap cleanup EXIT

if ((VERIFY_ONLY == 0)); then
    [[ -d "$(dirname "$HUMAN_OUTPUT")" && -d "$(dirname "$ZEA_OUTPUT")" ]] || {
        printf 'expected data-root seq/human and seq/Zea_mays directories are missing\n' >&2
        exit 1
    }
    [[ ! -e "$HUMAN_OUTPUT" && ! -e "$ZEA_OUTPUT" ]] || {
        printf 'refusing existing repeat BED output\n' >&2
        exit 1
    }
    HUMAN_TEMP=$(mktemp "${HUMAN_OUTPUT}.tmp.XXXXXX")
    LC_ALL=C awk 'BEGIN {
        OFS="\t"
        map["chr1"]="NC_000001.11"; map["chr2"]="NC_000002.12"
        map["chr3"]="NC_000003.12"; map["chr4"]="NC_000004.12"
        map["chr5"]="NC_000005.10"; map["chr6"]="NC_000006.12"
        map["chr7"]="NC_000007.14"; map["chr8"]="NC_000008.11"
        map["chr9"]="NC_000009.12"; map["chr10"]="NC_000010.11"
        map["chr11"]="NC_000011.10"; map["chr12"]="NC_000012.12"
        map["chr13"]="NC_000013.11"; map["chr14"]="NC_000014.9"
        map["chr15"]="NC_000015.10"; map["chr16"]="NC_000016.10"
        map["chr17"]="NC_000017.11"; map["chr18"]="NC_000018.10"
        map["chr19"]="NC_000019.10"; map["chr20"]="NC_000020.11"
        map["chr21"]="NC_000021.9"; map["chr22"]="NC_000022.11"
        map["chrX"]="NC_000023.11"; map["chrY"]="NC_000024.10"
        map["chrM"]="NC_012920.1"
    }
    $1 in map { $1=map[$1]; print }' "$HUMAN_SOURCE" > "$HUMAN_TEMP"

    ZEA_TEMP=$(mktemp "${ZEA_OUTPUT}.tmp.XXXXXX")
    LC_ALL=C awk 'BEGIN {OFS="\t"} !/^#/ {print $1, $4 - 1, $5, $3}' \
        "$ZEA_GFF" > "$ZEA_TEMP"

    mv "$HUMAN_TEMP" "$HUMAN_OUTPUT"
    HUMAN_TEMP=""
    mv "$ZEA_TEMP" "$ZEA_OUTPUT"
    ZEA_TEMP=""
fi

verify_file "$HUMAN_OUTPUT" 233983952 \
    74a5a4b8887b7ad061ad81feca8546df8a3668651d0c0e7e187e9b08f403d1a2 \
    'Human RefSeq-name repeat BED'
verify_file "$ZEA_OUTPUT" 79599886 \
    e402860999e6de118f3deada95de01bc96e80ffc4f505b5962abfca687fab0e9 \
    'Zea mays repeat BED'
printf 'S2_REPEAT_ANNOTATIONS=PASS\n'
