#ifndef KSSD_ARRAY_FAST_H
#define KSSD_ARRAY_FAST_H

#include <stddef.h>
#include <stdint.h>

#include "kssd_array.h"

#ifndef KSSD_ARRAY_FIXED_K
#error "Define KSSD_ARRAY_FIXED_K before including kssd_array_fast.h"
#endif

#if KSSD_ARRAY_FIXED_K < 1 || KSSD_ARRAY_FIXED_K > 32
#error "KSSD_ARRAY_FIXED_K must be in the range 1..32"
#endif

#if defined(__GNUC__) || defined(__clang__)
#define KSSD_ARRAY_ALWAYS_INLINE static inline __attribute__((always_inline))
#else
#define KSSD_ARRAY_ALWAYS_INLINE static inline
#endif

/*
 * Map one validated 2-bit encoded k-mer for the compile-time fixed k.
 *
 * Preconditions:
 * - context was initialized successfully for KSSD_ARRAY_FIXED_K;
 * - encoded_kmer has no bits above the low 2*k bits when k is below 32;
 * - initialization/destruction does not overlap this call.
 *
 * The function allocates nothing and consumes the same rank-derived tables
 * owned by kssd_array_t as the checked and unchecked core APIs. The result is
 * in [0, 4^k); the function cannot detect ambiguous bases after encoding.
 */
KSSD_ARRAY_ALWAYS_INLINE uint64_t
kssd_array_fast_with_tables(uint64_t encoded_kmer,
                            const kssd_array_t *context)
{
    const size_t fixed_k = (size_t)KSSD_ARRAY_FIXED_K;
    const size_t segment_count =
        (fixed_k + KSSD_ARRAY_SEGMENT_CAP - 1U) /
        KSSD_ARRAY_SEGMENT_CAP;
    const size_t quotient = fixed_k / segment_count;
    const size_t remainder = fixed_k % segment_count;
    uint64_t result = UINT64_C(0);
    size_t consumed = 0U;
    size_t segment_index;

    for (segment_index = 0U; segment_index < segment_count;
         ++segment_index) {
        const size_t segment_length =
            quotient + (segment_index < remainder ? 1U : 0U);
        const size_t remaining = fixed_k - consumed - segment_length;
        const size_t width = 2U * segment_length;
        const uint64_t mask = (UINT64_C(1) << width) - UINT64_C(1);
        const uint64_t segment =
            (encoded_kmer >> (2U * remaining)) & mask;
        const uint16_t mapped =
            context->permutations[segment_length][(size_t)segment];

        result = (result << width) | (uint64_t)mapped;
        consumed += segment_length;
    }
    return result;
}

#undef KSSD_ARRAY_ALWAYS_INLINE

#endif
