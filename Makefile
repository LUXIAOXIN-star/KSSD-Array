CC ?= cc
.DEFAULT_GOAL := all
AR ?= ar
RANLIB ?= ranlib
PREFIX ?= /usr/local
DESTDIR ?=
PACKAGE_VERSION := 1.1.0

CPPFLAGS := -Iinclude
CFLAGS ?= -O2
WARNFLAGS := -std=c11 -Wall -Wextra -Wpedantic
THREAD_FLAGS := -pthread
LIB_SOURCES := src/kssd_array.c src/permutation.c
LIB_OBJECTS := build/obj/kssd_array.o build/obj/permutation.o
STATIC_LIB := build/libkssd_array.a
SHARED_LIB := build/libkssd_array.so
FAST_K_VALUES := 4 8 9 16 19 21 24 31 32
FAST_TESTS := $(addprefix build/tests/test_fast_parity_,$(FAST_K_VALUES))
TESTS := build/tests/test_kssd_array build/tests/test_inline_parity $(FAST_TESTS)
EXAMPLES := build/examples/minimal_api build/examples/build_minimizers
TABLE2_DIR := reproducibility/table2
TABLE2_BINARY := build/reproducibility/table2/test_exhaustive_9mer
FIGURE2_DIR := reproducibility/figure2
FIGURE2_BINARY := build/reproducibility/figure2/benchmark_k21_w20
FIGURE3_DIR := reproducibility/figure3
FIGURE3_BINARY := build/reproducibility/figure3/benchmark_k21_w20
TABLE4_DIR := reproducibility/table4
TABLE4_BINARY := build/reproducibility/table4/benchmark_k21_w21
FIGURE4_DIR := reproducibility/figure4
FIGURE4_BINARY := build/reproducibility/figure4/benchmark_bucket_balance
NTHASH_PREFIX ?= $(if $(NTHASH_ROOT),$(NTHASH_ROOT),third_party/ntHash/install)
FIGURE4_JOBS ?= 1
FIGURE4_PREFLIGHT_OUTPUT ?= $(if $(TMPDIR),$(TMPDIR),/tmp)/kssd-array-figure4-preflight
MINIMAP2_JOBS ?= 2
MINIMAP2_INDEXING_CONFIG ?= reproducibility/minimap2/indexing/config.json
MINIMAP2_ALIGNMENT_CONFIG ?= reproducibility/minimap2/alignment_consistency/config.json

SAN_FLAGS := -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer
SAN_OBJECTS := build/sanitize/obj/kssd_array.o build/sanitize/obj/permutation.o
SAN_LIB := build/sanitize/libkssd_array.a
SAN_FAST_TESTS := $(addprefix build/sanitize/tests/test_fast_parity_,$(FAST_K_VALUES))
SAN_TABLE2_BINARY := build/sanitize/reproducibility/table2/test_exhaustive_9mer
SAN_TESTS := build/sanitize/tests/test_kssd_array \
	build/sanitize/tests/test_inline_parity $(SAN_FAST_TESTS) \
	$(SAN_TABLE2_BINARY)

.PHONY: all shared test sanitize examples table2-validation \
	table2-validation-smoke figure2-build figure2-smoke figure3-build \
	figure3-smoke table4-build table4-smoke figure4-build figure4-preflight \
	figure4-formal minimap2-verify-build minimap2-smoke \
	minimap2-indexing-preflight minimap2-indexing-formal \
	fixture-generator-test synthetic-generator-test s2-corrected-tests minimap2-alignment-preflight minimap2-alignment-formal install clean \
	help all-smoke reproducibility-smoke check check-public-tree check-secrets check-large-files \
	check-docs check-dependencies check-public-history

help:
	@sed -n '/^## Public targets:/,/^## End public targets/p' Makefile | \
		sed -n 's/^## //p'

## Public targets:
## make                     Build the static library.
## make test                Run deterministic core tests.
## make table2-validation   Run the exhaustive 9-mer validation.
## make reproducibility-smoke  Run lightweight manuscript workflows.
## make check               Run core tests and repository checks.
## make install PREFIX=...  Install headers, library, and pkg-config metadata.
## See reproducibility/reproduce_manuscript.sh help for workflow-specific inputs.
## End public targets

all: $(STATIC_LIB)

shared: $(SHARED_LIB)

test: $(TESTS)
	@set -e; for test_binary in $(TESTS); do ./$$test_binary; done

sanitize: $(SAN_TESTS)
	@set -e; for test_binary in $(SAN_TESTS); do \
		ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=print_stacktrace=1 ./$$test_binary; \
	done

