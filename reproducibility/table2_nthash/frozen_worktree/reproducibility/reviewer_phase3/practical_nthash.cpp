#define _POSIX_C_SOURCE 200809L

#include <kssd_array.h>
#ifndef K
#define K 21
#endif
#define KSSD_ARRAY_FIXED_K K
#include <kssd_array_fast.h>
#include <nthash/nthash.hpp>

#include <algorithm>
#include <chrono>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <string>
#include <vector>

static_assert(K >= 1 && K <= 32, "K must be in 1..32");

namespace {

volatile uint64_t phase3_sink = 0;

struct Input {
    std::string sequence;
    size_t raw_bases = 0;
    size_t ambiguous_bases = 0;
};

struct Timing {
    double seconds = 0.0;
    uint64_t tsc_cycles = 0;
    uint64_t checksum = 0;
    size_t count = 0;
};

struct WindowResult {
    Timing timing;
    size_t selected = 0;
    uint64_t position_checksum = 0;
    uint64_t score_checksum = 0;
};

uint64_t splitmix64_value(uint64_t value) {
    value = (value ^ (value >> 30U)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27U)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31U);
}

uint64_t read_tsc_begin() {
#if defined(__x86_64__) || defined(__i386__)
    unsigned low, high;
    __asm__ volatile("lfence\n\trdtsc" : "=a"(low), "=d"(high) :: "memory");
    return (static_cast<uint64_t>(high) << 32U) | low;
#else
    return 0;
#endif
}

uint64_t read_tsc_end() {
#if defined(__x86_64__) || defined(__i386__)
    unsigned low, high, auxiliary;
    __asm__ volatile("rdtscp\n\tlfence" : "=a"(low), "=d"(high), "=c"(auxiliary) :: "memory");
    (void)auxiliary;
    return (static_cast<uint64_t>(high) << 32U) | low;
#else
    return 0;
#endif
}

bool read_first_fasta_record(const char *path, Input *input) {
    FILE *file = std::fopen(path, "rb");
    if (file == nullptr) {
        std::perror("cannot open FASTA");
        return false;
    }
    std::setvbuf(file, nullptr, _IOFBF, 1U << 20U);
    bool found = false, header = false, line_start = true;
    int character;
    while ((character = std::fgetc(file)) != EOF) {
        if (line_start && character == '>') {
            if (found) break;
            found = true;
            header = true;
            line_start = false;
            continue;
        }
        if (character == '\n' || character == '\r') {
            line_start = true;
            header = false;
            continue;
        }
        line_start = false;
        if (!found || header) continue;
        ++input->raw_bases;
        switch (character) {
        case 'A': case 'a': input->sequence.push_back('A'); break;
        case 'C': case 'c': input->sequence.push_back('C'); break;
        case 'G': case 'g': input->sequence.push_back('G'); break;
        case 'T': case 't': input->sequence.push_back('T'); break;
        default: ++input->ambiguous_bases; break;
        }
    }
    const bool ok = found && !std::ferror(file);
    std::fclose(file);
    return ok;
}

inline uint64_t base_code(char base) {
    switch (base) {
    case 'C': return 1;
    case 'G': return 2;
    case 'T': return 3;
    default: return 0;
    }
}

constexpr uint64_t domain_mask() {
    if constexpr (K == 32) {
        return std::numeric_limits<uint64_t>::max();
    } else {
        return (UINT64_C(1) << (2U * K)) - 1U;
    }
}

Timing score_kssd(const std::string &sequence,
                  const kssd_array_t *context,
                  uint64_t *scores,
                  size_t count) {
    uint64_t forward = 0, reverse = 0, checksum = 0;
    size_t consumed = 0;
    const uint64_t tsc_start = read_tsc_begin();
    const auto start = std::chrono::steady_clock::now();
    for (size_t position = 0; position < count; ++position) {
        const size_t required = position == 0 ? static_cast<size_t>(K) : 1U;
        for (size_t step = 0; step < required; ++step) {
            const uint64_t code = base_code(sequence[consumed++]);
            forward = ((forward << 2U) | code) & domain_mask();
            reverse = (reverse >> 2U) |
                      ((UINT64_C(3) - code) << (2U * (K - 1U)));
        }
        const uint64_t canonical = std::min(forward, reverse);
        const uint64_t score = kssd_array_fast_with_tables(canonical, context);
        scores[position] = score;
        checksum ^= splitmix64_value(score ^
            (static_cast<uint64_t>(position) * UINT64_C(0x9e3779b97f4a7c15)));
    }
    const auto end = std::chrono::steady_clock::now();
    const uint64_t tsc_end = read_tsc_end();
    phase3_sink ^= checksum;
    return {std::chrono::duration<double>(end - start).count(),
            tsc_end - tsc_start, checksum, count};
}

