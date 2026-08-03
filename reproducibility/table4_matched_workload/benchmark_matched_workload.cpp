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

#include <nthash/nthash.hpp>
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

static_assert(K >= 4 && K <= 32, "K must be in 4..32");
static_assert(W >= 1, "W must be positive");

namespace {

volatile uint64_t benchmark_sink = 0;

struct SequenceInput {
    std::string cleaned;
    size_t raw_bases = 0;
    size_t ambiguous_bases = 0;
};

bool read_first_fasta_record(const char *path, SequenceInput *input) {
    constexpr int buffer_size = 1 << 20;
    std::vector<unsigned char> buffer(static_cast<size_t>(buffer_size));
    gzFile stream = gzopen(path, "rb");
    bool in_record = false;
    bool at_line_start = true;
    bool in_header = false;
    bool done = false;

    if (stream == nullptr) {
        std::fprintf(stderr, "cannot open FASTA: %s\n", path);
        return false;
    }
    while (!done) {
        const int count = gzread(stream, buffer.data(), buffer_size);
        if (count < 0) {
            int error_number = Z_OK;
            const char *message = gzerror(stream, &error_number);
            std::fprintf(stderr, "FASTA read error: %s\n",
                         message == nullptr ? "unknown" : message);
            gzclose(stream);
            return false;
        }
        if (count == 0) {
            break;
        }
        for (int index = 0; index < count; ++index) {
            const unsigned char character = buffer[static_cast<size_t>(index)];
            if (at_line_start && character == '>') {
                if (in_record) {
                    done = true;
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
            if (!in_record || in_header || std::isspace(character) != 0) {
                continue;
            }
            ++input->raw_bases;
            const int upper = std::toupper(character);
            if (upper == 'A' || upper == 'C' || upper == 'G' || upper == 'T') {
                input->cleaned.push_back(static_cast<char>(upper));
            } else {
                ++input->ambiguous_bases;
            }
        }
    }
    if (gzclose(stream) != Z_OK) {
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

template <unsigned KmerLength>
constexpr uint64_t kmer_mask() {
    if constexpr (KmerLength == 32U) {
        return std::numeric_limits<uint64_t>::max();
    } else {
        return (UINT64_C(1) << (2U * KmerLength)) - UINT64_C(1);
    }
}

template <unsigned KmerLength>
uint64_t direct_forward(const std::string &sequence, size_t start) {
    uint64_t value = 0;
    for (size_t offset = 0; offset < KmerLength; ++offset) {
        value = (value << 2U) | base_code(sequence[start + offset]);
    }
    return value;
}

template <unsigned KmerLength>
uint64_t direct_reverse_complement(const std::string &sequence, size_t start) {
    uint64_t value = 0;
    for (size_t offset = 0; offset < KmerLength; ++offset) {
        const uint64_t code =
            base_code(sequence[start + KmerLength - 1U - offset]);
        value = (value << 2U) | (UINT64_C(3) - code);
    }
    return value;
}

template <unsigned KmerLength>
std::string reverse_complement(const std::string &sequence) {
    std::string result(sequence.size(), 'A');
    for (size_t index = 0; index < sequence.size(); ++index) {
        const uint64_t code = base_code(sequence[sequence.size() - 1U - index]);
        static constexpr char bases[] = {'A', 'C', 'G', 'T'};
        result[index] = bases[3U - static_cast<unsigned>(code)];
    }
    return result;
}

template <unsigned KmerLength>
class CanonicalTwoBitGenerator {
public:
    CanonicalTwoBitGenerator(const std::string &sequence,
                             const kssd_array_t *context)
        : sequence_(sequence), context_(context) {}

    bool next(uint64_t *score) {
        const size_t required =
            produced_ == 0U ? static_cast<size_t>(KmerLength) : 1U;
        if (consumed_ + required > sequence_.size()) {
            return false;
        }
        for (size_t step = 0; step < required; ++step) {
            const uint64_t code = base_code(sequence_[consumed_]);
            forward_ = ((forward_ << 2U) | code) & kmer_mask<KmerLength>();
            reverse_ = (reverse_ >> 2U) |
                       ((UINT64_C(3) - code) << (2U * (KmerLength - 1U)));
            ++consumed_;
        }
        canonical_ = std::min(forward_, reverse_);
        *score = kssd_array_fast_with_tables(canonical_, context_);
        ++produced_;
        return true;
    }

    uint64_t forward() const { return forward_; }
    uint64_t reverse() const { return reverse_; }
    uint64_t canonical() const { return canonical_; }
    size_t produced() const { return produced_; }

private:
    const std::string &sequence_;
    const kssd_array_t *context_;
    size_t consumed_ = 0;
    size_t produced_ = 0;
    uint64_t forward_ = 0;
    uint64_t reverse_ = 0;
    uint64_t canonical_ = 0;
};

template <unsigned KmerLength>
class NtHashGenerator {
public:
    explicit NtHashGenerator(const std::string &sequence)
        : iterator_(sequence.data(), sequence.size(), 1U,
                    static_cast<nthash::typedefs::K_TYPE>(KmerLength)) {}

    bool next(uint64_t *score) {
        if (!iterator_.roll()) {
            return false;
        }
        *score = iterator_.hashes()[0];
        ++produced_;
        return true;
    }

    size_t produced() const { return produced_; }

private:
    nthash::NtHash iterator_;
    size_t produced_ = 0;
};

struct RunResult {
    double seconds = 0;
    uint64_t checksum = 0;
    size_t scores = 0;
    size_t windows = 0;
};

uint64_t checksum_window(uint64_t checksum,
                         uint64_t minimum,
                         size_t position,
                         size_t window_start) {
    const uint64_t position_term =
        static_cast<uint64_t>(position) * UINT64_C(0x9e3779b97f4a7c15);
    const uint64_t window_term =
        static_cast<uint64_t>(window_start) * UINT64_C(0xbf58476d1ce4e5b9);
    return checksum ^ (minimum + position_term + window_term);
}

template <typename Generator>
bool run_shared_minimizers(Generator *generator,
                           size_t score_count,
                           std::vector<uint64_t> *ring,
                           RunResult *result) {
    if (score_count < W || ring->size() != W) {
        return false;
    }
    uint64_t current_minimum = std::numeric_limits<uint64_t>::max();
    size_t current_position = 0;
    uint64_t checksum = 0;
    size_t windows = 0;
    const auto start = std::chrono::steady_clock::now();

    for (size_t position = 0; position < score_count; ++position) {
        uint64_t score = 0;
        if (!generator->next(&score)) {
            return false;
        }
        (*ring)[position % W] = score;
        if (position < W) {
            if (score < current_minimum) {
                current_minimum = score;
                current_position = position;
            }
            if (position + 1U == W) {
                checksum = checksum_window(checksum, current_minimum,
                                           current_position, 0U);
                ++windows;
            }
            continue;
        }

        const size_t window_start = position - W + 1U;
        const size_t departed_position = window_start - 1U;
        if (departed_position == current_position) {
            current_minimum = std::numeric_limits<uint64_t>::max();
            for (size_t offset = 0; offset < W; ++offset) {
                const size_t candidate_position = window_start + offset;
                const uint64_t candidate =
                    (*ring)[candidate_position % W];
                if (candidate < current_minimum) {
                    current_minimum = candidate;
                    current_position = candidate_position;
                }
            }
        } else if (score < current_minimum) {
            current_minimum = score;
            current_position = position;
        }
        checksum = checksum_window(checksum, current_minimum,
                                   current_position, window_start);
        ++windows;
    }
    const auto end = std::chrono::steady_clock::now();
    result->seconds = std::chrono::duration<double>(end - start).count();
    result->checksum = checksum;
    result->scores = score_count;
    result->windows = windows;
    benchmark_sink ^= checksum;
    return windows == score_count - W + 1U;
}

bool run_kssd(const std::string &sequence,
              uint64_t seed,
              RunResult *result) {
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    const kssd_array_status_t status =
        kssd_array_init(&context, K, seed);
    if (status != KSSD_ARRAY_OK) {
        std::fprintf(stderr, "KSSD-Array initialization failed: %s\n",
                     kssd_array_status_string(status));
        return false;
    }
    const size_t scores = sequence.size() - K + 1U;
    std::vector<uint64_t> ring(W);
    CanonicalTwoBitGenerator<K> generator(sequence, &context);
    const bool ok = run_shared_minimizers(&generator, scores, &ring, result) &&
                    generator.produced() == scores;
    kssd_array_destroy(&context);
    return ok;
}

bool run_nthash(const std::string &sequence, RunResult *result) {
    const size_t scores = sequence.size() - K + 1U;
    std::vector<uint64_t> ring(W);
    NtHashGenerator<K> generator(sequence);
    return run_shared_minimizers(&generator, scores, &ring, result) &&
           generator.produced() == scores;
}

bool validation_line(const char *name, bool passed, size_t observations) {
    std::printf("VALIDATION\t%s\t%s\t%zu\n", name,
                passed ? "PASS" : "FAIL", observations);
    return passed;
}

bool validate_rolling_and_api() {
    const std::string fixture =
        "ACGTTGCATGTCGCATGATGCATGAGAGCTTAGCGGATCCGATGCTAGCATCGATCGTACG"
        "TATGCCGTAGCTAGGCTAACCGGTTAACCGGTTAGCATGCTAGCTGATCGTAGCTAGCATC"
        "GGATCGATGCACTGATCGTACGATCGTAGCTAGCGTACGATCGGCTAACGTAGCTAGCATG";
    if (fixture.size() < static_cast<size_t>(K + W - 1U)) {
        return false;
    }
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    if (kssd_array_init(&context, K, KSSD_ARRAY_DEFAULT_SEED) !=
        KSSD_ARRAY_OK) {
        return false;
    }
    const size_t scores = fixture.size() - K + 1U;
    CanonicalTwoBitGenerator<K> rolling(fixture, &context);
    bool forward_ok = true;
    bool reverse_ok = true;
    bool canonical_ok = true;
    bool fast_ok = true;
    bool invariance_ok = true;
    for (size_t position = 0; position < scores; ++position) {
        uint64_t mapped = 0;
        if (!rolling.next(&mapped)) {
            kssd_array_destroy(&context);
            return false;
        }
        const uint64_t direct_fwd = direct_forward<K>(fixture, position);
        const uint64_t direct_rev =
            direct_reverse_complement<K>(fixture, position);
        const uint64_t direct_canonical = std::min(direct_fwd, direct_rev);
        forward_ok = forward_ok && rolling.forward() == direct_fwd;
        reverse_ok = reverse_ok && rolling.reverse() == direct_rev;
        canonical_ok = canonical_ok &&
                       rolling.canonical() == direct_canonical;
        uint64_t checked = 0;
        const kssd_array_status_t checked_status =
            kssd_array_map(&context, direct_canonical, &checked);
        fast_ok = fast_ok && checked_status == KSSD_ARRAY_OK &&
                  checked == mapped &&
                  kssd_array_map_unchecked(&context, direct_canonical) == mapped;

        const std::string kmer = fixture.substr(position, K);
        const std::string rc = reverse_complement<K>(kmer);
        const uint64_t rc_fwd = direct_forward<K>(rc, 0U);
        const uint64_t rc_rev = direct_reverse_complement<K>(rc, 0U);
        const uint64_t rc_canonical = std::min(rc_fwd, rc_rev);
        invariance_ok = invariance_ok &&
                        rc_canonical == direct_canonical &&
                        kssd_array_fast_with_tables(rc_canonical, &context) ==
                            mapped;
    }

    std::vector<uint64_t> ring_a(W);
    std::vector<uint64_t> ring_b(W);
    CanonicalTwoBitGenerator<K> kssd_a(fixture, &context);
    CanonicalTwoBitGenerator<K> kssd_b(fixture, &context);
    RunResult kssd_result_a;
    RunResult kssd_result_b;
    const bool kssd_run_ok =
        run_shared_minimizers(&kssd_a, scores, &ring_a, &kssd_result_a) &&
        run_shared_minimizers(&kssd_b, scores, &ring_b, &kssd_result_b);

    NtHashGenerator<K> nthash_a(fixture);
    NtHashGenerator<K> nthash_b(fixture);
    RunResult nthash_result_a;
    RunResult nthash_result_b;
    const bool nthash_run_ok =
        run_shared_minimizers(&nthash_a, scores, &ring_a, &nthash_result_a) &&
        run_shared_minimizers(&nthash_b, scores, &ring_b, &nthash_result_b);

    const size_t expected_windows = scores - W + 1U;
    const bool counts_ok =
        rolling.produced() == scores &&
        kssd_result_a.scores == scores &&
        kssd_result_b.scores == scores &&
        nthash_result_a.scores == scores &&
        nthash_result_b.scores == scores &&
        kssd_result_a.windows == expected_windows &&
        kssd_result_b.windows == expected_windows &&
        nthash_result_a.windows == expected_windows &&
        nthash_result_b.windows == expected_windows &&
        kssd_a.produced() == scores && kssd_b.produced() == scores &&
        nthash_a.produced() == scores && nthash_b.produced() == scores;
    const bool deterministic_ok =
        kssd_run_ok && nthash_run_ok &&
        kssd_result_a.checksum == kssd_result_b.checksum &&
        nthash_result_a.checksum == nthash_result_b.checksum;

    bool passed = true;
    passed = validation_line("rolling_forward_vs_direct", forward_ok,
                             scores) && passed;
    passed = validation_line("rolling_reverse_complement_vs_direct",
                             reverse_ok, scores) && passed;
    passed = validation_line("canonical_integer_vs_direct", canonical_ok,
                             scores) && passed;
    passed = validation_line("fast_vs_context_api", fast_ok, scores) && passed;
    passed = validation_line("reverse_complement_invariance", invariance_ok,
                             scores) && passed;
    passed = validation_line("score_and_window_counts", counts_ok,
                             expected_windows) && passed;
    passed = validation_line("deterministic_method_checksums",
                             deterministic_ok, 2U) && passed;
    std::printf("VALIDATION_CHECKSUM\tKSSD-Array\t%016" PRIx64 "\n",
                kssd_result_a.checksum);
    std::printf("VALIDATION_CHECKSUM\tntHash\t%016" PRIx64 "\n",
                nthash_result_a.checksum);
    std::printf("VALIDATION_COUNTS\t%zu\t%zu\t%zu\t%zu\n",
                fixture.size(), scores, expected_windows, expected_windows);
    kssd_array_destroy(&context);
    return passed;
}

void print_run(const char *method,
               const SequenceInput &input,
               const RunResult &result,
               uint64_t seed) {
    const size_t expected_scores = input.cleaned.size() - K + 1U;
    const size_t expected_windows = expected_scores - W + 1U;
    const double throughput =
        static_cast<double>(result.windows) / result.seconds;
    std::printf(
        "META\t%zu\t%zu\t%zu\t%zu\t%zu\t%d\t%d\t%" PRIu64 "\n",
        input.raw_bases, input.cleaned.size(), input.ambiguous_bases,
        expected_scores, expected_windows, K, W, seed);
    std::printf(
        "RESULT\t%s\t%.12f\t%.12f\t%.12f\t%zu\t%zu\t%zu\t%016" PRIx64
        "\n",
        method, result.seconds, throughput, throughput / 1.0e6,
        result.scores, result.windows, result.windows, result.checksum);
}

}  // namespace

int main(int argc, char **argv) {
    if (argc == 2 && std::string(argv[1]) == "--validate") {
        const bool passed = validate_rolling_and_api();
        std::printf("VALIDATION_SUMMARY\t%s\tK=%d\tW=%d\n",
                    passed ? "PASS" : "FAIL", K, W);
        return passed ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    if (argc != 5 || std::string(argv[1]) != "--run") {
        std::fprintf(stderr,
                     "usage: %s --validate | --run METHOD FASTA SEED\n",
                     argv[0]);
        return EXIT_FAILURE;
    }
    const std::string method = argv[2];
    const uint64_t seed = std::strtoull(argv[4], nullptr, 10);
    SequenceInput input;
    if (!read_first_fasta_record(argv[3], &input)) {
        return EXIT_FAILURE;
    }
    if (input.cleaned.size() < static_cast<size_t>(K + W - 1U)) {
        std::fprintf(stderr,
                     "first FASTA record is too short after cleaning\n");
        return EXIT_FAILURE;
    }
    RunResult result;
    bool passed = false;
    if (method == "KSSD-Array") {
        passed = run_kssd(input.cleaned, seed, &result);
    } else if (method == "ntHash") {
        passed = run_nthash(input.cleaned, &result);
    } else {
        std::fprintf(stderr, "unknown method: %s\n", method.c_str());
        return EXIT_FAILURE;
    }
    if (!passed) {
        std::fprintf(stderr, "benchmark execution failed\n");
        return EXIT_FAILURE;
    }
    print_run(method.c_str(), input, result, seed);
    return EXIT_SUCCESS;
}