examples: $(EXAMPLES)

table2-validation: $(TABLE2_BINARY)
	bash $(TABLE2_DIR)/run_exhaustive_9mer.sh

table2-validation-smoke: $(TABLE2_BINARY)
	bash $(TABLE2_DIR)/run_exhaustive_9mer.sh --smoke

figure2-build: $(FIGURE2_BINARY)

figure2-smoke: $(FIGURE2_BINARY)
	python3 $(FIGURE2_DIR)/run_figure2_single_thread.py --smoke

figure3-build: $(FIGURE3_BINARY)

figure3-smoke: $(FIGURE3_BINARY)
	python3 $(FIGURE3_DIR)/run_figure3_multithread.py --smoke

table4-build: $(TABLE4_BINARY)

table4-smoke: $(TABLE4_BINARY)
	python3 $(TABLE4_DIR)/run_table4_nthash.py --smoke

figure4-build: $(FIGURE4_BINARY)

figure4-preflight: $(FIGURE4_BINARY)
	python3 $(FIGURE4_DIR)/run_figure4_bucket_balance.py --preflight \
		--jobs $(FIGURE4_JOBS) --output-dir "$(FIGURE4_PREFLIGHT_OUTPUT)"

figure4-formal: $(FIGURE4_BINARY)
	@test -n "$(OUTPUT_DIR)" || \
		{ echo "OUTPUT_DIR is required for figure4-formal" >&2; exit 1; }
	python3 $(FIGURE4_DIR)/run_figure4_bucket_balance.py \
		--k-values 6 7 8 9 10 11 12 13 14 \
		--sequence-lengths 4000000 8000000 --bins 101 199 499 \
		--repeats 100 --jobs $(FIGURE4_JOBS) --output-dir "$(OUTPUT_DIR)"

minimap2-verify-build: $(STATIC_LIB)
	@test -n "$(MINIMAP2_SOURCE_DIR)" || \
		{ echo "MINIMAP2_SOURCE_DIR is required" >&2; exit 1; }
	@test -n "$(MINIMAP2_VERIFY_DIR)" || \
		{ echo "MINIMAP2_VERIFY_DIR is required" >&2; exit 1; }
	JOBS=$(MINIMAP2_JOBS) reproducibility/minimap2/verify_build.sh \
		--build-only "$(MINIMAP2_SOURCE_DIR)" "$(CURDIR)" \
		"$(MINIMAP2_VERIFY_DIR)"

minimap2-smoke: $(STATIC_LIB)
	@test -n "$(MINIMAP2_SOURCE_DIR)" || \
		{ echo "MINIMAP2_SOURCE_DIR is required" >&2; exit 1; }
	@test -n "$(MINIMAP2_SMOKE_DIR)" || \
		{ echo "MINIMAP2_SMOKE_DIR is required" >&2; exit 1; }
	JOBS=$(MINIMAP2_JOBS) reproducibility/minimap2/verify_build.sh \
		--smoke "$(MINIMAP2_SOURCE_DIR)" "$(CURDIR)" \
		"$(MINIMAP2_SMOKE_DIR)"

minimap2-indexing-preflight: $(STATIC_LIB)
	@test -n "$(MINIMAP2_SOURCE_DIR)" || \
		{ echo "MINIMAP2_SOURCE_DIR is required" >&2; exit 1; }
	@test -n "$(MINIMAP2_INDEXING_PREFLIGHT_DIR)" || \
		{ echo "MINIMAP2_INDEXING_PREFLIGHT_DIR is required" >&2; exit 1; }
	python3 reproducibility/minimap2/indexing/run_supplementary_indexing.py \
		--preflight --config "$(MINIMAP2_INDEXING_CONFIG)" \
		--upstream-source "$(MINIMAP2_SOURCE_DIR)" \
		--output-dir "$(MINIMAP2_INDEXING_PREFLIGHT_DIR)"

minimap2-indexing-formal: $(STATIC_LIB)
	@test -n "$(MINIMAP2_SOURCE_DIR)" || \
		{ echo "MINIMAP2_SOURCE_DIR is required" >&2; exit 1; }
	@test -n "$(DATA_CONFIG)" || \
		{ echo "DATA_CONFIG is required" >&2; exit 1; }
	@test -n "$(OUTPUT_DIR)" || \
		{ echo "OUTPUT_DIR is required" >&2; exit 1; }
	python3 reproducibility/minimap2/indexing/run_supplementary_indexing.py \
		--config "$(DATA_CONFIG)" --upstream-source "$(MINIMAP2_SOURCE_DIR)" \
		--output-dir "$(OUTPUT_DIR)" $(MINIMAP2_DATASET_ARGS)