Timing score_nthash(const std::string &sequence,
                    uint64_t *scores,
                    size_t count) {
    nthash::NtHash iterator(sequence.data(), sequence.size(), 1U,
        static_cast<nthash::typedefs::K_TYPE>(K));
    uint64_t checksum = 0;
    const uint64_t tsc_start = read_tsc_begin();
    const auto start = std::chrono::steady_clock::now();
    for (size_t position = 0; position < count; ++position) {
        if (!iterator.roll()) {
            std::fprintf(stderr, "ntHash ended at %zu/%zu\n", position, count);
            std::exit(EXIT_FAILURE);
        }
        const uint64_t score = iterator.hashes()[0];
        scores[position] = score;
        checksum ^= splitmix64_value(score ^
            (static_cast<uint64_t>(position) * UINT64_C(0x9e3779b97f4a7c15)));
    }
    const auto end = std::chrono::steady_clock::now();
    const uint64_t tsc_end = read_tsc_end();
    phase3_sink ^= checksum;
    return {std::chrono::duration<double>(end - start).count(),
            tsc_end - tsc_start, checksum, count};
}

WindowResult select_windows(const uint64_t *scores,
                            size_t count,
                            size_t width,
                            size_t *deque) {
    WindowResult result;
    size_t front = 0, back = 0;
    const uint64_t tsc_start = read_tsc_begin();
    const auto start = std::chrono::steady_clock::now();
    for (size_t index = 0; index < count; ++index) {
        while (front < back && deque[front] + width <= index) ++front;
        while (front < back && scores[deque[back - 1U]] > scores[index]) --back;
        deque[back++] = index;
        if (index + 1U >= width) {
            const size_t window_start = index + 1U - width;
            const size_t position = deque[front];
            result.position_checksum ^= splitmix64_value(
                static_cast<uint64_t>(position) ^
                (static_cast<uint64_t>(window_start) * UINT64_C(0xd6e8feb86659fd93)));
            result.score_checksum ^= splitmix64_value(
                scores[position] ^
                (static_cast<uint64_t>(window_start) * UINT64_C(0x9e3779b97f4a7c15)));
            ++result.selected;
        }
    }
    const auto end = std::chrono::steady_clock::now();
    const uint64_t tsc_end = read_tsc_end();
    result.timing = {std::chrono::duration<double>(end - start).count(),
                     tsc_end - tsc_start,
                     result.position_checksum ^ result.score_checksum,
                     result.selected};
    phase3_sink ^= result.timing.checksum;
    return result;
}

struct MethodResult {
    Timing score;
    WindowResult window;
};

MethodResult run_method(bool kssd,
                        const Input &input,
                        const kssd_array_t *context,
                        size_t width,
                        std::vector<uint64_t> *scores,
                        std::vector<size_t> *deque) {
    MethodResult result;
    result.score = kssd
        ? score_kssd(input.sequence, context, scores->data(), scores->size())
        : score_nthash(input.sequence, scores->data(), scores->size());
    result.window = select_windows(scores->data(), scores->size(), width,
                                   deque->data());
    return result;
}

void print_result(const char *dataset, size_t width, unsigned repeat,
                  unsigned order, const char *method,
                  const MethodResult &result) {
    const double total = result.score.seconds + result.window.timing.seconds;
    const double score_rate = result.score.count / result.score.seconds / 1.0e6;
    const double total_rate = result.window.selected / total / 1.0e6;
    std::printf(
        "PRACTICAL\t%s\t%d\t%zu\t%u\t%u\t%s\t%.12f\t%.12f\t%.12f"
        "\t%.9f\t%.9f\t%" PRIu64 "\t%" PRIu64 "\t%zu\t%zu\t%zu"
        "\t%016" PRIx64 "\t%016" PRIx64 "\t%016" PRIx64 "\n",
        dataset, K, width, repeat, order, method,
        result.score.seconds, result.window.timing.seconds, total,
        score_rate, total_rate, result.score.tsc_cycles,
        result.window.timing.tsc_cycles, result.score.count,
        result.window.selected, result.window.selected,
        result.score.checksum, result.window.position_checksum,
        result.window.score_checksum);
    std::fflush(stdout);
}

