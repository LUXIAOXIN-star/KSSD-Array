#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <zlib.h>

#define XXH_STATIC_LINKING_ONLY
#include <xxhash.h>

#include <kssd_array.h>

#ifndef K
#define K 21
#endif

#ifndef W
#define W 20
#endif

#define KSSD_ARRAY_FIXED_K K
#include <kssd_array_fast.h>

#if K < 1 || K > 32
#error "K must be in the range 1..32"
#endif

#if W < 1
#error "W must be positive"
#endif

#if K == 32
#define KMER_MASK UINT64_MAX
#else
#define KMER_MASK ((UINT64_C(1) << (2U * K)) - UINT64_C(1))
#endif

typedef struct {
    uint64_t *values;
    size_t count;
    size_t capacity;
    size_t valid_bases;
    size_t ambiguous_bases;
} encoded_input_t;

typedef struct {
    size_t range_start;
    size_t range_end;
    size_t processed_windows;
    uint64_t coverage_checksum;
    uint64_t final_minimum;
    size_t final_position;
    int active;
} worker_state_t;

typedef struct {
    double runtime_seconds;
    double throughput_windows_per_second;
    size_t minimizer_count;
    uint64_t checksum;
    uint64_t coverage_checksum;
    int observed_threads;
    int nonempty_workers;
    size_t processed_windows;
} benchmark_result_t;

typedef benchmark_result_t (*benchmark_function_t)(
    const uint64_t *, size_t, const kssd_array_t *, const uint64_t *, int);

static volatile uint64_t benchmark_sink = UINT64_C(0);

static uint64_t monotonic_nanoseconds(void)
{
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) +
           (uint64_t)value.tv_nsec;
}

static int base_code(int character, uint8_t *code)
{
    switch (character) {
    case 'A':
    case 'a':
        *code = UINT8_C(0);
        return 1;
    case 'C':
    case 'c':
        *code = UINT8_C(1);
        return 1;
    case 'G':
    case 'g':
        *code = UINT8_C(2);
        return 1;
    case 'T':
    case 't':
        *code = UINT8_C(3);
        return 1;
    default:
        return 0;
    }
}

static int append_kmer(encoded_input_t *input, uint64_t value)
{
    if (input->count == input->capacity) {
        const size_t next_capacity =
            input->capacity == 0U ? 4096U : input->capacity * 2U;
        uint64_t *next_values;
        if (next_capacity < input->capacity) {
            return 0;
        }
        next_values = (uint64_t *)realloc(
            input->values, next_capacity * sizeof(*next_values));
        if (next_values == NULL) {
            return 0;
        }
        input->values = next_values;
        input->capacity = next_capacity;
    }
    input->values[input->count++] = value;
    return 1;
}

/* Read only the first record and skip non-ACGT symbols without a reset. */
static int read_first_fasta_record(const char *path, encoded_input_t *input)
{
    gzFile file = gzopen(path, "rb");
    uint64_t rolling = UINT64_C(0);
    size_t rolling_bases = 0U;
    int at_line_start = 1;
    int in_header = 0;
    int found_record = 0;
    int character;

    if (file == NULL) {
        fprintf(stderr, "cannot open FASTA input %s\n", path);
        return 0;
    }
    memset(input, 0, sizeof(*input));
    while ((character = gzgetc(file)) != -1) {
        if (at_line_start != 0 && character == '>') {
            if (found_record != 0) {
                break;
            }
            found_record = 1;
            in_header = 1;
            at_line_start = 0;
            continue;
        }
        if (character == '\n' || character == '\r') {
            in_header = 0;
            at_line_start = 1;
            continue;
        }
        at_line_start = 0;
        if (found_record == 0 || in_header != 0 ||
            character == ' ' || character == '\t') {
            continue;
        }
        {
            uint8_t code;
            if (!base_code(character, &code)) {
                ++input->ambiguous_bases;
                continue;
            }
            ++input->valid_bases;
            ++rolling_bases;
            rolling = ((rolling << 2U) | (uint64_t)code) & KMER_MASK;
            if (rolling_bases >= (size_t)K &&
                !append_kmer(input, rolling)) {
                fputs("cannot allocate encoded k-mer array\n", stderr);
                gzclose(file);
                free(input->values);
                memset(input, 0, sizeof(*input));
                return 0;
            }
        }
    }
    if (gzclose(file) != Z_OK) {
        fprintf(stderr, "cannot close FASTA input %s\n", path);
        free(input->values);
        memset(input, 0, sizeof(*input));
        return 0;
    }
    if (found_record == 0) {
        fprintf(stderr, "input is not FASTA: %s\n", path);
        free(input->values);
        memset(input, 0, sizeof(*input));
        return 0;
    }
    return 1;
}