s2-corrected-tests:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
		-s reproducibility/minimap2/alignment_consistency_truth_origin/tests -v

fixture-generator-test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
		tests.fixture_generators.test_generate_test_fixtures -v

synthetic-generator-test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
		-s reproducibility/data_generation/synthetic_300M -p 'test_*.py' -v

minimap2-alignment-preflight: $(STATIC_LIB)
	@test -n "$(PHASE5B_OUTPUT)" || \
		{ echo "PHASE5B_OUTPUT is required" >&2; exit 1; }
	@test -n "$(MINIMAP2_ALIGNMENT_PREFLIGHT_DIR)" || \
		{ echo "MINIMAP2_ALIGNMENT_PREFLIGHT_DIR is required" >&2; exit 1; }
	python3 reproducibility/minimap2/alignment_consistency/run_alignment_consistency.py \
		--preflight --config "$(MINIMAP2_ALIGNMENT_CONFIG)" \
		--phase5b-output "$(PHASE5B_OUTPUT)" \
		--output-dir "$(MINIMAP2_ALIGNMENT_PREFLIGHT_DIR)"

minimap2-alignment-formal: $(STATIC_LIB)
	@test -n "$(PHASE5B_OUTPUT)" || \
		{ echo "PHASE5B_OUTPUT is required" >&2; exit 1; }
	@test -n "$(DATA_CONFIG)" || \
		{ echo "DATA_CONFIG is required" >&2; exit 1; }
	@test -n "$(OUTPUT_DIR)" || \
		{ echo "OUTPUT_DIR is required" >&2; exit 1; }
	python3 reproducibility/minimap2/alignment_consistency/run_alignment_consistency.py \
		--config "$(DATA_CONFIG)" --phase5b-output "$(PHASE5B_OUTPUT)" \
		--output-dir "$(OUTPUT_DIR)" $(MINIMAP2_ALIGNMENT_DATASET_ARGS)

reproducibility-smoke all-smoke:
	reproducibility/reproduce_manuscript.sh all-smoke

check-public-tree:
	python3 tools/check_public_tree.py

check-public-history:
	python3 tools/check_public_history.py

check-secrets:
	python3 tools/check_secrets.py

check-large-files:
	python3 tools/check_large_files.py

check-docs:
	python3 tools/check_documentation_links.py

check-dependencies:
	python3 tools/check_dependencies.py

check: test table2-validation fixture-generator-test synthetic-generator-test check-public-tree check-public-history \
	check-secrets check-large-files check-docs

install: $(STATIC_LIB)
	install -d "$(DESTDIR)$(PREFIX)/include" "$(DESTDIR)$(PREFIX)/lib" \
		"$(DESTDIR)$(PREFIX)/lib/pkgconfig"
	install -m 0644 include/kssd_array.h include/kssd_array_fast.h \
		include/kssd_array_inline.h \
		"$(DESTDIR)$(PREFIX)/include/"
	install -m 0644 $(STATIC_LIB) "$(DESTDIR)$(PREFIX)/lib/"
	sed -e 's|@PREFIX@|$(PREFIX)|g' \
		-e 's|@VERSION@|$(PACKAGE_VERSION)|g' pkgconfig/kssd-array-make.pc.in \
		> build/kssd-array.pc
	install -m 0644 build/kssd-array.pc \
		"$(DESTDIR)$(PREFIX)/lib/pkgconfig/kssd-array.pc"

clean:
	rm -rf build

build/obj/%.o: src/%.c include/kssd_array.h include/kssd_array_inline.h src/permutation.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNFLAGS) -fPIC -MMD -MP -c $< -o $@

$(STATIC_LIB): $(LIB_OBJECTS)
	$(AR) rcs $@ $^
	$(RANLIB) $@

$(SHARED_LIB): $(LIB_OBJECTS)
	$(CC) -shared -o $@ $^

build/tests/test_kssd_array: tests/test_kssd_array.c $(STATIC_LIB)
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNFLAGS) $(THREAD_FLAGS) $< \
		-Lbuild -Wl,-rpath,'$$ORIGIN/..' -lkssd_array -o $@

build/tests/test_inline_parity: tests/test_inline_parity.c $(STATIC_LIB) include/kssd_array_inline.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNFLAGS) $< \
		-Lbuild -Wl,-rpath,'$$ORIGIN/..' -lkssd_array -o $@