bool validate_fixture(const kssd_array_t *context) {
    const std::string sequence =
        "ACGTTGCATGTCGCATGATGCATGAGAGCTTAGCGGATCCGATGCTAGCATCGATCGTACG"
        "TATGCCGTAGCTAGGCTAACCGGTTAACCGGTTAGCATGCTAGCTGATCGTAGCTAGCATC"
        "GGATCGATGCACTGATCGTACGATCGTAGCTAGCGTACGATCGGCTAACGTAGCTAGCATG";
    Input input;
    input.sequence = sequence;
    const size_t count = sequence.size() - K + 1U;
    const size_t width = std::min<size_t>(10U, count);
    std::vector<uint64_t> scores(count), scores2(count);
    std::vector<size_t> deque(count);
    const Timing a = score_kssd(sequence, context, scores.data(), count);
    const Timing b = score_kssd(sequence, context, scores2.data(), count);
    const WindowResult wa = select_windows(scores.data(), count, width, deque.data());
    const WindowResult wb = select_windows(scores2.data(), count, width, deque.data());
    nthash::NtHash nt(sequence.data(), sequence.size(), 1U,
        static_cast<nthash::typedefs::K_TYPE>(K));
    bool nt_count = true;
    for (size_t i = 0; i < count; ++i) nt_count = nt.roll() && nt_count;
    const bool pass = a.checksum == b.checksum && scores == scores2 &&
        wa.position_checksum == wb.position_checksum &&
        wa.score_checksum == wb.score_checksum && nt_count &&
        wa.selected == count - width + 1U;
    std::printf("VALIDATION\tpractical_nthash\t%s\t%d\t%zu\t%zu\n",
                pass ? "PASS" : "FAIL", K, count, wa.selected);
    return pass;
}

} // namespace

int main(int argc, char **argv) {
    if (argc == 2 && std::string(argv[1]) == "--validate") {
        kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
        if (kssd_array_init(&context, K, UINT64_C(42)) != KSSD_ARRAY_OK)
            return EXIT_FAILURE;
        const bool passed = validate_fixture(&context);
        kssd_array_destroy(&context);
        return passed ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    if (argc != 5) {
        std::fprintf(stderr, "usage: %s --validate | FASTA DATASET W REPEATS\n", argv[0]);
        return EXIT_FAILURE;
    }
    const size_t width = std::strtoull(argv[3], nullptr, 10);
    const unsigned repeats = static_cast<unsigned>(std::strtoul(argv[4], nullptr, 10));
    Input input;
    if (!read_first_fasta_record(argv[1], &input) ||
        input.sequence.size() < static_cast<size_t>(K) || width == 0 || repeats == 0) {
        std::fprintf(stderr, "invalid input or parameters\n");
        return EXIT_FAILURE;
    }
    const size_t score_count = input.sequence.size() - K + 1U;
    if (width > score_count) return EXIT_FAILURE;
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    if (kssd_array_init(&context, K, UINT64_C(42)) != KSSD_ARRAY_OK) {
        std::fprintf(stderr, "KSSD initialization failed\n");
        return EXIT_FAILURE;
    }
    if (!validate_fixture(&context)) {
        kssd_array_destroy(&context);
        return EXIT_FAILURE;
    }
    std::vector<uint64_t> scores(score_count);
    std::vector<size_t> deque(score_count);
    (void)run_method(true, input, &context, width, &scores, &deque);
    (void)run_method(false, input, &context, width, &scores, &deque);
    std::printf("META\t%s\t%d\t%zu\t%zu\t%zu\t%zu\t%zu\t42\tSplitMix64\n",
                argv[2], K, width, input.raw_bases, input.sequence.size(),
                input.ambiguous_bases, score_count);
    const bool condition_flip = ((static_cast<unsigned>(K) +
                                  static_cast<unsigned>(width)) & 1U) != 0U;
    for (unsigned repeat = 1; repeat <= repeats; ++repeat) {
        const bool kssd_first = ((repeat & 1U) != 0U) ^ condition_flip;
        for (unsigned order = 1; order <= 2; ++order) {
            const bool kssd = order == 1 ? kssd_first : !kssd_first;
            const MethodResult result = run_method(kssd, input, &context,
                                                   width, &scores, &deque);
            print_result(argv[2], width, repeat, order,
                         kssd ? "KSSD-Array" : "ntHash", result);
        }
    }
    kssd_array_destroy(&context);
    return EXIT_SUCCESS;
}