static uint64_t rotate_left64(uint64_t value, unsigned int count)
{
    return (value << count) | (value >> (64U - count));
}

/* Benchmark-only MurmurHash3/wyhash adaptations; see THIRD_PARTY_NOTICES.md. */
static uint64_t murmur_fmix64(uint64_t value)
{
    value ^= value >> 33U;
    value *= UINT64_C(0xff51afd7ed558ccd);
    value ^= value >> 33U;
    value *= UINT64_C(0xc4ceb9fe1a85ec53);
    value ^= value >> 33U;
    return value;
}

static uint64_t murmurhash3_8bytes(uint64_t key)
{
    uint64_t h1 = UINT64_C(0);
    uint64_t h2 = UINT64_C(0);
    uint64_t k1 = key;

    k1 *= UINT64_C(0x87c37b91114253d5);
    k1 = rotate_left64(k1, 31U);
    k1 *= UINT64_C(0x4cf5ad432745937f);
    h1 ^= k1;
    h1 ^= UINT64_C(8);
    h2 ^= UINT64_C(8);
    h1 += h2;
    h2 += h1;
    h1 = murmur_fmix64(h1);
    h2 = murmur_fmix64(h2);
    h1 += h2;
    return h1;
}

static void wy_multiply(uint64_t *left, uint64_t *right)
{
#if defined(__SIZEOF_INT128__)
    const __uint128_t product =
        (__uint128_t)(*left) * (__uint128_t)(*right);
    *left = (uint64_t)product;
    *right = (uint64_t)(product >> 64U);
#else
#error "This migrated wyhash path requires compiler support for uint128"
#endif
}

static uint64_t wy_mix(uint64_t left, uint64_t right)
{
    wy_multiply(&left, &right);
    return left ^ right;
}

static uint64_t wy_random(uint64_t *seed)
{
    *seed += UINT64_C(0xa0761d6478bd642f);
    return wy_mix(*seed, *seed ^ UINT64_C(0xe7037ed1a0b428db));
}

static void wy_make_secret(uint64_t seed, uint64_t secret[4])
{
    static const uint8_t choices[] = {
        15, 23, 27, 29, 30, 39, 43, 45, 46, 51, 53, 54, 57, 58,
        60, 71, 75, 77, 78, 83, 85, 86, 89, 90, 92, 99, 101, 102,
        105, 106, 108, 113, 114, 116, 120, 135, 139, 141, 142, 147,
        149, 150, 153, 154, 156, 163, 165, 166, 169, 170, 172, 177,
        178, 180, 184, 195, 197, 198, 201, 202, 204, 209, 210, 212,
        216, 225, 226, 228, 232, 240};
    size_t index;

    for (index = 0U; index < 4U; ++index) {
        int acceptable;
        do {
            size_t byte_index;
            size_t previous;
            acceptable = 1;
            secret[index] = UINT64_C(0);
            for (byte_index = 0U; byte_index < 8U; ++byte_index) {
                secret[index] |=
                    (uint64_t)choices[wy_random(&seed) %
                                      (sizeof(choices) / sizeof(choices[0]))]
                    << (8U * byte_index);
            }
            if ((secret[index] & UINT64_C(1)) == UINT64_C(0)) {
                acceptable = 0;
            }
            for (previous = 0U;
                 acceptable != 0 && previous < index;
                 ++previous) {
                if (__builtin_popcountll(secret[previous] ^ secret[index]) !=
                    32) {
                    acceptable = 0;
                }
            }
        } while (acceptable == 0);
    }
}

