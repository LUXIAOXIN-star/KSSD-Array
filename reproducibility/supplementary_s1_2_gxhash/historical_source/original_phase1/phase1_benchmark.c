#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <fcntl.h>
#include <linux/perf_event.h>
#include <omp.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>

#include <kssd_array.h>
#include "permutation.h"
#include "accepted_xxhash_shared.h"

#ifndef K
#define K 21
#endif

#if K < 1 || K > 32
#error "K must be in the range 1..32"
#endif

#define KSSD_ARRAY_FIXED_K K
#include <kssd_array_fast.h>

/* Keep the reviewer-control xxHash implementation private to this TU. */
#define XXH_NAMESPACE PHASE1_PINNED_
#define XXH_INLINE_ALL
#include "third_party/xxhash-v0.8.3/xxhash.h"

#if K == 32
#define PHASE1_DOMAIN_MASK UINT64_MAX
#else
#define PHASE1_DOMAIN_MASK \
    ((UINT64_C(1) << (2U * (unsigned)K)) - UINT64_C(1))
#endif

#define PHASE1_BASE_SEED UINT64_C(42)
#define PHASE1_ODD_A UINT64_C(0x9e3779b97f4a7c15)
#define PHASE1_AFFINE_B UINT64_C(0xd1b54a32d192ed03)
#define PHASE1_SEED_MIX UINT64_C(0x94d049bb133111eb)
#define PHASE1_MAX_METHODS 15U
#define PHASE1_MAX_W_VALUES 8U
#define PHASE1_MAX_THREADS 32U

typedef enum {
    METHOD_RANK_DERIVED = 0,
    METHOD_XXH3_PINNED_INLINE,
    METHOD_XXH64_PINNED_INLINE,
    METHOD_MURMURHASH3,
    METHOD_WYHASH,
    METHOD_IDENTITY,
    METHOD_BIT_REVERSE,
    METHOD_ODD_MULTIPLY,
    METHOD_AFFINE,
    METHOD_XORSHIFT_BIJECTIVE,
    METHOD_INDEPENDENT_SHUFFLE,
    METHOD_IDENTITY_SHORT,
    METHOD_AFFINE_SHORT,
    METHOD_XXH3_ACCEPTED_SHARED,
    METHOD_XXH64_ACCEPTED_SHARED,
    METHOD_COUNT
} method_id_t;

typedef enum {
    TABLE_RANK_DERIVED = 0,
    TABLE_INDEPENDENT_SHUFFLE,
    TABLE_IDENTITY_SHORT,
    TABLE_AFFINE_SHORT,
    TABLE_VARIANT_COUNT
} table_variant_t;

typedef struct {
    uint64_t *values;
    size_t count;
    size_t valid_bases;
    size_t ambiguous_bases;
    uint64_t checksum;
} encoded_input_t;

typedef struct {
    kssd_array_t contexts[TABLE_VARIANT_COUNT];
    uint64_t wy_secret[4];
} method_state_t;

typedef struct {
    uint64_t master_ns;
    uint64_t short_ns;
    size_t persistent_bytes;
} initialization_measurement_t;

typedef struct {
    double wall_seconds;
    double cpu_seconds;
    uint64_t tsc_cycles;
    uint64_t perf_cycles;
    uint64_t perf_instructions;
    int perf_available;
    int perf_errno;
    uint64_t checksum;
    size_t count;
} timing_result_t;

typedef struct {
    int leader_fd;
    int instruction_fd;
    int error_number;
} perf_group_t;

typedef struct {
    size_t window_count;
    size_t selected_count;
    uint64_t position_checksum;
    uint64_t score_checksum;
} window_result_t;

typedef struct {
    size_t mapping_calls;
    size_t full_rescans;
    size_t entering_updates;
    size_t selected_positions;
    size_t unique_positions;
    size_t adjacent_repeated_positions;
    uint64_t position_checksum;
    uint64_t final_checksum;
} rescan_result_t;

static volatile uint64_t phase1_sink = UINT64_C(0);

static const char *const method_names[METHOD_COUNT] = {
    "KSSD-Array-RankDerived",
    "XXH3-pinned-inline",
    "XXH64-pinned-inline",
    "MurmurHash3",
    "wyhash",
    "Identity",
    "BitReverse",
    "OddMultiply",
    "Affine",
    "XorShiftBijective",
    "IndependentShuffle",
    "IdentityShort",
    "AffineShort",
    "XXH3-accepted-shared",
    "XXH64-accepted-shared"
};

static const char *const table_variant_names[TABLE_VARIANT_COUNT] = {
    "RankDerived",
    "IndependentShuffle",
    "IdentityShort",
    "AffineShort"
};

static uint64_t monotonic_nanoseconds(void)
{
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime CLOCK_MONOTONIC");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) +
           (uint64_t)value.tv_nsec;
}

static uint64_t process_cpu_nanoseconds(void)
{
    struct timespec value;
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0) {
        perror("clock_gettime CLOCK_PROCESS_CPUTIME_ID");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) +
           (uint64_t)value.tv_nsec;
}

static uint64_t read_tsc_begin(void)
{
#if defined(__x86_64__) || defined(__i386__)
    unsigned low;
    unsigned high;
    __asm__ volatile("lfence\n\trdtsc" : "=a"(low), "=d"(high) :: "memory");
    return ((uint64_t)high << 32U) | (uint64_t)low;
#else
    return UINT64_C(0);
#endif
}

static uint64_t read_tsc_end(void)
{
#if defined(__x86_64__) || defined(__i386__)
    unsigned low;
    unsigned high;
    unsigned auxiliary;
    __asm__ volatile("rdtscp\n\tlfence"
                     : "=a"(low), "=d"(high), "=c"(auxiliary)
                     :
                     : "memory");
    (void)auxiliary;
    return ((uint64_t)high << 32U) | (uint64_t)low;
#else
    return UINT64_C(0);
#endif
}

static int perf_event_open_local(struct perf_event_attr *attribute,
                                 int group_fd)
{
    return (int)syscall(__NR_perf_event_open,
                        attribute,
                        0,
                        -1,
                        group_fd,
                        0);
}

static perf_group_t perf_group_open(void)
{
    struct perf_event_attr attribute;
    perf_group_t group;

    group.leader_fd = -1;
    group.instruction_fd = -1;
    group.error_number = 0;
    memset(&attribute, 0, sizeof(attribute));
    attribute.type = PERF_TYPE_HARDWARE;
    attribute.size = sizeof(attribute);
    attribute.config = PERF_COUNT_HW_CPU_CYCLES;
    attribute.disabled = 1;
    attribute.exclude_kernel = 1;
    attribute.exclude_hv = 1;
    group.leader_fd = perf_event_open_local(&attribute, -1);
    if (group.leader_fd < 0) {
        group.error_number = errno;
        return group;
    }
    attribute.config = PERF_COUNT_HW_INSTRUCTIONS;
    group.instruction_fd = perf_event_open_local(&attribute, group.leader_fd);
    if (group.instruction_fd < 0) {
        group.error_number = errno;
        close(group.leader_fd);
        group.leader_fd = -1;
    }
    return group;
}

static void perf_group_start(const perf_group_t *group)
{
    if (group->leader_fd >= 0) {
        (void)ioctl(group->leader_fd, PERF_EVENT_IOC_RESET,
                    PERF_IOC_FLAG_GROUP);
        (void)ioctl(group->leader_fd, PERF_EVENT_IOC_ENABLE,
                    PERF_IOC_FLAG_GROUP);
    }
}

static void perf_group_stop(perf_group_t *group,
                            uint64_t *cycles,
                            uint64_t *instructions)
{
    *cycles = UINT64_C(0);
    *instructions = UINT64_C(0);
    if (group->leader_fd < 0) {
        return;
    }
    (void)ioctl(group->leader_fd, PERF_EVENT_IOC_DISABLE,
                PERF_IOC_FLAG_GROUP);
    if (read(group->leader_fd, cycles, sizeof(*cycles)) !=
            (ssize_t)sizeof(*cycles) ||
        read(group->instruction_fd, instructions, sizeof(*instructions)) !=
            (ssize_t)sizeof(*instructions)) {
        group->error_number = errno != 0 ? errno : EIO;
        *cycles = UINT64_C(0);
        *instructions = UINT64_C(0);
    }
    close(group->instruction_fd);
    close(group->leader_fd);
    group->instruction_fd = -1;
    group->leader_fd = -1;
}

static uint64_t splitmix64_value(uint64_t value)
{
    value = (value ^ (value >> 30U)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27U)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31U);
}

static uint64_t splitmix64_next_local(uint64_t *state)
{
    *state += UINT64_C(0x9e3779b97f4a7c15);
    return splitmix64_value(*state);
}

static uint64_t checksum_update(uint64_t checksum,
                                uint64_t value,
                                size_t position)
{
    const uint64_t mixed = splitmix64_value(
        value ^ ((uint64_t)position * UINT64_C(0x9e3779b97f4a7c15)));
    return checksum ^ mixed;
}

static uint64_t selected_position_update(uint64_t checksum,
                                         size_t position,
                                         size_t window_start)
{
    return checksum ^ splitmix64_value(
        (uint64_t)position ^
        ((uint64_t)window_start * UINT64_C(0xd6e8feb86659fd93)));
}

static int base_code(int character, uint8_t *code)
{
    switch (character) {
    case 'A': case 'a': *code = UINT8_C(0); return 1;
    case 'C': case 'c': *code = UINT8_C(1); return 1;
    case 'G': case 'g': *code = UINT8_C(2); return 1;
    case 'T': case 't': *code = UINT8_C(3); return 1;
    default: return 0;
    }
}

