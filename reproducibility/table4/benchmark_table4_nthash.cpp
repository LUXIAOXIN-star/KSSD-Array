#define _POSIX_C_SOURCE 200809L

#include <kssd_array.h>

#ifndef K
#define K 21
#endif
#ifndef W
#define W K
#endif

#define KSSD_ARRAY_FIXED_K K
#include <kssd_array_fast.h>

#include "nthash_wrapper.h"

#include <zlib.h>

#include <algorithm>
#include <chrono>
#include <cctype>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <string>
#include <vector>

namespace {

volatile uint64_t benchmark_sink = 0;

struct SequenceInput {
    std::string cleaned;
    size_t raw_bases = 0;
    size_t ambiguous_bases = 0;
};

bool read_first_fasta_record(const char *path, SequenceInput *input) {
    gzFile stream = gzopen(path, "rb");
    bool in_record = false;
    bool at_line_start = true;
    bool in_header = false;
    int character;

    if (stream == nullptr) {
        std::fprintf(stderr, "cannot open FASTA: %s\n", path);
        return false;
    }
    while ((character = gzgetc(stream)) != -1) {
        if (at_line_start && character == '>') {
            if (in_record) {
                break;
            }
            in_record = true;
            in_header = true;
            at_line_start = false;
            continue;
        }
        if (character == '\n' || character == '\r') {
            at_line_start = true;
            in_header = false;
            continue;
        }
        at_line_start = false;
        if (!in_record || in_header || std::isspace(character)) {
            continue;
        }
        ++input->raw_bases;
        const int upper = std::toupper(static_cast<unsigned char>(character));
        if (upper == 'A' || upper == 'C' || upper == 'G' || upper == 'T') {
            input->cleaned.push_back(static_cast<char>(upper));
        } else {
            ++input->ambiguous_bases;
        }
    }
    const int close_status = gzclose(stream);
    if (close_status != Z_OK) {
        std::fprintf(stderr, "error while closing FASTA: %s\n", path);
        return false;
    }
    if (!in_record) {
        std::fprintf(stderr, "FASTA has no record: %s\n", path);
        return false;
    }
    return true;
}

uint64_t base_code(char base) {
    switch (base) {
        case 'C': return UINT64_C(1);
        case 'G': return UINT64_C(2);
        case 'T': return UINT64_C(3);
        default: return UINT64_C(0);
    }
}

std::vector<uint64_t> encode_kmers(const std::string &sequence) {
    const uint64_t mask = K == 32 ? std::numeric_limits<uint64_t>::max()
                                  : (UINT64_C(1) << (2U * K)) - UINT64_C(1);
    std::vector<uint64_t> kmers(sequence.size() - K + 1U);
    uint64_t current = 0;
    for (size_t i = 0; i < sequence.size(); ++i) {
        current = ((current << 2U) | base_code(sequence[i])) & mask;
        if (i + 1U >= K) {
            kmers[i + 1U - K] = current;
        }
    }
    return kmers;
}

bool validate_fast_parity(const std::vector<uint64_t> &kmers,
                          const kssd_array_t *context,
                          size_t *samples) {
    *samples = std::min<size_t>(kmers.size(), 1024U);
    for (size_t i = 0; i < *samples; ++i) {
        const uint64_t normal = kssd_array_map_unchecked(context, kmers[i]);
        const uint64_t fast = kssd_array_fast_with_tables(kmers[i], context);
        if (normal != fast) {
            std::fprintf(stderr, "fast/context parity mismatch at k-mer %zu\n", i);
            return false;
        }
    }
    return *samples > 0U;
}

struct Result {
    double seconds;
    uint64_t checksum;
};

Result benchmark_kssd(const std::vector<uint64_t> &kmers,
                      const kssd_array_t *context,
                      size_t windows) {
    uint64_t current_min = std::numeric_limits<uint64_t>::max();
    size_t current_position = 0;
    const auto start = std::chrono::steady_clock::now();

    for (size_t i = 0; i < W; ++i) {
        const uint64_t hash = kssd_array_fast_with_tables(kmers[i], context);
        if (hash < current_min) {
            current_min = hash;
            current_position = i;
        }
    }
    uint64_t checksum = current_min ^ static_cast<uint64_t>(current_position);
    for (size_t window_start = 1; window_start < windows; ++window_start) {
        const size_t previous_position = window_start - 1U;
        const size_t new_position = window_start + W - 1U;
        if (previous_position == current_position) {
            current_min = std::numeric_limits<uint64_t>::max();
            for (size_t offset = 0; offset < W; ++offset) {
                const size_t position = window_start + offset;
                const uint64_t hash =
                    kssd_array_fast_with_tables(kmers[position], context);
                if (hash < current_min) {
                    current_min = hash;
                    current_position = position;
                }
            }
        } else {
            const uint64_t hash =
                kssd_array_fast_with_tables(kmers[new_position], context);
            if (hash < current_min) {
                current_min = hash;
                current_position = new_position;
            }
        }
        checksum ^= current_min + static_cast<uint64_t>(current_position);
    }
    const auto end = std::chrono::steady_clock::now();
    benchmark_sink ^= checksum;
    return {std::chrono::duration<double>(end - start).count(), checksum};
}

bool benchmark_nthash(const std::string &sequence,
                      size_t kmers,
                      size_t windows,
                      Result *result) {
    table4_nthash_handle_t *handle =
        table4_nthash_create(sequence.data(), sequence.size(), K);
    std::vector<uint64_t> ring(W);
    uint64_t current_min = std::numeric_limits<uint64_t>::max();
    size_t current_position = 0;
    uint64_t checksum = 0;

    if (handle == nullptr) {
        std::fprintf(stderr, "ntHash initialization failed\n");
        return false;
    }
    const auto start = std::chrono::steady_clock::now();
    for (size_t i = 0; i < kmers; ++i) {
        if (!table4_nthash_roll(handle)) {
            std::fprintf(stderr, "ntHash stopped after %zu of %zu k-mers\n", i,
                         kmers);
            table4_nthash_destroy(handle);
            return false;
        }
        const uint64_t hash = table4_nthash_current(handle);
        ring[i % W] = hash;
        if (i < W) {
            if (hash < current_min) {
                current_min = hash;
                current_position = i;
            }
            if (i + 1U == W) {
                checksum ^= current_min + static_cast<uint64_t>(current_position);
            }
            continue;
        }
        const size_t window_start = i - W + 1U;
        const size_t previous_position = window_start - 1U;
        if (previous_position == current_position) {
            current_min = std::numeric_limits<uint64_t>::max();
            for (size_t offset = 0; offset < W; ++offset) {
                const size_t position = window_start + offset;
                const uint64_t old_hash = ring[position % W];
                if (old_hash < current_min) {
                    current_min = old_hash;
                    current_position = position;
                }
            }
        } else if (hash < current_min) {
            current_min = hash;
            current_position = i;
        }
        checksum ^= current_min + static_cast<uint64_t>(current_position);
    }
    const auto end = std::chrono::steady_clock::now();
    table4_nthash_destroy(handle);
    benchmark_sink ^= checksum;
    result->seconds = std::chrono::duration<double>(end - start).count();
    result->checksum = checksum;
    return windows > 0U;
}

void print_result(const char *method, const Result &result, size_t kmers,
                  size_t windows) {
    const double throughput = static_cast<double>(windows) / result.seconds;
    std::printf("RESULT\t%s\t%.12f\t%.6f\t%zu\t%zu\t%zu\t%016" PRIx64 "\n",
                method, result.seconds, throughput, kmers, windows, windows,
                result.checksum);
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 4) {
        std::fprintf(stderr, "usage: %s FASTA REPEAT SEED\n", argv[0]);
        return EXIT_FAILURE;
    }
    const unsigned long repeat = std::strtoul(argv[2], nullptr, 10);
    const uint64_t seed = std::strtoull(argv[3], nullptr, 10);
    SequenceInput input;
    if (!read_first_fasta_record(argv[1], &input)) {
        return EXIT_FAILURE;
    }
    if (input.cleaned.size() < static_cast<size_t>(K + W - 1U)) {
        std::fprintf(stderr, "first FASTA record is too short after cleaning\n");
        return EXIT_FAILURE;
    }
    std::vector<uint64_t> kmers = encode_kmers(input.cleaned);
    const size_t windows = kmers.size() - W + 1U;
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    const kssd_array_status_t init_status = kssd_array_init_with_rng(
        &context, K, seed, KSSD_ARRAY_RNG_GLIBC_COMPAT);
    if (init_status != KSSD_ARRAY_OK) {
        std::fprintf(stderr, "KSSD-Array initialization failed: %s\n",
                     kssd_array_status_string(init_status));
        return EXIT_FAILURE;
    }
    size_t parity_samples = 0;
    if (!validate_fast_parity(kmers, &context, &parity_samples)) {
        kssd_array_destroy(&context);
        return EXIT_FAILURE;
    }
    const Result kssd_result = benchmark_kssd(kmers, &context, windows);
    Result nthash_result{};
    if (!benchmark_nthash(input.cleaned, kmers.size(), windows, &nthash_result)) {
        kssd_array_destroy(&context);
        return EXIT_FAILURE;
    }
    std::printf("META\t%zu\t%zu\t%zu\t%zu\t%zu\t%d\t%d\t%lu\t%" PRIu64 "\n",
                input.raw_bases, input.cleaned.size(), input.ambiguous_bases,
                kmers.size(), windows, K, W, repeat, seed);
    std::printf("PARITY\tPASS\t%zu\n", parity_samples);
    print_result("KSSD-Array", kssd_result, kmers.size(), windows);
    print_result("ntHash", nthash_result, kmers.size(), windows);
    kssd_array_destroy(&context);
    return EXIT_SUCCESS;
}
