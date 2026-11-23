#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ $# -ne 1 ]; then echo 'Usage: bash scripts/reproduce.sh /path/to/the/two/original/genome/files' >&2; exit 2; fi
bash scripts/build.sh
sha256sum -c logs/config_checksums_before.sha256
python3 scripts/prepare_inputs.py "$1"
# Serialized inputs are read during scoring. Check that production initialization recreates them.
for k in 2 3 9 21 32; do
 build/freeze "$k" "cache/validation_k${k}.bin"
 cmp "cache/validation_k${k}.bin" "configs/kssd_k${k}_seed42.bin"
done
python3 scripts/validate_fixed.py >logs/reproduced_fixture_validation_E20.json
# Run separately: simultaneous preparation of large references is unnecessary.
build/prepare cache/yeast.fna 21 cache/yeast_k21 >logs/reproduced_prepare_yeast.txt 2>&1
build/prepare cache/arabidopsis.fna 21 cache/arabidopsis_k21 >logs/reproduced_prepare_arabidopsis.txt 2>&1
python3 scripts/run_fixed.py primary
python3 scripts/run_fixed.py sensitivity10
python3 scripts/run_fixed.py sensitivity50
python3 scripts/summarize_fixed.py
sha256sum -c logs/config_checksums_before.sha256