static int read_first_fasta_record(const char *path,
                                   size_t expected_valid_bases,
                                   encoded_input_t *input)
{
    FILE *file;
    uint64_t rolling = UINT64_C(0);
    size_t rolling_bases = 0U;
    size_t expected_kmers;
    int at_line_start = 1;
    int in_header = 0;
    int found_record = 0;
    int character;

    memset(input, 0, sizeof(*input));
    if (expected_valid_bases < (size_t)K) {
        fputs("expected valid-base count is smaller than K\n", stderr);
        return 0;
    }
    expected_kmers = expected_valid_bases - (size_t)K + 1U;
    input->values = (uint64_t *)malloc(expected_kmers * sizeof(uint64_t));
    if (input->values == NULL) {
        fputs("cannot allocate exact encoded k-mer array\n", stderr);
        return 0;
    }
    file = fopen(path, "rb");
    if (file == NULL) {
        fprintf(stderr, "cannot open FASTA input %s: %s\n",
                path, strerror(errno));
        free(input->values);
        memset(input, 0, sizeof(*input));
        return 0;
    }
    while ((character = fgetc(file)) != EOF) {
        if (at_line_start && character == '>') {
            if (found_record != 0) {
                break;
            }
            found_record = 1;
            in_header = 1;
            at_line_start = 0;
            continue;
        }
        if (character == '\n' || character == '\r') {
            if (in_header != 0) {
                in_header = 0;
            }
            at_line_start = 1;
            continue;
        }
        at_line_start = 0;
        if (found_record == 0 || in_header != 0) {
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
            rolling = ((rolling << 2U) | (uint64_t)code) &
                      PHASE1_DOMAIN_MASK;
            if (rolling_bases >= (size_t)K) {
                if (input->count >= expected_kmers) {
                    fputs("processed input exceeds expected k-mer count\n",
                          stderr);
                    fclose(file);
                    free(input->values);
                    memset(input, 0, sizeof(*input));
                    return 0;
                }
                input->values[input->count++] = rolling;
            }
        }
    }
    if (ferror(file) != 0 || found_record == 0) {
        fputs("failed to read first FASTA record\n", stderr);
        fclose(file);
        free(input->values);
        memset(input, 0, sizeof(*input));
        return 0;
    }
    fclose(file);
    if (input->valid_bases != expected_valid_bases ||
        input->count != expected_kmers) {
        fprintf(stderr,
                "processed input mismatch: bases=%zu expected=%zu "
                "kmers=%zu expected=%zu\n",
                input->valid_bases, expected_valid_bases,
                input->count, expected_kmers);
        free(input->values);
        memset(input, 0, sizeof(*input));
        return 0;
    }
    {
        size_t i;
        uint64_t checksum = UINT64_C(0);
        for (i = 0U; i < input->count; ++i) {
            checksum = checksum_update(checksum, input->values[i], i);
        }
        input->checksum = checksum;
    }
    return 1;
}

static uint64_t rotate_left64(uint64_t value, unsigned int count)
{
    return (value << count) | (value >> (64U - count));
}

/* Exact accepted benchmark-local MurmurHash3 eight-byte specialization. */
static inline uint64_t murmur_fmix64(uint64_t value)
{
    value ^= value >> 33U;
    value *= UINT64_C(0xff51afd7ed558ccd);
    value ^= value >> 33U;
    value *= UINT64_C(0xc4ceb9fe1a85ec53);
    value ^= value >> 33U;
    return value;
}

static inline uint64_t murmurhash3_8bytes(uint64_t key)
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

static inline void wy_multiply(uint64_t *left, uint64_t *right)
{
#if defined(__SIZEOF_INT128__)
    const __uint128_t product =
        (__uint128_t)(*left) * (__uint128_t)(*right);
    *left = (uint64_t)product;
    *right = (uint64_t)(product >> 64U);
#else
#error "Phase 1 wyhash requires compiler support for uint128"
#endif
}

static inline uint64_t wy_mix(uint64_t left, uint64_t right)
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

static inline uint64_t wyhash_8bytes(uint64_t key,
                                     const uint64_t secret[4])
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

static inline uint64_t bit_reverse_low(uint64_t value)
{
    const unsigned width = 2U * (unsigned)K;
    value = ((value & UINT64_C(0x5555555555555555)) << 1U) |
            ((value >> 1U) & UINT64_C(0x5555555555555555));
    value = ((value & UINT64_C(0x3333333333333333)) << 2U) |
            ((value >> 2U) & UINT64_C(0x3333333333333333));
    value = ((value & UINT64_C(0x0f0f0f0f0f0f0f0f)) << 4U) |
            ((value >> 4U) & UINT64_C(0x0f0f0f0f0f0f0f0f));
    value = ((value & UINT64_C(0x00ff00ff00ff00ff)) << 8U) |
            ((value >> 8U) & UINT64_C(0x00ff00ff00ff00ff));
    value = ((value & UINT64_C(0x0000ffff0000ffff)) << 16U) |
            ((value >> 16U) & UINT64_C(0x0000ffff0000ffff));
    value = (value << 32U) | (value >> 32U);
    return width == 64U ? value : value >> (64U - width);
}

static inline uint64_t xorshift_bijective(uint64_t value)
{
    value ^= value >> 13U;
    value ^= (value << 7U) & PHASE1_DOMAIN_MASK;
    value ^= value >> 17U;
    return value & PHASE1_DOMAIN_MASK;
}

static uint64_t independent_seed(size_t segment_length)
{
    return PHASE1_BASE_SEED ^ PHASE1_AFFINE_B ^
           (PHASE1_SEED_MIX * (uint64_t)(segment_length + 1U));
}

static int initialize_variant(kssd_array_t *context,
                              table_variant_t variant,
                              initialization_measurement_t *measurement)
{
    kssd_array_status_t status;
    uint64_t master_start;
    uint64_t master_end;
    uint64_t short_start;
    uint64_t short_end;
    size_t segment_length;

    memset(context, 0, sizeof(*context));
    memset(measurement, 0, sizeof(*measurement));
    status = kssd_array_layout((size_t)K,
                               KSSD_ARRAY_SEGMENT_CAP,
                               &context->layout);
    if (status != KSSD_ARRAY_OK) {
        return 0;
    }
    context->seed = PHASE1_BASE_SEED;
    context->rng = KSSD_ARRAY_RNG_SPLITMIX64;
    master_start = monotonic_nanoseconds();
    status = kssd_array_build_master(&context->master_permutation,
                                     &context->master_size,
                                     context->layout.master_length,
                                     PHASE1_BASE_SEED,
                                     KSSD_ARRAY_RNG_SPLITMIX64);
    master_end = monotonic_nanoseconds();
    if (status != KSSD_ARRAY_OK) {
        return 0;
    }
    context->permutations[context->layout.master_length] =
        context->master_permutation;
    context->permutation_sizes[context->layout.master_length] =
        context->master_size;
    measurement->persistent_bytes =
        context->master_size * sizeof(*context->master_permutation);

    short_start = monotonic_nanoseconds();
    for (segment_length = 1U;
         segment_length < context->layout.master_length;
         ++segment_length) {
        uint16_t *table = NULL;
        size_t size = 0U;
        size_t index;

        if (variant == TABLE_RANK_DERIVED) {
            status = kssd_array_derive_permutation(
                context->master_permutation,
                context->layout.master_length,
                segment_length,
                &table,
                &size);
        } else if (variant == TABLE_INDEPENDENT_SHUFFLE) {
            status = kssd_array_build_master(
                &table,
                &size,
                segment_length,
                independent_seed(segment_length),
                KSSD_ARRAY_RNG_SPLITMIX64);
        } else {
            status = kssd_array_pow4(segment_length, &size);
            if (status == KSSD_ARRAY_OK) {
                table = (uint16_t *)malloc(size * sizeof(*table));
                if (table == NULL) {
                    status = KSSD_ARRAY_OUT_OF_MEMORY;
                }
            }
            if (status == KSSD_ARRAY_OK) {
                for (index = 0U; index < size; ++index) {
                    if (variant == TABLE_IDENTITY_SHORT) {
                        table[index] = (uint16_t)index;
                    } else {
                        table[index] = (uint16_t)(
                            (PHASE1_ODD_A * (uint64_t)index +
                             PHASE1_AFFINE_B) & (uint64_t)(size - 1U));
                    }
                }
            }
        }
        if (status != KSSD_ARRAY_OK) {
            free(table);
            kssd_array_destroy(context);
            return 0;
        }
        context->permutations[segment_length] = table;
        context->permutation_sizes[segment_length] = size;
        measurement->persistent_bytes += size * sizeof(*table);
    }
    short_end = monotonic_nanoseconds();
    context->initialized = 1;
    measurement->master_ns = master_end - master_start;
    measurement->short_ns = short_end - short_start;
    return 1;
}

static int initialize_method_state(method_state_t *state,
                                   initialization_measurement_t measurements[
                                       TABLE_VARIANT_COUNT])
{
    size_t variant;
    memset(state, 0, sizeof(*state));
    for (variant = 0U; variant < TABLE_VARIANT_COUNT; ++variant) {
        if (!initialize_variant(&state->contexts[variant],
                                (table_variant_t)variant,
                                &measurements[variant])) {
            size_t prior;
            for (prior = 0U; prior < variant; ++prior) {
                kssd_array_destroy(&state->contexts[prior]);
            }
            return 0;
        }
    }
    wy_make_secret(PHASE1_BASE_SEED, state->wy_secret);
    return 1;
}

static void destroy_method_state(method_state_t *state)
{
    size_t variant;
    for (variant = 0U; variant < TABLE_VARIANT_COUNT; ++variant) {
        kssd_array_destroy(&state->contexts[variant]);
    }
    memset(state, 0, sizeof(*state));
}

