#ifndef KSSD_ARRAY_INLINE_H
#define KSSD_ARRAY_INLINE_H

#include <stddef.h>
#include <stdint.h>

#include "kssd_array.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * A read-only mapping plan derived from one initialized kssd_array_t.
 *
 * The plan borrows direct permutation-table pointers from its source context.
 * The context must therefore remain initialized and alive for every mapping
 * call that uses the plan. Initialization and destruction must not overlap a
 * mapping call. A plan is safe to share between threads under the same rules
 * as its source context.
 */
typedef struct {
    size_t segment_count;
    uint8_t input_shifts[KSSD_ARRAY_MAX_SEGMENTS];
    uint64_t input_masks[KSSD_ARRAY_MAX_SEGMENTS];
    uint8_t output_shifts[KSSD_ARRAY_MAX_SEGMENTS];
    const uint16_t *permutation_tables[KSSD_ARRAY_MAX_SEGMENTS];
} kssd_array_inline_plan_t;

#ifdef __cplusplus
#define KSSD_ARRAY_INLINE_PLAN_INIT {}
#else
#define KSSD_ARRAY_INLINE_PLAN_INIT {0}
#endif

/*
 * Initialize a reusable hot-path plan from an initialized context. This is a
 * cold-path operation and performs all layout and table-pointer selection that
 * the inline mapper intentionally omits.
 */
kssd_array_status_t kssd_array_inline_plan_init(
    kssd_array_inline_plan_t *plan,
    const kssd_array_t *context);

#ifdef __cplusplus
}
#endif

#if defined(__GNUC__) || defined(__clang__)
#define KSSD_ARRAY_RUNTIME_ALWAYS_INLINE \
    static inline __attribute__((always_inline))
#else
#define KSSD_ARRAY_RUNTIME_ALWAYS_INLINE static inline
#endif

/*
 * Map one validated encoded k-mer using a preinitialized runtime plan.
 *
 * Preconditions:
 * - plan was initialized successfully by kssd_array_inline_plan_init();
 * - the source context is still initialized and alive;
 * - encoded_kmer is within the source context's 2*k-bit input domain.
 *
 * The four-case switch is deliberately unrolled: this function performs no
 * generic segment loop and no table selection by segment length.
 */
KSSD_ARRAY_RUNTIME_ALWAYS_INLINE uint64_t
kssd_array_inline_map_unchecked(const kssd_array_inline_plan_t *plan,
                                uint64_t encoded_kmer)
{
    uint64_t result = UINT64_C(0);

#define KSSD_ARRAY_INLINE_SEGMENT(INDEX)                                      \
    (((encoded_kmer) >> plan->input_shifts[(INDEX)]) &                       \
     plan->input_masks[(INDEX)])
#define KSSD_ARRAY_INLINE_MAPPED(INDEX)                                       \
    ((uint64_t)plan->permutation_tables[(INDEX)]                              \
        [(size_t)KSSD_ARRAY_INLINE_SEGMENT(INDEX)])
#define KSSD_ARRAY_INLINE_COMBINE(INDEX)                                      \
    (KSSD_ARRAY_INLINE_MAPPED(INDEX) << plan->output_shifts[(INDEX)])

    switch (plan->segment_count) {
    case 4U:
        result |= KSSD_ARRAY_INLINE_COMBINE(3U);
        /* fall through */
    case 3U:
        result |= KSSD_ARRAY_INLINE_COMBINE(2U);
        /* fall through */
    case 2U:
        result |= KSSD_ARRAY_INLINE_COMBINE(1U);
        /* fall through */
    case 1U:
        result |= KSSD_ARRAY_INLINE_COMBINE(0U);
        break;
    default:
        /* Unreachable when the documented preconditions are satisfied. */
        break;
    }

#undef KSSD_ARRAY_INLINE_COMBINE
#undef KSSD_ARRAY_INLINE_MAPPED
#undef KSSD_ARRAY_INLINE_SEGMENT

    return result;
}

#undef KSSD_ARRAY_RUNTIME_ALWAYS_INLINE

#endif