static uint64_t wyhash_8bytes(uint64_t key, const uint64_t secret[4])
{
    uint32_t words[2];
    const uint64_t seed = wy_mix(secret[0], secret[1]);
    uint64_t left;
    uint64_t right;

    memcpy(words, &key, sizeof(words));
    left = ((uint64_t)words[0] << 32U) | (uint64_t)words[1];
    right = ((uint64_t)words[1] << 32U) | (uint64_t)words[0];
    left ^= secret[1];
    right ^= seed;
    wy_multiply(&left, &right);
    return wy_mix(left ^ secret[0] ^ UINT64_C(8),
                  right ^ secret[1]);
}

static uint64_t sink_mix(uint64_t hash, size_t position, size_t window_start)
{
    return hash ^ ((uint64_t)position << 32U) ^ (uint64_t)window_start;
}

#define DEFINE_MULTITHREAD_BENCHMARK(function_name, hash_expression)           \
    static benchmark_result_t function_name(                                  \
        const uint64_t *kmers, size_t kmer_count,                              \
        const kssd_array_t *context, const uint64_t *wy_secret,                \
        int requested_threads)                                                 \
    {                                                                           \
        benchmark_result_t result;                                              \
        const size_t window_count = kmer_count - (size_t)W + 1U;               \
        worker_state_t *states = (worker_state_t *)calloc(                      \
            (size_t)requested_threads, sizeof(*states));                        \
        int observed_threads = 0;                                               \
        int nonempty_workers = 0;                                               \
        size_t processed_windows = 0U;                                          \
        uint64_t coverage_checksum = UINT64_C(0);                               \
        uint64_t final_minimum = UINT64_C(0);                                   \
        size_t final_position = 0U;                                             \
        size_t final_range_end = 0U;                                            \
        uint64_t start;                                                         \
        uint64_t end;                                                           \
        int worker;                                                             \
        (void)context;                                                          \
        (void)wy_secret;                                                        \
        if (states == NULL) {                                                   \
            fputs("cannot allocate per-thread benchmark state\n", stderr);    \
            exit(EXIT_FAILURE);                                                 \
        }                                                                       \
        start = monotonic_nanoseconds();                                        \
        _Pragma("omp parallel num_threads(requested_threads) shared(states, observed_threads)") \
        {                                                                       \
            const int thread_id = omp_get_thread_num();                         \
            const int thread_count = omp_get_num_threads();                     \
            const size_t range_start =                                          \
                (window_count * (size_t)thread_id) / (size_t)thread_count;       \
            const size_t range_end =                                            \
                (window_count * (size_t)(thread_id + 1)) /                      \
                (size_t)thread_count;                                           \
            worker_state_t *state = &states[thread_id];                         \
            _Pragma("omp single")                                              \
            observed_threads = thread_count;                                    \
            state->range_start = range_start;                                   \
            state->range_end = range_end;                                       \
            if (range_start < range_end) {                                      \
                uint64_t current_minimum = UINT64_MAX;                          \
                uint64_t local_coverage_checksum = UINT64_C(0);                \
                size_t current_position = range_start;                          \
                size_t local_processed_windows = 0U;                            \
                size_t offset;                                                  \
                size_t window_start;                                            \
                state->active = 1;                                              \
                for (offset = 0U; offset < (size_t)W; ++offset) {               \
                    const uint64_t kmer = kmers[range_start + offset];           \
                    const uint64_t hash = (hash_expression);                    \
                    if (hash < current_minimum) {                               \
                        current_minimum = hash;                                 \
                        current_position = range_start + offset;                \
                    }                                                           \
                }                                                               \
                local_coverage_checksum ^= sink_mix(                            \
                    current_minimum, current_position, range_start);            \
                ++local_processed_windows;                                      \
                for (window_start = range_start + 1U;                           \
                     window_start < range_end;                                  \
                     ++window_start) {                                          \
                    const size_t previous_position = window_start - 1U;         \
                    const size_t new_position =                                 \
                        window_start + (size_t)W - 1U;                          \
                    if (previous_position == current_position) {                \
                        current_minimum = UINT64_MAX;                           \
                        for (offset = 0U; offset < (size_t)W; ++offset) {       \
                            const size_t position = window_start + offset;      \
                            const uint64_t kmer = kmers[position];              \
                            const uint64_t hash = (hash_expression);            \
                            if (hash < current_minimum) {                       \
                                current_minimum = hash;                         \
                                current_position = position;                   \
                            }                                                   \
                        }                                                       \
                    } else {                                                    \
                        const uint64_t kmer = kmers[new_position];              \
                        const uint64_t hash = (hash_expression);                \
                        if (hash < current_minimum) {                           \
                            current_minimum = hash;                             \
                            current_position = new_position;                   \
                        }                                                       \
                    }                                                           \
                    local_coverage_checksum ^= sink_mix(                        \
                        current_minimum, current_position, window_start);       \
                    ++local_processed_windows;                                  \
                }                                                               \
                state->coverage_checksum = local_coverage_checksum;             \
                state->processed_windows = local_processed_windows;             \
                state->final_minimum = current_minimum;                         \
                state->final_position = current_position;                       \
            }                                                                   \
        }                                                                       \
        for (worker = 0; worker < observed_threads; ++worker) {                 \
            const worker_state_t *state = &states[worker];                      \
            coverage_checksum ^= state->coverage_checksum;                     \
            processed_windows += state->processed_windows;                     \
            if (state->active != 0) {                                          \
                ++nonempty_workers;                                             \
                if (state->range_end >= final_range_end) {                     \
                    final_range_end = state->range_end;                         \
                    final_minimum = state->final_minimum;                       \
                    final_position = state->final_position;                     \
                }                                                               \
            }                                                                   \
        }                                                                       \
        end = monotonic_nanoseconds();                                          \
        result.runtime_seconds = (double)(end - start) / 1000000000.0;         \
        result.throughput_windows_per_second =                                  \
            (double)window_count / result.runtime_seconds;                      \
        result.minimizer_count = processed_windows;                            \
        result.checksum = final_minimum ^ (uint64_t)final_position;            \
        result.coverage_checksum = coverage_checksum;                          \
        result.observed_threads = observed_threads;                            \
        result.nonempty_workers = nonempty_workers;                            \
        result.processed_windows = processed_windows;                          \
        benchmark_sink ^= result.checksum ^ result.coverage_checksum;          \
        free(states);                                                           \
        return result;                                                          \
    }