static inline uint64_t score_one(method_id_t method,
                                 uint64_t key,
                                 const method_state_t *state)
{
    switch (method) {
    case METHOD_RANK_DERIVED:
        return kssd_array_fast_with_tables(
            key, &state->contexts[TABLE_RANK_DERIVED]);
    case METHOD_XXH3_PINNED_INLINE:
        return XXH3_64bits_withSeed(&key, sizeof(key), UINT64_C(0));
    case METHOD_XXH64_PINNED_INLINE:
        return XXH64(&key, sizeof(key), UINT64_C(0));
    case METHOD_MURMURHASH3:
        return murmurhash3_8bytes(key);
    case METHOD_WYHASH:
        return wyhash_8bytes(key, state->wy_secret);
    case METHOD_IDENTITY:
        return key & PHASE1_DOMAIN_MASK;
    case METHOD_BIT_REVERSE:
        return bit_reverse_low(key);
    case METHOD_ODD_MULTIPLY:
        return (PHASE1_ODD_A * key) & PHASE1_DOMAIN_MASK;
    case METHOD_AFFINE:
        return (PHASE1_ODD_A * key + PHASE1_AFFINE_B) &
               PHASE1_DOMAIN_MASK;
    case METHOD_XORSHIFT_BIJECTIVE:
        return xorshift_bijective(key);
    case METHOD_INDEPENDENT_SHUFFLE:
        return kssd_array_fast_with_tables(
            key, &state->contexts[TABLE_INDEPENDENT_SHUFFLE]);
    case METHOD_IDENTITY_SHORT:
        return kssd_array_fast_with_tables(
            key, &state->contexts[TABLE_IDENTITY_SHORT]);
    case METHOD_AFFINE_SHORT:
        return kssd_array_fast_with_tables(
            key, &state->contexts[TABLE_AFFINE_SHORT]);
    case METHOD_XXH3_ACCEPTED_SHARED:
        return phase1_accepted_xxh3_shared_direct(
            &key, sizeof(key), UINT64_C(0));
    case METHOD_XXH64_ACCEPTED_SHARED:
        return phase1_accepted_xxh64_shared_direct(
            &key, sizeof(key), UINT64_C(0));
    default:
        return UINT64_C(0);
    }
}

static const char *method_group(method_id_t method)
{
    if (method == METHOD_XXH3_ACCEPTED_SHARED ||
        method == METHOD_XXH64_ACCEPTED_SHARED) {
        return "historical_anchor";
    }
    if (method == METHOD_INDEPENDENT_SHUFFLE ||
        method == METHOD_IDENTITY_SHORT ||
        method == METHOD_AFFINE_SHORT) {
        return "rank_ablation";
    }
    if (method >= METHOD_IDENTITY &&
        method <= METHOD_XORSHIFT_BIJECTIVE) {
        return "specialized_bijection";
    }
    return "primary_general";
}

/* Direct-expression loops keep primary methods in the same translation unit. */
#define PHASE1_TIMED_SCORE_LOOP(SCORE_EXPRESSION, STORE_OUTPUT)                \
    do {                                                                       \
        size_t phase1_i;                                                       \
        uint64_t phase1_checksum = UINT64_C(0);                                \
        uint64_t phase1_wall_start;                                            \
        uint64_t phase1_wall_end;                                              \
        uint64_t phase1_cpu_start;                                             \
        uint64_t phase1_cpu_end;                                               \
        uint64_t phase1_tsc_start;                                             \
        uint64_t phase1_tsc_end;                                               \
        perf_group_t phase1_perf = perf_group_open();                          \
        __asm__ volatile("" ::: "memory");                                   \
        perf_group_start(&phase1_perf);                                        \
        phase1_cpu_start = process_cpu_nanoseconds();                          \
        phase1_wall_start = monotonic_nanoseconds();                           \
        phase1_tsc_start = read_tsc_begin();                                   \
        for (phase1_i = 0U; phase1_i < count; ++phase1_i) {                    \
            const uint64_t phase1_key = values[phase1_i];                      \
            const uint64_t phase1_score = (SCORE_EXPRESSION);                  \
            if ((STORE_OUTPUT) != NULL) {                                      \
                (STORE_OUTPUT)[phase1_i] = phase1_score;                       \
            }                                                                  \
            phase1_checksum += phase1_score ^ (uint64_t)phase1_i;              \
        }                                                                      \
        phase1_tsc_end = read_tsc_end();                                       \
        phase1_wall_end = monotonic_nanoseconds();                             \
        phase1_cpu_end = process_cpu_nanoseconds();                            \
        perf_group_stop(&phase1_perf,                                          \
                        &result.perf_cycles,                                   \
                        &result.perf_instructions);                            \
        __asm__ volatile("" ::: "memory");                                   \
        result.wall_seconds =                                                  \
            (double)(phase1_wall_end - phase1_wall_start) / 1.0e9;            \
        result.cpu_seconds =                                                   \
            (double)(phase1_cpu_end - phase1_cpu_start) / 1.0e9;              \
        result.tsc_cycles = phase1_tsc_end - phase1_tsc_start;                 \
        result.perf_available = phase1_perf.error_number == 0 &&               \
                                phase1_perf.leader_fd == -1 &&                 \
                                result.perf_cycles != UINT64_C(0);             \
        result.perf_errno = phase1_perf.error_number;                          \
        result.checksum = phase1_checksum;                                     \
        result.count = count;                                                  \
        phase1_sink ^= phase1_checksum;                                        \
        return result;                                                         \
    } while (0)

static timing_result_t run_score_loop(method_id_t method,
                                      const uint64_t *values,
                                      uint64_t *output,
                                      size_t count,
                                      const method_state_t *state)
{
    timing_result_t result;
    memset(&result, 0, sizeof(result));
    switch (method) {
    case METHOD_RANK_DERIVED:
        PHASE1_TIMED_SCORE_LOOP(
            kssd_array_fast_with_tables(
                phase1_key, &state->contexts[TABLE_RANK_DERIVED]), output);
    case METHOD_XXH3_PINNED_INLINE:
        PHASE1_TIMED_SCORE_LOOP(
            XXH3_64bits_withSeed(&phase1_key,
                                 sizeof(phase1_key), UINT64_C(0)), output);
    case METHOD_XXH64_PINNED_INLINE:
        PHASE1_TIMED_SCORE_LOOP(
            XXH64(&phase1_key, sizeof(phase1_key), UINT64_C(0)), output);
    case METHOD_MURMURHASH3:
        PHASE1_TIMED_SCORE_LOOP(murmurhash3_8bytes(phase1_key), output);
    case METHOD_WYHASH:
        PHASE1_TIMED_SCORE_LOOP(
            wyhash_8bytes(phase1_key, state->wy_secret), output);
    case METHOD_IDENTITY:
        PHASE1_TIMED_SCORE_LOOP(phase1_key & PHASE1_DOMAIN_MASK, output);
    case METHOD_BIT_REVERSE:
        PHASE1_TIMED_SCORE_LOOP(bit_reverse_low(phase1_key), output);
    case METHOD_ODD_MULTIPLY:
        PHASE1_TIMED_SCORE_LOOP(
            (PHASE1_ODD_A * phase1_key) & PHASE1_DOMAIN_MASK, output);
    case METHOD_AFFINE:
        PHASE1_TIMED_SCORE_LOOP(
            (PHASE1_ODD_A * phase1_key + PHASE1_AFFINE_B) &
                PHASE1_DOMAIN_MASK,
            output);
    case METHOD_XORSHIFT_BIJECTIVE:
        PHASE1_TIMED_SCORE_LOOP(xorshift_bijective(phase1_key), output);
    case METHOD_INDEPENDENT_SHUFFLE:
        PHASE1_TIMED_SCORE_LOOP(
            kssd_array_fast_with_tables(
                phase1_key,
                &state->contexts[TABLE_INDEPENDENT_SHUFFLE]), output);
    case METHOD_IDENTITY_SHORT:
        PHASE1_TIMED_SCORE_LOOP(
            kssd_array_fast_with_tables(
                phase1_key, &state->contexts[TABLE_IDENTITY_SHORT]), output);
    case METHOD_AFFINE_SHORT:
        PHASE1_TIMED_SCORE_LOOP(
            kssd_array_fast_with_tables(
                phase1_key, &state->contexts[TABLE_AFFINE_SHORT]), output);
    case METHOD_XXH3_ACCEPTED_SHARED:
        PHASE1_TIMED_SCORE_LOOP(
            phase1_accepted_xxh3_shared_direct(
                &phase1_key, sizeof(phase1_key), UINT64_C(0)), output);
    case METHOD_XXH64_ACCEPTED_SHARED:
        PHASE1_TIMED_SCORE_LOOP(
            phase1_accepted_xxh64_shared_direct(
                &phase1_key, sizeof(phase1_key), UINT64_C(0)), output);
    default:
        fputs("invalid method\n", stderr);
        exit(EXIT_FAILURE);
    }
}

#undef PHASE1_TIMED_SCORE_LOOP

