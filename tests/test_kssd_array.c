#include <inttypes.h>
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <kssd_array.h>

#define ARRAY_LENGTH(values) (sizeof(values) / sizeof((values)[0]))
#define CHECK(expression)                                                     \
    do {                                                                      \
        if (!(expression)) {                                                  \
            fprintf(stderr, "%s:%d: check failed: %s\n",                    \
                    __FILE__, __LINE__, #expression);                         \
            return 0;                                                         \
        }                                                                     \
    } while (0)

static size_t pow4_size(size_t k)
{
    return (size_t)1U << (2U * k);
}

static uint64_t kmer_mask(size_t k)
{
    return k == KSSD_ARRAY_MAX_K
               ? UINT64_MAX
               : (UINT64_C(1) << (2U * k)) - UINT64_C(1);
}

static int is_permutation(const uint16_t *permutation, size_t size)
{
    unsigned char *seen = (unsigned char *)calloc(size, sizeof(*seen));
    size_t index;

    if (permutation == NULL || seen == NULL) {
        free(seen);
        return 0;
    }
    for (index = 0U; index < size; ++index) {
        const size_t value = (size_t)permutation[index];
        if (value >= size || seen[value] != 0U) {
            free(seen);
            return 0;
        }
        seen[value] = 1U;
    }
    free(seen);
    return 1;
}

static int test_layouts(void)
{
    static const size_t cases[] = {1U, 4U, 8U, 9U, 16U,
                                   19U, 21U, 24U, 31U, 32U};
    size_t case_index;

    for (case_index = 0U; case_index < ARRAY_LENGTH(cases); ++case_index) {
        const size_t k = cases[case_index];
        const size_t expected_count =
            (k + KSSD_ARRAY_SEGMENT_CAP - 1U) / KSSD_ARRAY_SEGMENT_CAP;
        const size_t quotient = k / expected_count;
        const size_t remainder = k % expected_count;
        kssd_array_layout_t layout;
        size_t sum = 0U;
        size_t index;

        CHECK(kssd_array_layout(k, KSSD_ARRAY_SEGMENT_CAP, &layout) ==
              KSSD_ARRAY_OK);
        CHECK(layout.segment_count == expected_count);
        for (index = 0U; index < expected_count; ++index) {
            CHECK(layout.segment_lengths[index] ==
                  quotient + (index < remainder ? 1U : 0U));
            CHECK(layout.segment_lengths[index] <= KSSD_ARRAY_SEGMENT_CAP);
            sum += layout.segment_lengths[index];
        }
        CHECK(sum == k);
        CHECK(layout.master_length == layout.segment_lengths[0]);
    }
    return 1;
}

static int test_rank_derived_tables(void)
{
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    const uint16_t *master;
    size_t master_size;
    size_t segment_length;

    CHECK(kssd_array_init(&context, 31U, KSSD_ARRAY_DEFAULT_SEED) ==
          KSSD_ARRAY_OK);
    master = kssd_array_master_permutation(&context, &master_size);
    CHECK(master_size == pow4_size(context.layout.master_length));
    CHECK(is_permutation(master, master_size));

    for (segment_length = 1U;
         segment_length <= context.layout.master_length;
         ++segment_length) {
        const uint16_t *derived;
        const size_t size = pow4_size(segment_length);
        size_t reported_size;

        derived = kssd_array_permutation(&context,
                                         segment_length,
                                         &reported_size);
        CHECK(reported_size == size);
        CHECK(is_permutation(derived, size));
        if (segment_length < context.layout.master_length) {
            uint16_t *selected =
                (uint16_t *)malloc(size * sizeof(*selected));
            const size_t shift =
                2U * (context.layout.master_length - segment_length);
            size_t input;
            size_t rank;

            CHECK(selected != NULL);
            for (input = 0U; input < size; ++input) {
                selected[derived[input]] = master[input << shift];
            }
            for (rank = 1U; rank < size; ++rank) {
                if (selected[rank - 1U] >= selected[rank]) {
                    free(selected);
                    kssd_array_destroy(&context);
                    return 0;
                }
            }
            free(selected);
        }
    }
    kssd_array_destroy(&context);
    return 1;
}

static int exhaustive_injectivity(size_t k)
{
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    const size_t size = pow4_size(k);
    unsigned char *seen = (unsigned char *)calloc(size, sizeof(*seen));
    size_t input;

    CHECK(seen != NULL);
    CHECK(kssd_array_init(&context, k, KSSD_ARRAY_DEFAULT_SEED) ==
          KSSD_ARRAY_OK);
    for (input = 0U; input < size; ++input) {
        uint64_t mapped = UINT64_MAX;
        CHECK(kssd_array_map(&context, (uint64_t)input, &mapped) ==
              KSSD_ARRAY_OK);
        CHECK(mapped < (uint64_t)size);
        CHECK(mapped == kssd_array_map_unchecked(&context, (uint64_t)input));
        CHECK(seen[(size_t)mapped] == 0U);
        seen[(size_t)mapped] = 1U;
    }
    free(seen);
    kssd_array_destroy(&context);
    return 1;
}

static int test_boundaries_and_determinism(void)
{
    static const size_t cases[] = {4U, 9U, 16U, 19U,
                                   21U, 24U, 31U, 32U};
    size_t case_index;

    for (case_index = 0U; case_index < ARRAY_LENGTH(cases); ++case_index) {
        const size_t k = cases[case_index];
        const uint64_t mask = kmer_mask(k);
        const uint64_t inputs[] = {
            UINT64_C(0), UINT64_C(1) & mask, mask, mask >> 1U,
            UINT64_C(0x0123456789abcdef) & mask,
            UINT64_C(0xfedcba9876543210) & mask};
        kssd_array_t first = KSSD_ARRAY_CONTEXT_INIT;
        kssd_array_t second = KSSD_ARRAY_CONTEXT_INIT;
        size_t input_index;

        CHECK(kssd_array_init(&first, k, KSSD_ARRAY_DEFAULT_SEED) ==
              KSSD_ARRAY_OK);
        CHECK(kssd_array_init(&second, k, KSSD_ARRAY_DEFAULT_SEED) ==
              KSSD_ARRAY_OK);
        CHECK(first.master_size == second.master_size);
        CHECK(memcmp(first.master_permutation,
                     second.master_permutation,
                     first.master_size * sizeof(*first.master_permutation)) ==
              0);
        for (input_index = 0U; input_index < ARRAY_LENGTH(inputs);
             ++input_index) {
            uint64_t mapped;
            CHECK(kssd_array_map(&first, inputs[input_index], &mapped) ==
                  KSSD_ARRAY_OK);
            CHECK(mapped == kssd_array_map_unchecked(&second,
                                                      inputs[input_index]));
            CHECK(k == 32U || (mapped & ~mask) == 0U);
        }
        kssd_array_destroy(&second);
        kssd_array_destroy(&first);
    }
    return 1;
}

static int test_glibc_compatibility(void)
{
    static const uint16_t expected[] = {
        UINT16_C(59805), UINT16_C(16426), UINT16_C(29732), UINT16_C(55859),
        UINT16_C(58159), UINT16_C(60961), UINT16_C(13042), UINT16_C(57056)};
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;

    CHECK(kssd_array_init_with_rng(&context,
                                   31U,
                                   KSSD_ARRAY_DEFAULT_SEED,
                                   KSSD_ARRAY_RNG_GLIBC_COMPAT) ==
          KSSD_ARRAY_OK);
    CHECK(memcmp(context.master_permutation, expected, sizeof(expected)) == 0);
    kssd_array_destroy(&context);
    return 1;
}

static int test_errors(void)
{
    kssd_array_layout_t layout;
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    uint64_t result = UINT64_C(0xaaaaaaaaaaaaaaaa);

    CHECK(kssd_array_layout(0U, KSSD_ARRAY_SEGMENT_CAP, &layout) ==
          KSSD_ARRAY_UNSUPPORTED_K);
    CHECK(kssd_array_layout(33U, KSSD_ARRAY_SEGMENT_CAP, &layout) ==
          KSSD_ARRAY_UNSUPPORTED_K);
    CHECK(kssd_array_layout(4U, 0U, &layout) ==
          KSSD_ARRAY_INVALID_ARGUMENT);
    CHECK(kssd_array_init(NULL, 4U, 42U) == KSSD_ARRAY_INVALID_ARGUMENT);
    CHECK(kssd_array_map(&context, 0U, &result) ==
          KSSD_ARRAY_NOT_INITIALIZED);
    CHECK(kssd_array_init(&context, 4U, 42U) == KSSD_ARRAY_OK);
    CHECK(kssd_array_init(&context, 4U, 42U) ==
          KSSD_ARRAY_ALREADY_INITIALIZED);
    CHECK(kssd_array_map(&context, UINT64_C(1) << 8U, &result) ==
          KSSD_ARRAY_INPUT_OUT_OF_RANGE);
    CHECK(result == UINT64_C(0xaaaaaaaaaaaaaaaa));
    CHECK(kssd_array_map(&context, 0U, NULL) == KSSD_ARRAY_INVALID_ARGUMENT);
    CHECK(strcmp(kssd_array_status_string(KSSD_ARRAY_OK), "success") == 0);
    CHECK(strcmp(kssd_array_status_string((kssd_array_status_t)999),
                 "unknown status") == 0);
    kssd_array_destroy(&context);
    kssd_array_destroy(&context);
    return 1;
}

static int compare_uint64_numeric(const void *left, const void *right)
{
    const uint64_t a = *(const uint64_t *)left;
    const uint64_t b = *(const uint64_t *)right;
    return (a > b) - (a < b);
}

static int test_uint64_numeric_comparator(void)
{
    uint64_t values[] = {
        UINT64_MAX,
        UINT64_C(0),
        UINT64_C(0x0000000000000100),
        UINT64_C(1),
        UINT64_C(0x8000000000000000),
        (uint64_t)INT64_MAX,
        UINT64_C(0x0100000000000000),
        UINT64_C(0x0000000000010000)};
    static const uint64_t expected[] = {
        UINT64_C(0),
        UINT64_C(1),
        UINT64_C(0x0000000000000100),
        UINT64_C(0x0000000000010000),
        UINT64_C(0x0100000000000000),
        (uint64_t)INT64_MAX,
        UINT64_C(0x8000000000000000),
        UINT64_MAX};

    CHECK(compare_uint64_numeric(&values[0], &values[1]) > 0);
    CHECK(compare_uint64_numeric(&values[1], &values[0]) < 0);
    CHECK(compare_uint64_numeric(&values[2], &values[2]) == 0);
    qsort(values, ARRAY_LENGTH(values), sizeof(values[0]),
          compare_uint64_numeric);
    CHECK(memcmp(values, expected, sizeof(expected)) == 0);
    return 1;
}

typedef struct {
    const kssd_array_t *context;
    uint64_t checksum;
} thread_job_t;

static void *map_worker(void *argument)
{
    thread_job_t *job = (thread_job_t *)argument;
    uint64_t checksum = UINT64_C(0);
    uint64_t input;

    for (input = 0U; input < UINT64_C(20000); ++input) {
        checksum ^= kssd_array_map_unchecked(job->context, input);
        checksum = (checksum << 1U) | (checksum >> 63U);
    }
    job->checksum = checksum;
    return NULL;
}

static int test_concurrent_reads(void)
{
    enum { THREAD_COUNT = 4 };
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    pthread_t threads[THREAD_COUNT];
    thread_job_t jobs[THREAD_COUNT];
    size_t index;

    CHECK(kssd_array_init(&context, 19U, 42U) == KSSD_ARRAY_OK);
    for (index = 0U; index < THREAD_COUNT; ++index) {
        jobs[index].context = &context;
        jobs[index].checksum = UINT64_MAX;
        CHECK(pthread_create(&threads[index], NULL, map_worker,
                             &jobs[index]) == 0);
    }
    for (index = 0U; index < THREAD_COUNT; ++index) {
        CHECK(pthread_join(threads[index], NULL) == 0);
        CHECK(jobs[index].checksum == jobs[0].checksum);
    }
    kssd_array_destroy(&context);
    return 1;
}

int main(void)
{
    if (!test_layouts() ||
        !test_rank_derived_tables() ||
        !exhaustive_injectivity(4U) ||
        !exhaustive_injectivity(9U) ||
        !test_boundaries_and_determinism() ||
        !test_glibc_compatibility() ||
        !test_errors() ||
        !test_uint64_numeric_comparator() ||
        !test_concurrent_reads()) {
        return 1;
    }
    puts("all core library tests passed");
    return 0;
}
