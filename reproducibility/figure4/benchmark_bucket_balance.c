#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <kssd_array.h>
#define XXH_STATIC_LINKING_ONLY
#include <xxhash.h>

enum { METHOD_COUNT = 5 };

static uint64_t splitmix64_next(uint64_t *state)
{
    uint64_t value;

    *state += UINT64_C(0x9e3779b97f4a7c15);
    value = *state;
    value = (value ^ (value >> 30U)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27U)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31U);
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

static uint64_t murmurhash3_8bytes(uint64_t key, uint64_t seed)
{
    uint64_t h1 = (uint64_t)(uint32_t)seed;
    uint64_t h2 = (uint64_t)(uint32_t)seed;
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
#error "This workflow requires compiler support for uint128"
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

static void print_histogram(const char *method,
                            const uint64_t *counts,
                            size_t bins)
{
    size_t index;

    printf("HIST\t%s", method);
    for (index = 0U; index < bins; ++index) {
        printf("\t%" PRIu64, counts[index]);
    }
    putchar('\n');
}

int main(int argc, char **argv)
{
    static const char *method_names[METHOD_COUNT] = {
        "KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "wyhash"};
    uint64_t raw_k;
    uint64_t raw_bins;
    uint64_t sequence_length;
    uint64_t seed;
    uint64_t sequence_seed;
    uint64_t sequence_state;
    uint64_t mask;
    uint64_t current_kmer = UINT64_C(0);
    uint64_t mapped_count;
    uint64_t kssd_domain_max;
    uint64_t kssd_observed_max = UINT64_C(0);
    uint64_t wy_secret[4];
    uint64_t *storage;
    uint64_t *histograms[METHOD_COUNT];
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    size_t k;
    size_t bins;
    size_t method;
    size_t position;

    if (argc != 5) {
        fprintf(stderr, "usage: %s K BINS SEQUENCE_LENGTH SEED\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (!parse_uint64(argv[1], &raw_k) ||
        !parse_uint64(argv[2], &raw_bins) ||
        !parse_uint64(argv[3], &sequence_length) ||
        !parse_uint64(argv[4], &seed) ||
        raw_k == UINT64_C(0) || raw_k > UINT64_C(32) ||
        raw_bins == UINT64_C(0) || raw_bins > (uint64_t)SIZE_MAX ||
        sequence_length < raw_k) {
        fputs("invalid K, BINS, SEQUENCE_LENGTH, or SEED\n", stderr);
        return EXIT_FAILURE;
    }
    k = (size_t)raw_k;
    bins = (size_t)raw_bins;
    if (bins > SIZE_MAX / METHOD_COUNT / sizeof(*storage)) {
        fputs("histogram allocation is too large\n", stderr);
        return EXIT_FAILURE;
    }

    storage = (uint64_t *)calloc(METHOD_COUNT * bins, sizeof(*storage));
    if (storage == NULL) {
        fputs("cannot allocate histograms\n", stderr);
        return EXIT_FAILURE;
    }
    for (method = 0U; method < METHOD_COUNT; ++method) {
        histograms[method] = storage + method * bins;
    }

    if (kssd_array_init_with_rng(&context, k, seed,
                                 KSSD_ARRAY_RNG_SPLITMIX64) != KSSD_ARRAY_OK) {
        fputs("cannot initialize public KSSD-Array context\n", stderr);
        free(storage);
        return EXIT_FAILURE;
    }
    wy_make_secret(seed, wy_secret);
    sequence_seed = seed + UINT64_C(1000003);
    sequence_state = sequence_seed;
    mapped_count = sequence_length - raw_k + UINT64_C(1);
    mask = k == 32U ? UINT64_MAX
                    : (UINT64_C(1) << (2U * k)) - UINT64_C(1);
    kssd_domain_max = mask;

    for (position = 0U; position < k; ++position) {
        current_kmer = (current_kmer << 2U) |
                       (splitmix64_next(&sequence_state) & UINT64_C(3));
    }
    for (position = 0U; (uint64_t)position < mapped_count; ++position) {
        uint64_t mapped;

        if (position != 0U) {
            current_kmer = ((current_kmer << 2U) |
                            (splitmix64_next(&sequence_state) & UINT64_C(3))) &
                           mask;
        }
        mapped = kssd_array_map_unchecked(&context, current_kmer);
        if (mapped > kssd_observed_max) {
            kssd_observed_max = mapped;
        }
        ++histograms[0][mapped % raw_bins];
        ++histograms[1][XXH3_64bits_withSeed(&current_kmer,
                                             sizeof(current_kmer), seed) %
                        raw_bins];
        ++histograms[2][XXH64(&current_kmer, sizeof(current_kmer), seed) %
                        raw_bins];
        ++histograms[3][murmurhash3_8bytes(current_kmer, seed) % raw_bins];
        ++histograms[4][wyhash_8bytes(current_kmer, wy_secret) % raw_bins];
    }

    printf("META\tK=%zu\tBINS=%zu\tSEQUENCE_LENGTH=%" PRIu64
           "\tSEED=%" PRIu64 "\tSEQUENCE_SEED=%" PRIu64
           "\tMAPPED_COUNT=%" PRIu64 "\tKSSD_DOMAIN_MAX=%" PRIu64
           "\tKSSD_OBSERVED_MAX=%" PRIu64 "\tXXHASH_VERSION=%u\n",
           k, bins, sequence_length, seed, sequence_seed, mapped_count,
           kssd_domain_max, kssd_observed_max, XXH_versionNumber());
    for (method = 0U; method < METHOD_COUNT; ++method) {
        print_histogram(method_names[method], histograms[method], bins);
    }

    kssd_array_destroy(&context);
    free(storage);
    return EXIT_SUCCESS;
}