static window_result_t monotonic_deque_select(const uint64_t *scores,
                                              size_t score_count,
                                              size_t width,
                                              size_t *deque,
                                              timing_result_t *timing)
{
    window_result_t result;
    size_t front = 0U;
    size_t back = 0U;
    size_t index;
    uint64_t wall_start;
    uint64_t wall_end;
    uint64_t cpu_start;
    uint64_t cpu_end;
    uint64_t tsc_start;
    uint64_t tsc_end;
    perf_group_t perf;

    memset(&result, 0, sizeof(result));
    memset(timing, 0, sizeof(*timing));
    if (width == 0U || width > score_count) {
        return result;
    }
    result.window_count = score_count - width + 1U;
    perf = perf_group_open();
    __asm__ volatile("" ::: "memory");
    perf_group_start(&perf);
    cpu_start = process_cpu_nanoseconds();
    wall_start = monotonic_nanoseconds();
    tsc_start = read_tsc_begin();
    for (index = 0U; index < score_count; ++index) {
        while (front < back && deque[front] + width <= index) {
            ++front;
        }
        while (front < back &&
               scores[deque[back - 1U]] > scores[index]) {
            --back;
        }
        deque[back++] = index;
        if (index + 1U >= width) {
            const size_t window_start = index + 1U - width;
            const size_t position = deque[front];
            result.position_checksum = selected_position_update(
                result.position_checksum, position, window_start);
            result.score_checksum = checksum_update(
                result.score_checksum, scores[position], window_start);
            ++result.selected_count;
        }
    }
    tsc_end = read_tsc_end();
    wall_end = monotonic_nanoseconds();
    cpu_end = process_cpu_nanoseconds();
    perf_group_stop(&perf, &timing->perf_cycles,
                    &timing->perf_instructions);
    __asm__ volatile("" ::: "memory");
    timing->wall_seconds = (double)(wall_end - wall_start) / 1.0e9;
    timing->cpu_seconds = (double)(cpu_end - cpu_start) / 1.0e9;
    timing->tsc_cycles = tsc_end - tsc_start;
    timing->perf_available = perf.error_number == 0 &&
                             timing->perf_cycles != UINT64_C(0);
    timing->perf_errno = perf.error_number;
    timing->checksum = result.position_checksum ^ result.score_checksum;
    timing->count = result.window_count;
    phase1_sink ^= timing->checksum;
    return result;
}

static void shuffle_methods(method_id_t *methods,
                            size_t count,
                            uint64_t seed)
{
    size_t index;
    for (index = count; index > 1U; --index) {
        const size_t selected =
            (size_t)(splitmix64_next_local(&seed) % (uint64_t)index);
        const method_id_t temporary = methods[index - 1U];
        methods[index - 1U] = methods[selected];
        methods[selected] = temporary;
    }
}

static void print_meta(const char *dataset,
                       const encoded_input_t *input,
                       const method_state_t *state)
{
    printf("META\t%s\t%d\t%zu\t%zu\t%zu\t%" PRIu64
           "\t%u\t%u\t%" PRIu64 "\t%" PRIu64 "\t%" PRIu64
           "\t%" PRIu64 "\n",
           dataset, K, input->valid_bases, input->ambiguous_bases,
           input->count, input->checksum,
           XXH_VERSION_NUMBER, phase1_accepted_xxhash_version_direct(),
           state->wy_secret[0], state->wy_secret[1],
           state->wy_secret[2], state->wy_secret[3]);
}

static void print_timing_fields(const timing_result_t *timing)
{
    const double ns_per_item = timing->count == 0U
        ? NAN
        : timing->wall_seconds * 1.0e9 / (double)timing->count;
    const double million_per_second = timing->wall_seconds <= 0.0
        ? NAN
        : (double)timing->count / timing->wall_seconds / 1.0e6;
    const double tsc_per_item = timing->count == 0U
        ? NAN
        : (double)timing->tsc_cycles / (double)timing->count;

    printf("%.9f\t%.9f\t%.9f\t%.9f\t%" PRIu64 "\t%.9f\t%d\t%d"
           "\t%" PRIu64 "\t%" PRIu64,
           timing->wall_seconds,
           timing->cpu_seconds,
           ns_per_item,
           million_per_second,
           timing->tsc_cycles,
           tsc_per_item,
           timing->perf_available,
           timing->perf_errno,
           timing->perf_cycles,
           timing->perf_instructions);
}

static void initialize_method_list(method_id_t *methods, size_t count)
{
    size_t index;
    for (index = 0U; index < count; ++index) {
        methods[index] = (method_id_t)index;
    }
}

static int run_mapping_mode(const char *dataset,
                            const encoded_input_t *input,
                            const method_state_t *state,
                            unsigned repeats,
                            int perform_warmup)
{
    method_id_t methods[METHOD_COUNT];
    uint64_t expected_checksum[METHOD_COUNT];
    unsigned repeat;
    size_t method_index;

    memset(expected_checksum, 0, sizeof(expected_checksum));
    initialize_method_list(methods, METHOD_COUNT);
    if (perform_warmup != 0) {
        method_id_t warmup_order[METHOD_COUNT];
        memcpy(warmup_order, methods, sizeof(warmup_order));
        shuffle_methods(warmup_order, METHOD_COUNT,
                        UINT64_C(0x4d415050494e4757));
        for (method_index = 0U; method_index < METHOD_COUNT;
             ++method_index) {
            (void)run_score_loop(warmup_order[method_index],
                                 input->values, NULL, input->count, state);
        }
    }
    for (repeat = 1U; repeat <= repeats; ++repeat) {
        method_id_t order[METHOD_COUNT];
        memcpy(order, methods, sizeof(order));
        shuffle_methods(order, METHOD_COUNT,
                        PHASE1_BASE_SEED ^
                        (UINT64_C(0x4d415050494e4700) + repeat));
        for (method_index = 0U; method_index < METHOD_COUNT;
             ++method_index) {
            const method_id_t method = order[method_index];
            const timing_result_t timing = run_score_loop(
                method, input->values, NULL, input->count, state);
            if (repeat == 1U) {
                expected_checksum[method] = timing.checksum;
            } else if (expected_checksum[method] != timing.checksum) {
                fprintf(stderr,
                        "mapping checksum changed for %s repeat %u\n",
                        method_names[method], repeat);
                return 0;
            }
            printf("MAPPING\t%s\t%d\t%u\t%zu\t%s\t%s\t%zu\t",
                   dataset, K, repeat, method_index + 1U,
                   method_names[method], method_group(method), input->count);
            print_timing_fields(&timing);
            printf("\t%" PRIu64 "\t%" PRIu64 "\t%zu\n",
                   timing.checksum, input->checksum, timing.count);
            fflush(stdout);
        }
    }
    return 1;
}

static int run_neutral_mode(const char *dataset,
                            const encoded_input_t *input,
                            const method_state_t *state,
                            const size_t *widths,
                            size_t width_count,
                            unsigned repeats,
                            int perform_warmup)
{
    const size_t neutral_method_count =
        (size_t)METHOD_AFFINE_SHORT + 1U;
    method_id_t methods[METHOD_COUNT];
    uint64_t expected_score_checksum[METHOD_COUNT];
    uint64_t expected_position_checksum[METHOD_COUNT][PHASE1_MAX_W_VALUES];
    uint64_t *scores;
    size_t *deque;
    unsigned repeat;
    size_t method_index;

    if (width_count == 0U || width_count > PHASE1_MAX_W_VALUES) {
        fputs("invalid neutral width count\n", stderr);
        return 0;
    }
    scores = (uint64_t *)malloc(input->count * sizeof(*scores));
    deque = (size_t *)malloc(input->count * sizeof(*deque));
    if (scores == NULL || deque == NULL) {
        fputs("cannot allocate neutral score/deque arrays\n", stderr);
        free(scores);
        free(deque);
        return 0;
    }
    memset(expected_score_checksum, 0, sizeof(expected_score_checksum));
    memset(expected_position_checksum, 0,
           sizeof(expected_position_checksum));
    initialize_method_list(methods, neutral_method_count);

    if (perform_warmup != 0) {
        method_id_t warmup_order[METHOD_COUNT];
        memcpy(warmup_order, methods,
               neutral_method_count * sizeof(*warmup_order));
        shuffle_methods(warmup_order, neutral_method_count,
                        UINT64_C(0x4e45555452414c57));
        for (method_index = 0U; method_index < neutral_method_count;
             ++method_index) {
            size_t width_index;
            timing_result_t ignored;
            (void)run_score_loop(warmup_order[method_index],
                                 input->values, scores, input->count, state);
            for (width_index = 0U; width_index < width_count;
                 ++width_index) {
                (void)monotonic_deque_select(scores, input->count,
                                             widths[width_index], deque,
                                             &ignored);
            }
        }
    }

    for (repeat = 1U; repeat <= repeats; ++repeat) {
        method_id_t order[METHOD_COUNT];
        memcpy(order, methods, neutral_method_count * sizeof(*order));
        shuffle_methods(order, neutral_method_count,
                        PHASE1_BASE_SEED ^
                        (UINT64_C(0x4e45555452414c00) + repeat));
        for (method_index = 0U; method_index < neutral_method_count;
             ++method_index) {
            const method_id_t method = order[method_index];
            const timing_result_t score_timing = run_score_loop(
                method, input->values, scores, input->count, state);
            size_t width_index;
            if (repeat == 1U) {
                expected_score_checksum[method] = score_timing.checksum;
            } else if (expected_score_checksum[method] !=
                       score_timing.checksum) {
                fprintf(stderr,
                        "neutral score checksum changed for %s repeat %u\n",
                        method_names[method], repeat);
                free(scores);
                free(deque);
                return 0;
            }
            for (width_index = 0U; width_index < width_count;
                 ++width_index) {
                timing_result_t window_timing;
                const size_t width = widths[width_index];
                const window_result_t window = monotonic_deque_select(
                    scores, input->count, width, deque, &window_timing);
                const double total_seconds = score_timing.wall_seconds +
                                             window_timing.wall_seconds;
                const double total_mwindows = total_seconds <= 0.0
                    ? NAN
                    : (double)window.window_count / total_seconds / 1.0e6;
                if (window.selected_count != window.window_count) {
                    fputs("neutral selected/window count mismatch\n", stderr);
                    free(scores);
                    free(deque);
                    return 0;
                }
                if (repeat == 1U) {
                    expected_position_checksum[method][width_index] =
                        window.position_checksum;
                } else if (expected_position_checksum[method][width_index] !=
                           window.position_checksum) {
                    fprintf(stderr,
                            "neutral position checksum changed for %s W=%zu "
                            "repeat %u\n",
                            method_names[method], width, repeat);
                    free(scores);
                    free(deque);
                    return 0;
                }
                printf("NEUTRAL\t%s\t%d\t%zu\t%u\t%zu\t%s\t%s\t"
                       "%zu\t%zu\t",
                       dataset, K, width, repeat, method_index + 1U,
                       method_names[method], method_group(method),
                       input->count, window.window_count);
                print_timing_fields(&score_timing);
                printf("\t");
                print_timing_fields(&window_timing);
                printf("\t%.9f\t%.9f\t%zu\t%" PRIu64 "\t%" PRIu64
                       "\t%" PRIu64 "\t%zu\t0\n",
                       total_seconds, total_mwindows,
                       window.selected_count,
                       window.position_checksum,
                       window.score_checksum,
                       score_timing.checksum,
                       score_timing.count);
                fflush(stdout);
            }
        }
    }
    free(scores);
    free(deque);
    return 1;
}

