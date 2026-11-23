#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build logs cache results
python3 scripts/verify_sources.py
cc=${CC:-gcc}; cxx=${CXX:-g++}
"$cc" -O3 -std=c11 -Wall -Wextra -Iproduction/include -Iproduction/src -c production/src/kssd_array.c -o build/kssd_array.o
"$cc" -O3 -std=c11 -Wall -Wextra -Iproduction/include -Iproduction/src -c production/src/permutation.c -o build/permutation.o
ar rcs build/libkssd_array.a build/kssd_array.o build/permutation.o
for src in prepare analyze freeze score_dump; do
 "$cxx" -O3 -std=c++17 -Wall -Wextra -Iproduction/include "scripts/${src}.cpp" build/libkssd_array.a -o "build/$src"
done
