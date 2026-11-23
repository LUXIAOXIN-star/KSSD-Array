#include "permutation.h"

#include <stdlib.h>

typedef struct {
    uint16_t value;
    uint16_t index;
} kssd_array_rank_pair_t;

typedef struct {
    kssd_array_rng_t kind;
    uint64_t splitmix_state;
    uint32_t glibc_state[344];
    size_t glibc_index;
} kssd_array_rng_state_t;

static uint64_t splitmix64_next(uint64_t *state)
{
    uint64_t z;

    *state += UINT64_C(0x9E3779B97F4A7C15);
    z = *state;
    z = (z ^ (z >> 30U)) * UINT64_C(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27U)) * UINT64_C(0x94D049BB133111EB);
    return z ^ (z >> 31U);
}

static void glibc_compat_seed(kssd_array_rng_state_t *rng, uint32_t seed)
{
    int64_t word;
    size_t i;

    if (seed == 0U) {
        seed = 1U;
    }
    rng->glibc_state[0] = seed;
    /* glibc converts the unsigned seed to a signed 32-bit word here. */
    word = seed <= (uint32_t)INT32_MAX
               ? (int64_t)seed
               : (int64_t)seed - INT64_C(4294967296);
    for (i = 1U; i < 31U; ++i) {
        word = (INT64_C(16807) * word) % INT64_C(2147483647);
        if (word < 0) {
            word += INT64_C(2147483647);
        }
        rng->glibc_state[i] = (uint32_t)word;
    }
    rng->glibc_state[31] = rng->glibc_state[0];
    rng->glibc_state[32] = rng->glibc_state[1];
    rng->glibc_state[33] = rng->glibc_state[2];
    for (i = 34U; i < 344U; ++i) {
        rng->glibc_state[i] =
            rng->glibc_state[i - 31U] + rng->glibc_state[i - 3U];
    }
    rng->glibc_index = 344U;
}

static void rng_seed(kssd_array_rng_state_t *rng,
                     kssd_array_rng_t kind,
                     uint64_t seed)
{
    rng->kind = kind;
    rng->splitmix_state = seed;
    if (kind == KSSD_ARRAY_RNG_GLIBC_COMPAT) {
        glibc_compat_seed(rng, (uint32_t)seed);
    }
}

static uint64_t rng_next(kssd_array_rng_state_t *rng)
{
    if (rng->kind == KSSD_ARRAY_RNG_SPLITMIX64) {
        return splitmix64_next(&rng->splitmix_state);
    }

    {
        const size_t index = rng->glibc_index;
        const uint32_t value =
            rng->glibc_state[(index - 31U) % 344U] +
            rng->glibc_state[(index - 3U) % 344U];
        rng->glibc_state[index % 344U] = value;
        rng->glibc_index = index + 1U;
        return (uint64_t)(value >> 1U);
    }
}

static int compare_rank_pair(const void *left, const void *right)
{
    const kssd_array_rank_pair_t *a =
        (const kssd_array_rank_pair_t *)left;
    const kssd_array_rank_pair_t *b =
        (const kssd_array_rank_pair_t *)right;

    if (a->value != b->value) {
        return (a->value > b->value) - (a->value < b->value);
    }
    return (a->index > b->index) - (a->index < b->index);
}

kssd_array_status_t kssd_array_pow4(size_t segment_length, size_t *result)
{
    if (result == NULL || segment_length == 0U ||
        segment_length > KSSD_ARRAY_SEGMENT_CAP) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }

    *result = (size_t)1U << (2U * segment_length);
    return KSSD_ARRAY_OK;
}

kssd_array_status_t kssd_array_build_master(uint16_t **master,
                                            size_t *master_size,
                                            size_t master_length,
                                            uint64_t seed,
                                            kssd_array_rng_t rng_kind)
{
    uint16_t *permutation;
    kssd_array_rng_state_t rng;
    size_t size;
    size_t i;

    if (master == NULL || master_size == NULL ||
        (rng_kind != KSSD_ARRAY_RNG_SPLITMIX64 &&
         rng_kind != KSSD_ARRAY_RNG_GLIBC_COMPAT) ||
        (rng_kind == KSSD_ARRAY_RNG_GLIBC_COMPAT &&
         seed > (uint64_t)UINT32_MAX)) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }
    *master = NULL;
    *master_size = 0U;

    if (kssd_array_pow4(master_length, &size) != KSSD_ARRAY_OK) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }

    permutation = (uint16_t *)malloc(size * sizeof(*permutation));
    if (permutation == NULL) {
        return KSSD_ARRAY_OUT_OF_MEMORY;
    }

    for (i = 0U; i < size; ++i) {
        permutation[i] = (uint16_t)i;
    }

    rng_seed(&rng, rng_kind, seed);
    /* Fisher-Yates with an explicitly versioned deterministic RNG stream. */
    for (i = size - 1U; i > 0U; --i) {
        const size_t j =
            (size_t)(rng_next(&rng) % (uint64_t)(i + 1U));
        const uint16_t temporary = permutation[i];
        permutation[i] = permutation[j];
        permutation[j] = temporary;
    }

    *master = permutation;
    *master_size = size;
    return KSSD_ARRAY_OK;
}

kssd_array_status_t kssd_array_derive_permutation(const uint16_t *master,
                                                  size_t master_length,
                                                  size_t segment_length,
                                                  uint16_t **derived,
                                                  size_t *derived_size)
{
    kssd_array_rank_pair_t *pairs;
    uint16_t *permutation;
    size_t size;
    size_t rank;
    size_t x;
    size_t pad_shift;

    if (master == NULL || derived == NULL || derived_size == NULL ||
        segment_length == 0U || segment_length >= master_length ||
        master_length > KSSD_ARRAY_SEGMENT_CAP) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }
    *derived = NULL;
    *derived_size = 0U;

    if (kssd_array_pow4(segment_length, &size) != KSSD_ARRAY_OK) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }

    pairs = (kssd_array_rank_pair_t *)malloc(size * sizeof(*pairs));
    permutation = (uint16_t *)malloc(size * sizeof(*permutation));
    if (pairs == NULL || permutation == NULL) {
        free(pairs);
        free(permutation);
        return KSSD_ARRAY_OUT_OF_MEMORY;
    }

    pad_shift = 2U * (master_length - segment_length);
    for (x = 0U; x < size; ++x) {
        const size_t padded = x << pad_shift;
        pairs[x].value = master[padded];
        pairs[x].index = (uint16_t)x;
    }

    qsort(pairs, size, sizeof(*pairs), compare_rank_pair);
    for (rank = 0U; rank < size; ++rank) {
        permutation[pairs[rank].index] = (uint16_t)rank;
    }

    free(pairs);
    *derived = permutation;
    *derived_size = size;
    return KSSD_ARRAY_OK;
}