static int run_initialization_mode(void)
{
    size_t variant;
    for (variant = 0U; variant < TABLE_VARIANT_COUNT; ++variant) {
        kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
        initialization_measurement_t measurement;
        size_t segment_index;
        int informative = 0;
        if (!initialize_variant(&context, (table_variant_t)variant,
                                &measurement)) {
            return 0;
        }
        for (segment_index = 0U;
             segment_index < context.layout.segment_count;
             ++segment_index) {
            if (context.layout.segment_lengths[segment_index] <
                context.layout.master_length) {
                informative = 1;
            }
        }
        printf("INITIALIZATION\t%d\t%s\t%zu\t%" PRIu64 "\t%" PRIu64
               "\t%" PRIu64 "\t%zu\t%d\t",
               K, table_variant_names[variant],
               context.layout.master_length,
               measurement.master_ns,
               measurement.short_ns,
               measurement.master_ns + measurement.short_ns,
               measurement.persistent_bytes,
               informative);
        for (segment_index = 0U;
             segment_index < context.layout.segment_count;
             ++segment_index) {
            printf("%s%zu", segment_index == 0U ? "" : ",",
                   context.layout.segment_lengths[segment_index]);
        }
        putchar('\n');
        kssd_array_destroy(&context);
    }
    return 1;
}

static int validate_bijection_method(method_id_t method,
                                     const method_state_t *state,
                                     const char *category)
{
    const size_t domain_size = (size_t)1U << (2U * (unsigned)K);
    uint8_t *seen;
    size_t input;
    size_t duplicates = 0U;
    size_t out_of_range = 0U;

    if (K != 9) {
        fputs("bijection validation must be compiled with K=9\n", stderr);
        return 0;
    }
    seen = (uint8_t *)calloc(domain_size, sizeof(*seen));
    if (seen == NULL) {
        return 0;
    }
    for (input = 0U; input < domain_size; ++input) {
        const uint64_t output = score_one(method, (uint64_t)input, state);
        if (output >= (uint64_t)domain_size) {
            ++out_of_range;
        } else if (seen[(size_t)output] != 0U) {
            ++duplicates;
        } else {
            seen[(size_t)output] = UINT8_C(1);
        }
    }
    printf("BIJECTION\t%s\t%s\t%d\t%zu\t%zu\t%zu\t%s\n",
           category, method_names[method], K, domain_size,
           duplicates, out_of_range,
           duplicates == 0U && out_of_range == 0U ? "PASS" : "FAIL");
    free(seen);
    return duplicates == 0U && out_of_range == 0U;
}

static int run_bijection_validation(const method_state_t *state)
{
    static const method_id_t specialized[] = {
        METHOD_IDENTITY,
        METHOD_BIT_REVERSE,
        METHOD_ODD_MULTIPLY,
        METHOD_AFFINE,
        METHOD_XORSHIFT_BIJECTIVE
    };
    static const method_id_t ablations[] = {
        METHOD_RANK_DERIVED,
        METHOD_INDEPENDENT_SHUFFLE,
        METHOD_IDENTITY_SHORT,
        METHOD_AFFINE_SHORT
    };
    size_t index;
    int pass = 1;
    for (index = 0U; index < sizeof(specialized) / sizeof(specialized[0]);
         ++index) {
        pass &= validate_bijection_method(specialized[index], state,
                                          "specialized");
    }
    for (index = 0U; index < sizeof(ablations) / sizeof(ablations[0]);
         ++index) {
        pass &= validate_bijection_method(ablations[index], state,
                                          "rank_ablation");
    }
    return pass;
}

static void brute_force_trace(const uint64_t *scores,
                              size_t count,
                              size_t width,
                              uint64_t *minimum_scores,
                              size_t *minimum_positions)
{
    size_t start;
    for (start = 0U; start + width <= count; ++start) {
        uint64_t minimum = UINT64_MAX;
        size_t position = start;
        size_t offset;
        for (offset = 0U; offset < width; ++offset) {
            const size_t candidate = start + offset;
            if (scores[candidate] < minimum) {
                minimum = scores[candidate];
                position = candidate;
            }
        }
        minimum_scores[start] = minimum;
        minimum_positions[start] = position;
    }
}

static void deque_trace(const uint64_t *scores,
                        size_t count,
                        size_t width,
                        size_t *deque,
                        uint64_t *minimum_scores,
                        size_t *minimum_positions)
{
    size_t front = 0U;
    size_t back = 0U;
    size_t index;
    for (index = 0U; index < count; ++index) {
        while (front < back && deque[front] + width <= index) {
            ++front;
        }
        while (front < back && scores[deque[back - 1U]] > scores[index]) {
            --back;
        }
        deque[back++] = index;
        if (index + 1U >= width) {
            const size_t start = index + 1U - width;
            minimum_positions[start] = deque[front];
            minimum_scores[start] = scores[deque[front]];
        }
    }
}

static int validate_one_score_fixture(const char *name,
                                      const char *method,
                                      const uint64_t *scores,
                                      size_t count,
                                      size_t width)
{
    const size_t windows = count - width + 1U;
    uint64_t *brute_scores = (uint64_t *)malloc(windows * sizeof(uint64_t));
    uint64_t *deque_scores = (uint64_t *)malloc(windows * sizeof(uint64_t));
    size_t *brute_positions = (size_t *)malloc(windows * sizeof(size_t));
    size_t *deque_positions = (size_t *)malloc(windows * sizeof(size_t));
    size_t *deque = (size_t *)malloc(count * sizeof(size_t));
    size_t index;
    uint64_t brute_checksum = UINT64_C(0);
    uint64_t deque_checksum = UINT64_C(0);
    int pass = 1;

    if (brute_scores == NULL || deque_scores == NULL ||
        brute_positions == NULL || deque_positions == NULL ||
        deque == NULL) {
        free(brute_scores); free(deque_scores);
        free(brute_positions); free(deque_positions); free(deque);
        return 0;
    }
    brute_force_trace(scores, count, width, brute_scores, brute_positions);
    deque_trace(scores, count, width, deque, deque_scores, deque_positions);
    for (index = 0U; index < windows; ++index) {
        brute_checksum = selected_position_update(
            brute_checksum, brute_positions[index], index);
        deque_checksum = selected_position_update(
            deque_checksum, deque_positions[index], index);
        if (brute_scores[index] != deque_scores[index] ||
            brute_positions[index] != deque_positions[index]) {
            pass = 0;
            break;
        }
    }
    if (brute_checksum != deque_checksum) {
        pass = 0;
    }
    printf("DEQUE_TEST\t%d\t%s\t%s\t%zu\t%zu\t%" PRIu64
           "\t%" PRIu64 "\t%s\n",
           K, name, method, count, width,
           brute_checksum, deque_checksum, pass ? "PASS" : "FAIL");
    free(brute_scores); free(deque_scores);
    free(brute_positions); free(deque_positions); free(deque);
    return pass;
}

static int run_deque_validation(const method_state_t *state)
{
    enum { FIXTURE_COUNT = 257 };
    uint64_t keys[FIXTURE_COUNT];
    uint64_t scores[FIXTURE_COUNT];
    static const size_t widths[] = {1U, 2U, 7U, 64U, FIXTURE_COUNT};
    size_t index;
    uint64_t rng = UINT64_C(0x123456789abcdef0);
    int pass = 1;

    for (index = 0U; index < FIXTURE_COUNT; ++index) {
        keys[index] = splitmix64_next_local(&rng) & PHASE1_DOMAIN_MASK;
    }
    keys[0] = UINT64_C(0);
    keys[1] = PHASE1_DOMAIN_MASK;
    keys[2] = UINT64_C(0x3333333333333333) & PHASE1_DOMAIN_MASK;
    keys[3] = UINT64_C(0xcccccccccccccccc) & PHASE1_DOMAIN_MASK;
    for (index = 0U; index <= (size_t)METHOD_AFFINE_SHORT; ++index) {
        size_t score_index;
        size_t width_index;
        for (score_index = 0U; score_index < FIXTURE_COUNT; ++score_index) {
            scores[score_index] = score_one((method_id_t)index,
                                            keys[score_index], state);
        }
        for (width_index = 0U;
             width_index < sizeof(widths) / sizeof(widths[0]);
             ++width_index) {
            pass &= validate_one_score_fixture(
                "method_generated", method_names[index], scores,
                FIXTURE_COUNT, widths[width_index]);
        }
    }
    for (index = 0U; index < FIXTURE_COUNT; ++index) {
        scores[index] = (uint64_t)index;
    }
    pass &= validate_one_score_fixture("increasing", "synthetic_scores",
                                       scores, FIXTURE_COUNT, 23U);
    for (index = 0U; index < FIXTURE_COUNT; ++index) {
        scores[index] = (uint64_t)(FIXTURE_COUNT - index);
    }
    pass &= validate_one_score_fixture("decreasing", "synthetic_scores",
                                       scores, FIXTURE_COUNT, 23U);
    for (index = 0U; index < FIXTURE_COUNT; ++index) {
        scores[index] = (uint64_t)(index % 5U);
    }
    pass &= validate_one_score_fixture("repeated_ties", "synthetic_scores",
                                       scores, FIXTURE_COUNT, 23U);
    for (index = 0U; index < FIXTURE_COUNT; ++index) {
        scores[index] = UINT64_C(7);
    }
    pass &= validate_one_score_fixture("all_ties", "synthetic_scores",
                                       scores, FIXTURE_COUNT, 23U);
    if ((K % 2) == 0) {
        enum { PALINDROME_COUNT = 64 };
        uint64_t palindrome_keys[PALINDROME_COUNT];
        size_t palindrome_index;
        for (palindrome_index = 0U;
             palindrome_index < PALINDROME_COUNT;
             ++palindrome_index) {
            uint8_t bases[32];
            size_t base_index;
            uint64_t key = UINT64_C(0);
            for (base_index = 0U; base_index < (size_t)K / 2U;
                 ++base_index) {
                bases[base_index] = (uint8_t)(
                    (palindrome_index + 3U * base_index) & 3U);
                bases[(size_t)K - 1U - base_index] =
                    (uint8_t)(3U - bases[base_index]);
            }
            for (base_index = 0U; base_index < (size_t)K; ++base_index) {
                key = (key << 2U) | (uint64_t)bases[base_index];
            }
            palindrome_keys[palindrome_index] = key;
        }
        for (index = 0U; index <= (size_t)METHOD_AFFINE_SHORT; ++index) {
            size_t score_index;
            for (score_index = 0U; score_index < PALINDROME_COUNT;
                 ++score_index) {
                scores[score_index] = score_one(
                    (method_id_t)index, palindrome_keys[score_index], state);
            }
            pass &= validate_one_score_fixture(
                "reverse_complement_palindromes", method_names[index],
                scores, PALINDROME_COUNT, 7U);
        }
    }
    return pass;
}