DEFINE_MULTITHREAD_BENCHMARK(
    benchmark_kssd_array,
    kssd_array_fast_with_tables(kmer, context))
DEFINE_MULTITHREAD_BENCHMARK(
    benchmark_xxh3,
    XXH3_64bits_withSeed(&kmer, sizeof(kmer), UINT64_C(0)))
DEFINE_MULTITHREAD_BENCHMARK(
    benchmark_xxh64,
    XXH64(&kmer, sizeof(kmer), UINT64_C(0)))
DEFINE_MULTITHREAD_BENCHMARK(
    benchmark_murmurhash3,
    murmurhash3_8bytes(kmer))
DEFINE_MULTITHREAD_BENCHMARK(
    benchmark_wyhash,
    wyhash_8bytes(kmer, wy_secret))

static int parse_uint64(const char *text, uint64_t *value)
{
    char *end = NULL;
    unsigned long long parsed;
    errno = 0;
    parsed = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        return 0;
    }
    *value = (uint64_t)parsed;
    return 1;
}

static int verify_fast_parity(const encoded_input_t *input,
                              const kssd_array_t *context,
                              size_t *checked)
{
    const size_t sample_count = input->count < 1024U ? input->count : 1024U;
    size_t index;
    for (index = 0U; index < sample_count; ++index) {
        const uint64_t encoded = input->values[index];
        if (kssd_array_map_unchecked(context, encoded) !=
            kssd_array_fast_with_tables(encoded, context)) {
            fprintf(stderr, "fast/context parity failed at sample %zu\n",
                    index);
            return 0;
        }
    }
    *checked = sample_count;
    return sample_count > 0U;
}

