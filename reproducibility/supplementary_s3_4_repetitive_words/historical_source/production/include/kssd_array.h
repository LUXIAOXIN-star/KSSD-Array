#ifndef KSSD_ARRAY_H
#define KSSD_ARRAY_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define KSSD_ARRAY_MAX_K 32U
#define KSSD_ARRAY_SEGMENT_CAP 8U
#define KSSD_ARRAY_MAX_SEGMENTS 4U
#define KSSD_ARRAY_DEFAULT_SEED UINT64_C(42)

typedef enum {
    KSSD_ARRAY_OK = 0,
    KSSD_ARRAY_INVALID_ARGUMENT,
    KSSD_ARRAY_UNSUPPORTED_K,
    KSSD_ARRAY_OUT_OF_MEMORY,
    KSSD_ARRAY_NOT_INITIALIZED,
    KSSD_ARRAY_INPUT_OUT_OF_RANGE,
    KSSD_ARRAY_ALREADY_INITIALIZED
} kssd_array_status_t;

typedef enum {
    /* Portable stream used by the exhaustive ablation and seed experiments. */
    KSSD_ARRAY_RNG_SPLITMIX64 = 0,
    /* Exact local emulation of the glibc rand() stream used by server runs. */
    KSSD_ARRAY_RNG_GLIBC_COMPAT
} kssd_array_rng_t;

typedef struct {
    size_t k;
    size_t segment_cap;
    size_t segment_count;
    size_t segment_lengths[KSSD_ARRAY_MAX_SEGMENTS];
    size_t master_length;
} kssd_array_layout_t;

/*
 * One context owns one master permutation R_L and all rank-derived P_s.
 * A zero-initialized context may be initialized once and must be destroyed
 * before it is initialized again. Mapping through an initialized const context
 * is read-only and may be performed concurrently by multiple threads after the
 * creating thread has safely published the initialized context. Initialization
 * and destruction must never overlap a mapping call.
 *
 * This is an owning, non-copyable object: do not copy it by value and do not
 * modify its fields. The fields are public only so callers can allocate the
 * context without a second heap object; use the accessors below for inspection.
 */
typedef struct {
    kssd_array_layout_t layout;
    uint64_t seed;
    kssd_array_rng_t rng;
    uint16_t *master_permutation;
    size_t master_size;
    uint16_t *permutations[KSSD_ARRAY_SEGMENT_CAP + 1U];
    size_t permutation_sizes[KSSD_ARRAY_SEGMENT_CAP + 1U];
    int initialized;
} kssd_array_t;

#ifdef __cplusplus
#define KSSD_ARRAY_CONTEXT_INIT {}
#else
#define KSSD_ARRAY_CONTEXT_INIT {0}
#endif

/* Compute the nucleotide-level balanced segmentation used by the manuscript. */
kssd_array_status_t kssd_array_layout(size_t k,
                                      size_t segment_cap,
                                      kssd_array_layout_t *layout);

/*
 * Initialize for 1 <= k <= 32 with a deterministic SplitMix64 stream.
 * Equal (k, seed, RNG mode) tuples produce identical tables and mappings.
 */
kssd_array_status_t kssd_array_init(kssd_array_t *context,
                                    size_t k,
                                    uint64_t seed);

/* Select an explicitly versioned master-permutation RNG. */
kssd_array_status_t kssd_array_init_with_rng(kssd_array_t *context,
                                             size_t k,
                                             uint64_t seed,
                                             kssd_array_rng_t rng);

/* Release all arrays owned by context. Safe for a zero-initialized context. */
void kssd_array_destroy(kssd_array_t *context);

/*
 * Checked mapping. Inputs are already encoded by the caller; this API cannot
 * detect ambiguous DNA bases. Inputs for k<32 must not contain set bits above
 * bit 2k-1. The result is written only on success and is in [0, 4^k). For a
 * fixed initialized context, mapping is a permutation of that complete domain.
 */
kssd_array_status_t kssd_array_map(const kssd_array_t *context,
                                   uint64_t encoded_kmer,
                                   uint64_t *result);

/*
 * Hot-path mapping for a validated input and initialized context. It has the
 * same output domain as kssd_array_map() but performs no argument checks.
 */
uint64_t kssd_array_map_unchecked(const kssd_array_t *context,
                                  uint64_t encoded_kmer);

/* Read-only inspection helpers used by validation and integrations. */
const uint16_t *kssd_array_master_permutation(const kssd_array_t *context,
                                              size_t *size);
const uint16_t *kssd_array_permutation(const kssd_array_t *context,
                                       size_t segment_length,
                                       size_t *size);

const char *kssd_array_status_string(kssd_array_status_t status);

#ifdef __cplusplus
}
#endif

#endif