static void rescan_record_selection(rescan_result_t *result,
                                    size_t position,
                                    size_t window_start,
                                    size_t *last_position,
                                    int *have_last,
                                    uint8_t *selected_seen)
{
    ++result->selected_positions;
    if ((selected_seen[position >> 3U] &
         (uint8_t)(UINT8_C(1) << (position & 7U))) == 0U) {
        selected_seen[position >> 3U] |=
            (uint8_t)(UINT8_C(1) << (position & 7U));
        ++result->unique_positions;
    }
    if (*have_last != 0 && position == *last_position) {
        ++result->adjacent_repeated_positions;
    }
    *last_position = position;
    *have_last = 1;
    result->position_checksum = selected_position_update(
        result->position_checksum, position, window_start);
}

static int accepted_rescan_diagnostic(method_id_t method,
                                      const uint64_t *scores,
                                      size_t kmer_count,
                                      size_t width,
                                      size_t requested_workers,
                                      rescan_result_t *result)
{
    const size_t window_count = kmer_count - width + 1U;
    size_t worker;
    size_t last_position = 0U;
    int have_last = 0;
    uint8_t *selected_seen;

    memset(result, 0, sizeof(*result));
    if (width == 0U || width > kmer_count || requested_workers == 0U) {
        return 0;
    }
    selected_seen = (uint8_t *)calloc((kmer_count + 7U) / 8U,
                                      sizeof(*selected_seen));
    if (selected_seen == NULL) {
        return 0;
    }
    for (worker = 0U; worker < requested_workers; ++worker) {
        const size_t range_start =
            (window_count * worker) / requested_workers;
        const size_t range_end =
            (window_count * (worker + 1U)) / requested_workers;
        uint64_t current_minimum = UINT64_MAX;
        size_t current_position = range_start;
        size_t offset;
        size_t window_start;

        if (range_start >= range_end) {
            continue;
        }
        for (offset = 0U; offset < width; ++offset) {
            const size_t position = range_start + offset;
            const uint64_t score = scores[position];
            ++result->mapping_calls;
            if (score < current_minimum) {
                current_minimum = score;
                current_position = position;
            }
        }
        rescan_record_selection(result, current_position, range_start,
                                &last_position, &have_last, selected_seen);
        for (window_start = range_start + 1U;
             window_start < range_end;
             ++window_start) {
            const size_t previous_position = window_start - 1U;
            const size_t new_position = window_start + width - 1U;
            if (previous_position == current_position) {
                ++result->full_rescans;
                current_minimum = UINT64_MAX;
                for (offset = 0U; offset < width; ++offset) {
                    const size_t position = window_start + offset;
                    const uint64_t score = scores[position];
                    ++result->mapping_calls;
                    if (score < current_minimum) {
                        current_minimum = score;
                        current_position = position;
                    }
                }
            } else {
                const uint64_t score = scores[new_position];
                ++result->entering_updates;
                ++result->mapping_calls;
                if (score < current_minimum) {
                    current_minimum = score;
                    current_position = new_position;
                }
            }
            rescan_record_selection(result, current_position, window_start,
                                    &last_position, &have_last, selected_seen);
        }
        result->final_checksum = current_minimum ^
                                 (uint64_t)current_position;
    }
    free(selected_seen);
    (void)method;
    return result->selected_positions == window_count;
}

static int run_rescan_mode(const char *dataset,
                           const encoded_input_t *input,
                           const method_state_t *state,
                           const size_t *widths,
                           size_t width_count,
                           const size_t *thread_counts,
                           size_t thread_count_count)
{
    static const method_id_t accepted_methods[] = {
        METHOD_RANK_DERIVED,
        METHOD_XXH3_ACCEPTED_SHARED,
        METHOD_XXH64_ACCEPTED_SHARED,
        METHOD_MURMURHASH3,
        METHOD_WYHASH
    };
    size_t width_index;
    size_t method_index;
    uint64_t *scores = (uint64_t *)malloc(input->count * sizeof(*scores));

    if (scores == NULL) {
        return 0;
    }
    for (method_index = 0U;
         method_index < sizeof(accepted_methods) /
                            sizeof(accepted_methods[0]);
         ++method_index) {
        const method_id_t method = accepted_methods[method_index];
        size_t position;
        for (position = 0U; position < input->count; ++position) {
            scores[position] = score_one(method, input->values[position], state);
        }
        for (width_index = 0U; width_index < width_count; ++width_index) {
            const size_t width = widths[width_index];
            rescan_result_t result;
            const size_t windows = input->count - width + 1U;
            if (!accepted_rescan_diagnostic(method,
                                            scores,
                                            input->count,
                                            width,
                                            1U,
                                            &result)) {
                free(scores);
                return 0;
            }
            printf("RESCAN\tFigure2\t%s\t%d\t%zu\t1\t%s\t%zu\t%zu"
                   "\t%zu\t%zu\t%zu\t%.12f\t%zu\t%zu\t%zu"
                   "\t%" PRIu64 "\t%" PRIu64 "\n",
                   dataset, K, width, method_names[method],
                   input->count, windows,
                   result.mapping_calls, result.full_rescans,
                   result.entering_updates,
                   (double)result.mapping_calls / (double)windows,
                   result.selected_positions, result.unique_positions,
                   result.adjacent_repeated_positions,
                   result.position_checksum, result.final_checksum);
            fflush(stdout);
        }
        if (K == 21) {
            size_t thread_index;
            for (thread_index = 0U; thread_index < thread_count_count;
                 ++thread_index) {
                const size_t workers = thread_counts[thread_index];
                for (width_index = 0U; width_index < width_count;
                     ++width_index) {
                    const size_t width = widths[width_index];
                    rescan_result_t result;
                    const size_t windows = input->count - width + 1U;
                    if (!accepted_rescan_diagnostic(method,
                                                    scores,
                                                    input->count,
                                                    width,
                                                    workers,
                                                    &result)) {
                        free(scores);
                        return 0;
                    }
                    printf("RESCAN\tFigure3\t%s\t%d\t%zu\t%zu\t%s\t"
                           "%zu\t%zu\t%zu\t%zu\t%zu\t%.12f\t%zu\t"
                           "%zu\t%zu\t%" PRIu64 "\t%" PRIu64 "\n",
                           dataset, K, width, workers,
                           method_names[method], input->count, windows,
                           result.mapping_calls, result.full_rescans,
                           result.entering_updates,
                           (double)result.mapping_calls / (double)windows,
                           result.selected_positions,
                           result.unique_positions,
                           result.adjacent_repeated_positions,
                           result.position_checksum,
                           result.final_checksum);
                    fflush(stdout);
                }
            }
        }
    }
    free(scores);
    return 1;
}

#define PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION(FUNCTION_NAME, SCORE_EXPRESSION) \
    static timing_result_t FUNCTION_NAME(                                      \
        const uint64_t *values, uint64_t *scores, size_t count,                \
        const method_state_t *state, int requested_threads,                    \
        int *observed_threads)                                                 \
    {                                                                          \
        timing_result_t result;                                                \
        uint64_t checksum = UINT64_C(0);                                       \
        uint64_t wall_start;                                                   \
        uint64_t wall_end;                                                     \
        uint64_t cpu_start;                                                    \
        uint64_t cpu_end;                                                      \
        uint64_t tsc_start;                                                    \
        uint64_t tsc_end;                                                      \
        memset(&result, 0, sizeof(result));                                    \
        (void)state;                                                           \
        *observed_threads = 0;                                                 \
        __asm__ volatile("" ::: "memory");                                   \
        cpu_start = process_cpu_nanoseconds();                                 \
        wall_start = monotonic_nanoseconds();                                  \
        tsc_start = read_tsc_begin();                                          \
        _Pragma("omp parallel num_threads(requested_threads) reduction(+:checksum)") \
        {                                                                      \
            size_t phase1_i;                                                   \
            _Pragma("omp single")                                             \
            { *observed_threads = omp_get_num_threads(); }                     \
            _Pragma("omp for schedule(static)")                               \
            for (phase1_i = 0U; phase1_i < count; ++phase1_i) {                \
                const uint64_t phase1_key = values[phase1_i];                  \
                const uint64_t phase1_score = (SCORE_EXPRESSION);              \
                scores[phase1_i] = phase1_score;                               \
                checksum += phase1_score ^ (uint64_t)phase1_i;                 \
            }                                                                  \
        }                                                                      \
        tsc_end = read_tsc_end();                                              \
        wall_end = monotonic_nanoseconds();                                    \
        cpu_end = process_cpu_nanoseconds();                                   \
        __asm__ volatile("" ::: "memory");                                   \
        result.wall_seconds = (double)(wall_end - wall_start) / 1.0e9;         \
        result.cpu_seconds = (double)(cpu_end - cpu_start) / 1.0e9;            \
        result.tsc_cycles = tsc_end - tsc_start;                               \
        result.checksum = checksum;                                            \
        result.count = count;                                                  \
        result.perf_available = 0;                                             \
        result.perf_errno = ENOTSUP;                                           \
        phase1_sink ^= checksum;                                               \
        return result;                                                         \
    }

PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION(
    parallel_score_rank,
    kssd_array_fast_with_tables(
        phase1_key, &state->contexts[TABLE_RANK_DERIVED]))
PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION(
    parallel_score_xxh3,
    XXH3_64bits_withSeed(&phase1_key, sizeof(phase1_key), UINT64_C(0)))
PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION(
    parallel_score_xxh64,
    XXH64(&phase1_key, sizeof(phase1_key), UINT64_C(0)))
PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION(
    parallel_score_murmur,
    murmurhash3_8bytes(phase1_key))
PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION(
    parallel_score_wyhash,
    wyhash_8bytes(phase1_key, state->wy_secret))
PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION(
    parallel_score_identity,
    phase1_key & PHASE1_DOMAIN_MASK)
PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION(
    parallel_score_odd_multiply,
    (PHASE1_ODD_A * phase1_key) & PHASE1_DOMAIN_MASK)

#undef PHASE1_DEFINE_PARALLEL_SCORE_FUNCTION

typedef timing_result_t (*parallel_score_function_t)(
    const uint64_t *, uint64_t *, size_t, const method_state_t *, int, int *);

static parallel_score_function_t parallel_score_function(method_id_t method)
{
    switch (method) {
    case METHOD_RANK_DERIVED: return parallel_score_rank;
    case METHOD_XXH3_PINNED_INLINE: return parallel_score_xxh3;
    case METHOD_XXH64_PINNED_INLINE: return parallel_score_xxh64;
    case METHOD_MURMURHASH3: return parallel_score_murmur;
    case METHOD_WYHASH: return parallel_score_wyhash;
    case METHOD_IDENTITY: return parallel_score_identity;
    case METHOD_ODD_MULTIPLY: return parallel_score_odd_multiply;
    default: return NULL;
    }
}

static window_result_t serial_window_result(const uint64_t *scores,
                                            size_t score_count,
                                            size_t width,
                                            size_t *deque)
{
    size_t front = 0U;
    size_t back = 0U;
    size_t index;
    window_result_t result;
    memset(&result, 0, sizeof(result));
    result.window_count = score_count - width + 1U;
    for (index = 0U; index < score_count; ++index) {
        while (front < back && deque[front] + width <= index) {
            ++front;
        }
        while (front < back && scores[deque[back - 1U]] > scores[index]) {
            --back;
        }
        deque[back++] = index;
        if (index + 1U >= width) {
            const size_t start = index + 1U - width;
            result.position_checksum = selected_position_update(
                result.position_checksum, deque[front], start);
            result.score_checksum = checksum_update(
                result.score_checksum, scores[deque[front]], start);
            ++result.selected_count;
        }
    }
    return result;
}

static window_result_t parallel_window_select(const uint64_t *scores,
                                              size_t score_count,
                                              size_t width,
                                              size_t *deque_storage,
                                              int requested_threads,
                                              int *observed_threads,
                                              timing_result_t *timing)
{
    const size_t window_count = score_count - width + 1U;
    uint64_t position_checksum = UINT64_C(0);
    uint64_t score_checksum = UINT64_C(0);
    size_t selected_count = 0U;
    uint64_t wall_start;
    uint64_t wall_end;
    uint64_t cpu_start;
    uint64_t cpu_end;
    uint64_t tsc_start;
    uint64_t tsc_end;
    window_result_t result;

    memset(&result, 0, sizeof(result));
    memset(timing, 0, sizeof(*timing));
    *observed_threads = 0;
    __asm__ volatile("" ::: "memory");
    cpu_start = process_cpu_nanoseconds();
    wall_start = monotonic_nanoseconds();
    tsc_start = read_tsc_begin();
#pragma omp parallel num_threads(requested_threads) \
    reduction(^:position_checksum,score_checksum) reduction(+:selected_count)
    {
        const size_t worker = (size_t)omp_get_thread_num();
        const size_t workers = (size_t)omp_get_num_threads();
        const size_t range_start = (window_count * worker) / workers;
        const size_t range_end = (window_count * (worker + 1U)) / workers;
        size_t *deque = deque_storage + range_start + worker * width;
        size_t front = 0U;
        size_t back = 0U;
        size_t index;
#pragma omp single
        { *observed_threads = omp_get_num_threads(); }
        if (range_start < range_end) {
            const size_t score_end = range_end + width - 1U;
            for (index = range_start; index < score_end; ++index) {
                while (front < back && deque[front] + width <= index) {
                    ++front;
                }
                while (front < back &&
                       scores[deque[back - 1U]] > scores[index]) {
                    --back;
                }
                deque[back++] = index;
                if (index + 1U >= range_start + width) {
                    const size_t start = index + 1U - width;
                    position_checksum ^= splitmix64_value(
                        (uint64_t)deque[front] ^
                        ((uint64_t)start *
                         UINT64_C(0xd6e8feb86659fd93)));
                    score_checksum ^= splitmix64_value(
                        scores[deque[front]] ^
                        ((uint64_t)start *
                         UINT64_C(0x9e3779b97f4a7c15)));
                    ++selected_count;
                }
            }
        }
    }
    tsc_end = read_tsc_end();
    wall_end = monotonic_nanoseconds();
    cpu_end = process_cpu_nanoseconds();
    __asm__ volatile("" ::: "memory");
    result.window_count = window_count;
    result.selected_count = selected_count;
    result.position_checksum = position_checksum;
    result.score_checksum = score_checksum;
    timing->wall_seconds = (double)(wall_end - wall_start) / 1.0e9;
    timing->cpu_seconds = (double)(cpu_end - cpu_start) / 1.0e9;
    timing->tsc_cycles = tsc_end - tsc_start;
    timing->perf_available = 0;
    timing->perf_errno = ENOTSUP;
    timing->checksum = position_checksum ^ score_checksum;
    timing->count = window_count;
    phase1_sink ^= timing->checksum;
    return result;
}