build/tests/test_fast_parity_%: tests/test_fast_parity.c $(STATIC_LIB) include/kssd_array_fast.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNFLAGS) -DKSSD_ARRAY_FIXED_K=$* $< \
		-Lbuild -Wl,-rpath,'$$ORIGIN/..' -lkssd_array -o $@

build/examples/%: examples/%.c $(STATIC_LIB) include/kssd_array_fast.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNFLAGS) $< \
		-Lbuild -Wl,-rpath,'$$ORIGIN/..' -lkssd_array -o $@

$(TABLE2_BINARY): $(TABLE2_DIR)/test_exhaustive_9mer.c $(STATIC_LIB)
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNFLAGS) -Wconversion -Werror $< \
		-Lbuild -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic -o $@

$(FIGURE2_BINARY): $(FIGURE2_DIR)/benchmark_single_thread_realistic_kw.c \
		$(STATIC_LIB) include/kssd_array_fast.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) -O3 -march=native $(WARNFLAGS) -DK=21 -DW=20 $< \
		-Lbuild -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic \
		-lxxhash -lm -o $@

$(FIGURE3_BINARY): $(FIGURE3_DIR)/benchmark_multithread_k21.c \
		$(STATIC_LIB) include/kssd_array_fast.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) -O3 -march=native $(WARNFLAGS) -fopenmp \
		-DK=21 -DW=20 $< \
		-Lbuild -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic \
		-lxxhash -lz -lm -fopenmp -o $@

$(TABLE4_BINARY): $(TABLE4_DIR)/benchmark_table4_nthash.cpp \
		$(TABLE4_DIR)/nthash_wrapper.cpp $(TABLE4_DIR)/nthash_wrapper.h \
		$(STATIC_LIB) include/kssd_array_fast.h
	@test -f "$(NTHASH_PREFIX)/include/nthash/nthash.hpp" || \
		{ echo "ntHash header missing; set NTHASH_ROOT or run reproducibility/table4/prepare_nthash.sh" >&2; exit 1; }
	@test -f "$(NTHASH_PREFIX)/lib/libnthash.a" || \
		{ echo "ntHash library missing; set NTHASH_ROOT or run reproducibility/table4/prepare_nthash.sh" >&2; exit 1; }
	@mkdir -p $(@D)
	$(CXX) -O3 -march=native -std=c++17 -Wall -Wextra -Wpedantic \
		-DK=21 -DW=21 -Iinclude -I"$(NTHASH_PREFIX)/include" \
		$(TABLE4_DIR)/benchmark_table4_nthash.cpp \
		$(TABLE4_DIR)/nthash_wrapper.cpp \
		-Lbuild -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic \
		-L"$(NTHASH_PREFIX)/lib" -lnthash -lz -o $@

$(FIGURE4_BINARY): $(FIGURE4_DIR)/benchmark_bucket_balance.c $(STATIC_LIB)
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) -O3 -march=native $(WARNFLAGS) $< \
		-Lbuild -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic \
		-lxxhash -lm -o $@

build/sanitize/obj/%.o: src/%.c include/kssd_array.h include/kssd_array_inline.h src/permutation.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(WARNFLAGS) $(SAN_FLAGS) -MMD -MP -c $< -o $@

$(SAN_LIB): $(SAN_OBJECTS)
	$(AR) rcs $@ $^
	$(RANLIB) $@

build/sanitize/tests/test_kssd_array: tests/test_kssd_array.c $(SAN_LIB)
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(WARNFLAGS) $(SAN_FLAGS) $(THREAD_FLAGS) $< \
		-Lbuild/sanitize -lkssd_array -o $@

build/sanitize/tests/test_inline_parity: tests/test_inline_parity.c $(SAN_LIB) include/kssd_array_inline.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(WARNFLAGS) $(SAN_FLAGS) $< \
		-Lbuild/sanitize -lkssd_array -o $@

build/sanitize/tests/test_fast_parity_%: tests/test_fast_parity.c $(SAN_LIB) include/kssd_array_fast.h
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(WARNFLAGS) $(SAN_FLAGS) -DKSSD_ARRAY_FIXED_K=$* $< \
		-Lbuild/sanitize -lkssd_array -o $@

$(SAN_TABLE2_BINARY): $(TABLE2_DIR)/test_exhaustive_9mer.c $(SAN_LIB)
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(WARNFLAGS) $(SAN_FLAGS) -Wconversion -Werror $< \
		-Lbuild/sanitize -Wl,-Bstatic -lkssd_array -Wl,-Bdynamic -o $@

-include $(LIB_OBJECTS:.o=.d) $(SAN_OBJECTS:.o=.d)