static int observe_thread_count(int requested_threads)
{
    int observed = 0;
    _Pragma("omp parallel num_threads(requested_threads) shared(observed)")
    {
        _Pragma("omp single")
        observed = omp_get_num_threads();
    }
    return observed;
}

int main(int argc, char **argv)
{
    static const char *method_names[] = {
        "KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "wyhash"};
    static const benchmark_function_t benchmark_functions[] = {
        benchmark_kssd_array,
        benchmark_xxh3,
        benchmark_xxh64,
        benchmark_murmurhash3,
        benchmark_wyhash};
    encoded_input_t input;
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    uint64_t repeat;
    uint64_t seed;
    uint64_t requested_value;
    uint64_t wy_secret[4];
    size_t window_count;
    size_t parity_checked = 0U;
    size_t method;
    int requested_threads;
    int observed_threads;

    if (argc != 5) {
        fprintf(stderr, "usage: %s FASTA REPEAT SEED THREADS\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (!parse_uint64(argv[2], &repeat) || repeat == UINT64_C(0) ||
        !parse_uint64(argv[3], &seed) ||
        !parse_uint64(argv[4], &requested_value) ||
        requested_value == UINT64_C(0) || requested_value > (uint64_t)INT32_MAX) {
        fputs("REPEAT and THREADS must be positive; SEED must be an integer\n",
              stderr);
        return EXIT_FAILURE;
    }
    requested_threads = (int)requested_value;
    omp_set_dynamic(0);
    if (!read_first_fasta_record(argv[1], &input)) {
        return EXIT_FAILURE;
    }
    if (input.count < (size_t)W) {
        fprintf(stderr, "input has %zu k-mers but W=%d requires at least %d\n",
                input.count, W, W);
        free(input.values);
        return EXIT_FAILURE;
    }
    window_count = input.count - (size_t)W + 1U;
    if (kssd_array_init(&context, (size_t)K, seed) != KSSD_ARRAY_OK) {
        fputs("cannot initialize public KSSD-Array context\n", stderr);
        free(input.values);
        return EXIT_FAILURE;
    }
    if (!verify_fast_parity(&input, &context, &parity_checked)) {
        kssd_array_destroy(&context);
        free(input.values);
        return EXIT_FAILURE;
    }
    wy_make_secret(seed, wy_secret);
    observed_threads = observe_thread_count(requested_threads);

    printf("META\t%zu\t%zu\t%zu\t%zu\t%d\t%d\t%" PRIu64
           "\t%" PRIu64 "\t%d\t%d\t%d\n",
           input.valid_bases, input.ambiguous_bases, input.count,
           window_count, K, W, repeat, seed, requested_threads,
           observed_threads, _OPENMP);
    printf("PARITY\tPASS\t%zu\n", parity_checked);

    for (method = 0U;
         method < sizeof(method_names) / sizeof(method_names[0]);
         ++method) {
        const benchmark_result_t result = benchmark_functions[method](
            input.values, input.count, &context, wy_secret,
            requested_threads);
        printf("RESULT\t%s\t%.9f\t%.3f\t%zu\t%zu\t%zu\t%" PRIu64
               "\t%" PRIu64 "\t%d\t%d\t%d\t%zu\n",
               method_names[method], result.runtime_seconds,
               result.throughput_windows_per_second, input.count,
               window_count, result.minimizer_count, result.checksum,
               result.coverage_checksum, requested_threads,
               result.observed_threads, result.nonempty_workers,
               result.processed_windows);
    }

    kssd_array_destroy(&context);
    free(input.values);
    (void)benchmark_sink;
    return EXIT_SUCCESS;
}