static int run_multithread_mode(const char *dataset,
                                const encoded_input_t *input,
                                const method_state_t *state,
                                const size_t *widths,
                                size_t width_count,
                                const size_t *thread_counts,
                                size_t thread_count_count,
                                unsigned repeats,
                                int perform_warmup)
{
    static const method_id_t methods[] = {
        METHOD_RANK_DERIVED,
        METHOD_XXH3_PINNED_INLINE,
        METHOD_XXH64_PINNED_INLINE,
        METHOD_MURMURHASH3,
        METHOD_WYHASH,
        METHOD_IDENTITY,
        METHOD_ODD_MULTIPLY
    };
    uint64_t *scores;
    size_t *deque_storage;
    uint64_t expected_score_checksum[METHOD_COUNT];
    uint64_t expected_position_checksum[METHOD_COUNT][PHASE1_MAX_W_VALUES];
    uint64_t expected_window_score_checksum[METHOD_COUNT][PHASE1_MAX_W_VALUES];
    size_t max_width = 0U;
    size_t thread_index;
    size_t method_index;

    if (K != 21) {
        fputs("multithread control requires K=21\n", stderr);
        return 0;
    }
    for (thread_index = 0U; thread_index < width_count; ++thread_index) {
        if (widths[thread_index] > max_width) {
            max_width = widths[thread_index];
        }
    }
    scores = (uint64_t *)malloc(input->count * sizeof(*scores));
    deque_storage = (size_t *)malloc(
        (input->count + PHASE1_MAX_THREADS * max_width) *
        sizeof(*deque_storage));
    if (scores == NULL || deque_storage == NULL) {
        free(scores); free(deque_storage);
        return 0;
    }
    memset(expected_score_checksum, 0, sizeof(expected_score_checksum));
    memset(expected_position_checksum, 0,
           sizeof(expected_position_checksum));
    memset(expected_window_score_checksum, 0,
           sizeof(expected_window_score_checksum));
    omp_set_dynamic(0);

    for (thread_index = 0U; thread_index < thread_count_count;
         ++thread_index) {
        const int requested_threads = (int)thread_counts[thread_index];
        unsigned repeat;
        if (requested_threads <= 0 ||
            requested_threads > (int)PHASE1_MAX_THREADS) {
            free(scores); free(deque_storage);
            return 0;
        }
        if (perform_warmup != 0) {
            for (method_index = 0U;
                 method_index < sizeof(methods) / sizeof(methods[0]);
                 ++method_index) {
                int observed;
                size_t width_index;
                timing_result_t ignored;
                parallel_score_function_t function =
                    parallel_score_function(methods[method_index]);
                (void)function(input->values, scores, input->count, state,
                               requested_threads, &observed);
                if (observed != requested_threads) {
                    free(scores); free(deque_storage);
                    return 0;
                }
                for (width_index = 0U; width_index < width_count;
                     ++width_index) {
                    (void)parallel_window_select(
                        scores, input->count, widths[width_index],
                        deque_storage, requested_threads, &observed,
                        &ignored);
                    if (observed != requested_threads) {
                        free(scores); free(deque_storage);
                        return 0;
                    }
                }
            }
        }
        for (repeat = 1U; repeat <= repeats; ++repeat) {
            method_id_t order[sizeof(methods) / sizeof(methods[0])];
            memcpy(order, methods, sizeof(methods));
            shuffle_methods(order,
                            sizeof(methods) / sizeof(methods[0]),
                            PHASE1_BASE_SEED ^
                            ((uint64_t)requested_threads << 32U) ^ repeat);
            for (method_index = 0U;
                 method_index < sizeof(methods) / sizeof(methods[0]);
                 ++method_index) {
                const method_id_t method = order[method_index];
                parallel_score_function_t function =
                    parallel_score_function(method);
                timing_result_t score_timing;
                int observed_score;
                size_t width_index;
                score_timing = function(input->values, scores, input->count,
                                        state, requested_threads,
                                        &observed_score);
                if (observed_score != requested_threads ||
                    score_timing.count != input->count) {
                    free(scores); free(deque_storage);
                    return 0;
                }
                if (thread_index == 0U && repeat == 1U) {
                    expected_score_checksum[method] = score_timing.checksum;
                    for (width_index = 0U; width_index < width_count;
                         ++width_index) {
                        const window_result_t serial = serial_window_result(
                            scores, input->count, widths[width_index],
                            deque_storage);
                        expected_position_checksum[method][width_index] =
                            serial.position_checksum;
                        expected_window_score_checksum[method][width_index] =
                            serial.score_checksum;
                    }
                } else if (expected_score_checksum[method] !=
                           score_timing.checksum) {
                    fprintf(stderr,
                            "multithread score checksum mismatch %s T=%d\n",
                            method_names[method], requested_threads);
                    free(scores); free(deque_storage);
                    return 0;
                }
                for (width_index = 0U; width_index < width_count;
                     ++width_index) {
                    const size_t width = widths[width_index];
                    timing_result_t window_timing;
                    int observed_window;
                    const window_result_t window = parallel_window_select(
                        scores, input->count, width, deque_storage,
                        requested_threads, &observed_window,
                        &window_timing);
                    const double total_seconds = score_timing.wall_seconds +
                                                 window_timing.wall_seconds;
                    const double throughput = total_seconds <= 0.0
                        ? NAN
                        : (double)window.window_count / total_seconds / 1.0e6;
                    if (observed_window != requested_threads ||
                        window.selected_count != window.window_count ||
                        window.position_checksum !=
                            expected_position_checksum[method][width_index] ||
                        window.score_checksum !=
                            expected_window_score_checksum[method][width_index]) {
                        fprintf(stderr,
                                "multithread window validation mismatch "
                                "%s W=%zu T=%d\n",
                                method_names[method], width,
                                requested_threads);
                        free(scores); free(deque_storage);
                        return 0;
                    }
                    printf("MULTI\t%s\t%d\t%zu\t%d\t%d\t%u\t%zu\t%s"
                           "\t%zu\t%zu\t",
                           dataset, K, width, requested_threads,
                           observed_window, repeat, method_index + 1U,
                           method_names[method], input->count,
                           window.window_count);
                    print_timing_fields(&score_timing);
                    printf("\t");
                    print_timing_fields(&window_timing);
                    printf("\t%.9f\t%.9f\t%zu\t%" PRIu64
                           "\t%" PRIu64 "\t%" PRIu64 "\t%zu\t0\n",
                           total_seconds, throughput,
                           window.selected_count,
                           window.position_checksum,
                           window.score_checksum,
                           score_timing.checksum,
                           score_timing.count);
                    fflush(stdout);
                }
            }
        }
    }
    free(scores);
    free(deque_storage);
    return 1;
}

static int parse_size_value(const char *text, size_t *value)
{
    char *end = NULL;
    unsigned long long parsed;
    errno = 0;
    parsed = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' ||
        parsed > (unsigned long long)SIZE_MAX) {
        return 0;
    }
    *value = (size_t)parsed;
    return 1;
}

static int parse_size_list(const char *text,
                           size_t *values,
                           size_t capacity,
                           size_t *count)
{
    char *copy = strdup(text);
    char *save = NULL;
    char *token;
    *count = 0U;
    if (copy == NULL) {
        return 0;
    }
    token = strtok_r(copy, ",", &save);
    while (token != NULL) {
        if (*count >= capacity ||
            !parse_size_value(token, &values[*count]) ||
            values[*count] == 0U) {
            free(copy);
            return 0;
        }
        ++*count;
        token = strtok_r(NULL, ",", &save);
    }
    free(copy);
    return *count > 0U;
}

static void usage(const char *program)
{
    fprintf(stderr,
            "usage: %s --mode MODE [--input FASTA --dataset LABEL "
            "--expected-valid-bases N] [--widths 10,20,50] "
            "[--threads 1,2,4,8,16] [--repeats 5] [--warmup 0|1]\n",
            program);
}

int main(int argc, char **argv)
{
    const char *mode = NULL;
    const char *input_path = NULL;
    const char *dataset = NULL;
    size_t expected_valid_bases = 0U;
    size_t widths[PHASE1_MAX_W_VALUES] = {10U, 20U, 50U};
    size_t width_count = 3U;
    size_t thread_counts[PHASE1_MAX_THREADS] = {1U, 2U, 4U, 8U, 16U};
    size_t thread_count_count = 5U;
    unsigned repeats = 5U;
    int warmup = 1;
    int argument;
    method_state_t state;
    initialization_measurement_t measurements[TABLE_VARIANT_COUNT];
    encoded_input_t input;
    int success = 0;

    setvbuf(stdout, NULL, _IOLBF, 0);
    for (argument = 1; argument < argc; ++argument) {
        if (strcmp(argv[argument], "--mode") == 0 &&
            argument + 1 < argc) {
            mode = argv[++argument];
        } else if (strcmp(argv[argument], "--input") == 0 &&
                   argument + 1 < argc) {
            input_path = argv[++argument];
        } else if (strcmp(argv[argument], "--dataset") == 0 &&
                   argument + 1 < argc) {
            dataset = argv[++argument];
        } else if (strcmp(argv[argument], "--expected-valid-bases") == 0 &&
                   argument + 1 < argc) {
            if (!parse_size_value(argv[++argument],
                                  &expected_valid_bases)) {
                usage(argv[0]); return EXIT_FAILURE;
            }
        } else if (strcmp(argv[argument], "--widths") == 0 &&
                   argument + 1 < argc) {
            if (!parse_size_list(argv[++argument], widths,
                                 PHASE1_MAX_W_VALUES, &width_count)) {
                usage(argv[0]); return EXIT_FAILURE;
            }
        } else if (strcmp(argv[argument], "--threads") == 0 &&
                   argument + 1 < argc) {
            if (!parse_size_list(argv[++argument], thread_counts,
                                 PHASE1_MAX_THREADS,
                                 &thread_count_count)) {
                usage(argv[0]); return EXIT_FAILURE;
            }
        } else if (strcmp(argv[argument], "--repeats") == 0 &&
                   argument + 1 < argc) {
            size_t parsed;
            if (!parse_size_value(argv[++argument], &parsed) ||
                parsed == 0U || parsed > 1000U) {
                usage(argv[0]); return EXIT_FAILURE;
            }
            repeats = (unsigned)parsed;
        } else if (strcmp(argv[argument], "--warmup") == 0 &&
                   argument + 1 < argc) {
            size_t parsed;
            if (!parse_size_value(argv[++argument], &parsed) || parsed > 1U) {
                usage(argv[0]); return EXIT_FAILURE;
            }
            warmup = (int)parsed;
        } else {
            usage(argv[0]);
            return EXIT_FAILURE;
        }
    }
    if (mode == NULL) {
        usage(argv[0]);
        return EXIT_FAILURE;
    }
    if (strcmp(mode, "initialization") == 0) {
        return run_initialization_mode() ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    if (!initialize_method_state(&state, measurements)) {
        fputs("cannot initialize Phase 1 method state\n", stderr);
        return EXIT_FAILURE;
    }
    if (phase1_accepted_xxhash_version_direct() != 703U) {
        fprintf(stderr,
                "accepted shared xxHash version is %u, required 703\n",
                phase1_accepted_xxhash_version_direct());
        destroy_method_state(&state);
        return EXIT_FAILURE;
    }
    if (strcmp(mode, "bijection-validation") == 0) {
        success = run_bijection_validation(&state);
        destroy_method_state(&state);
        return success ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    if (strcmp(mode, "deque-validation") == 0) {
        success = run_deque_validation(&state);
        destroy_method_state(&state);
        return success ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    if (input_path == NULL || dataset == NULL ||
        expected_valid_bases == 0U) {
        usage(argv[0]);
        destroy_method_state(&state);
        return EXIT_FAILURE;
    }
    if (!read_first_fasta_record(input_path, expected_valid_bases, &input)) {
        destroy_method_state(&state);
        return EXIT_FAILURE;
    }
    print_meta(dataset, &input, &state);
    if (strcmp(mode, "input-audit") == 0) {
        success = 1;
    } else if (strcmp(mode, "mapping") == 0) {
        success = run_mapping_mode(dataset, &input, &state,
                                   repeats, warmup);
    } else if (strcmp(mode, "neutral") == 0) {
        success = run_neutral_mode(dataset, &input, &state,
                                   widths, width_count,
                                   repeats, warmup);
    } else if (strcmp(mode, "rescan") == 0) {
        success = run_rescan_mode(dataset, &input, &state,
                                  widths, width_count,
                                  thread_counts, thread_count_count);
    } else if (strcmp(mode, "multithread") == 0) {
        success = run_multithread_mode(dataset, &input, &state,
                                       widths, width_count,
                                       thread_counts, thread_count_count,
                                       repeats, warmup);
    } else {
        usage(argv[0]);
        success = 0;
    }
    free(input.values);
    destroy_method_state(&state);
    fprintf(stderr, "PHASE1_SINK=%" PRIu64 "\n", phase1_sink);
    return success ? EXIT_SUCCESS : EXIT_FAILURE;
}
