#include "kssd_array.h"
#include "kssd_array_inline.h"
#include "permutation.h"

#include <stdlib.h>
#include <string.h>

static uint64_t segment_mask(size_t segment_length)
{
    return (UINT64_C(1) << (2U * segment_length)) - UINT64_C(1);
}

kssd_array_status_t kssd_array_layout(size_t k,
                                      size_t segment_cap,
                                      kssd_array_layout_t *layout)
{
    size_t segment_count;
    size_t quotient;
    size_t remainder;
    size_t i;

    if (layout == NULL || segment_cap == 0U ||
        segment_cap > KSSD_ARRAY_SEGMENT_CAP) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }
    if (k == 0U || k > KSSD_ARRAY_MAX_K) {
        return KSSD_ARRAY_UNSUPPORTED_K;
    }

    segment_count = (k + segment_cap - 1U) / segment_cap;
    if (segment_count == 0U || segment_count > KSSD_ARRAY_MAX_SEGMENTS) {
        return KSSD_ARRAY_UNSUPPORTED_K;
    }

    quotient = k / segment_count;
    remainder = k % segment_count;

    memset(layout, 0, sizeof(*layout));
    layout->k = k;
    layout->segment_cap = segment_cap;
    layout->segment_count = segment_count;
    for (i = 0U; i < segment_count; ++i) {
        layout->segment_lengths[i] = quotient + (i < remainder ? 1U : 0U);
    }
    layout->master_length = layout->segment_lengths[0];
    return KSSD_ARRAY_OK;
}

kssd_array_status_t kssd_array_init(kssd_array_t *context,
                                    size_t k,
                                    uint64_t seed)
{
    return kssd_array_init_with_rng(context,
                                    k,
                                    seed,
                                    KSSD_ARRAY_RNG_SPLITMIX64);
}

kssd_array_status_t kssd_array_init_with_rng(kssd_array_t *context,
                                             size_t k,
                                             uint64_t seed,
                                             kssd_array_rng_t rng)
{
    kssd_array_status_t status;
    size_t segment_length;

    if (context == NULL ||
        (rng != KSSD_ARRAY_RNG_SPLITMIX64 &&
         rng != KSSD_ARRAY_RNG_GLIBC_COMPAT) ||
        (rng == KSSD_ARRAY_RNG_GLIBC_COMPAT &&
         seed > (uint64_t)UINT32_MAX)) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }
    if (context->initialized != 0) {
        return KSSD_ARRAY_ALREADY_INITIALIZED;
    }

    status = kssd_array_layout(k, KSSD_ARRAY_SEGMENT_CAP, &context->layout);
    if (status != KSSD_ARRAY_OK) {
        return status;
    }
    context->seed = seed;
    context->rng = rng;

    status = kssd_array_build_master(&context->master_permutation,
                                     &context->master_size,
                                     context->layout.master_length,
                                     seed,
                                     rng);
    if (status != KSSD_ARRAY_OK) {
        memset(context, 0, sizeof(*context));
        return status;
    }

    for (segment_length = 1U;
         segment_length <= context->layout.master_length;
         ++segment_length) {
        if (segment_length == context->layout.master_length) {
            context->permutations[segment_length] =
                context->master_permutation;
            context->permutation_sizes[segment_length] =
                context->master_size;
            continue;
        }

        status = kssd_array_derive_permutation(
            context->master_permutation,
            context->layout.master_length,
            segment_length,
            &context->permutations[segment_length],
            &context->permutation_sizes[segment_length]);
        if (status != KSSD_ARRAY_OK) {
            kssd_array_destroy(context);
            return status;
        }
    }

    context->initialized = 1;
    return KSSD_ARRAY_OK;
}

void kssd_array_destroy(kssd_array_t *context)
{
    size_t segment_length;

    if (context == NULL) {
        return;
    }

    for (segment_length = 1U;
         segment_length <= KSSD_ARRAY_SEGMENT_CAP;
         ++segment_length) {
        if (context->permutations[segment_length] != NULL &&
            context->permutations[segment_length] !=
                context->master_permutation) {
            free(context->permutations[segment_length]);
        }
    }
    free(context->master_permutation);
    memset(context, 0, sizeof(*context));
}

kssd_array_status_t kssd_array_inline_plan_init(
    kssd_array_inline_plan_t *plan,
    const kssd_array_t *context)
{
    size_t consumed = 0U;
    size_t segment_index;

    if (plan == NULL || context == NULL) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }
    memset(plan, 0, sizeof(*plan));
    if (context->initialized == 0) {
        return KSSD_ARRAY_NOT_INITIALIZED;
    }
    if (context->layout.segment_count == 0U ||
        context->layout.segment_count > KSSD_ARRAY_MAX_SEGMENTS) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }

    plan->segment_count = context->layout.segment_count;
    for (segment_index = 0U;
         segment_index < context->layout.segment_count;
         ++segment_index) {
        const size_t segment_length =
            context->layout.segment_lengths[segment_index];
        size_t remaining;

        if (segment_length == 0U ||
            segment_length > KSSD_ARRAY_SEGMENT_CAP ||
            consumed + segment_length > context->layout.k ||
            context->permutations[segment_length] == NULL) {
            memset(plan, 0, sizeof(*plan));
            return KSSD_ARRAY_INVALID_ARGUMENT;
        }
        consumed += segment_length;
        remaining = context->layout.k - consumed;
        plan->input_shifts[segment_index] = (uint8_t)(2U * remaining);
        plan->input_masks[segment_index] = segment_mask(segment_length);
        plan->output_shifts[segment_index] = (uint8_t)(2U * remaining);
        plan->permutation_tables[segment_index] =
            context->permutations[segment_length];
    }
    if (consumed != context->layout.k) {
        memset(plan, 0, sizeof(*plan));
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }
    return KSSD_ARRAY_OK;
}

uint64_t kssd_array_map_unchecked(const kssd_array_t *context,
                                  uint64_t encoded_kmer)
{
    uint64_t result = UINT64_C(0);
    size_t consumed = 0U;
    size_t segment_index;

    for (segment_index = 0U;
         segment_index < context->layout.segment_count;
         ++segment_index) {
        const size_t segment_length =
            context->layout.segment_lengths[segment_index];
        const size_t remaining =
            context->layout.k - consumed - segment_length;
        const size_t input_shift = 2U * remaining;
        const uint64_t segment =
            (encoded_kmer >> input_shift) & segment_mask(segment_length);
        const uint16_t mapped =
            context->permutations[segment_length][(size_t)segment];

        result = (result << (2U * segment_length)) | (uint64_t)mapped;
        consumed += segment_length;
    }

    return result;
}

kssd_array_status_t kssd_array_map(const kssd_array_t *context,
                                   uint64_t encoded_kmer,
                                   uint64_t *result)
{
    if (context == NULL || result == NULL) {
        return KSSD_ARRAY_INVALID_ARGUMENT;
    }
    if (context->initialized == 0) {
        return KSSD_ARRAY_NOT_INITIALIZED;
    }
    if (context->layout.k < KSSD_ARRAY_MAX_K &&
        (encoded_kmer >> (2U * context->layout.k)) != UINT64_C(0)) {
        return KSSD_ARRAY_INPUT_OUT_OF_RANGE;
    }

    *result = kssd_array_map_unchecked(context, encoded_kmer);
    return KSSD_ARRAY_OK;
}

const uint16_t *kssd_array_master_permutation(const kssd_array_t *context,
                                              size_t *size)
{
    if (size != NULL) {
        *size = (context != NULL && context->initialized != 0)
                    ? context->master_size
                    : 0U;
    }
    return (context != NULL && context->initialized != 0)
               ? context->master_permutation
               : NULL;
}

const uint16_t *kssd_array_permutation(const kssd_array_t *context,
                                       size_t segment_length,
                                       size_t *size)
{
    const int valid = context != NULL && context->initialized != 0 &&
                      segment_length > 0U &&
                      segment_length <= context->layout.master_length;

    if (size != NULL) {
        *size = valid ? context->permutation_sizes[segment_length] : 0U;
    }
    return valid ? context->permutations[segment_length] : NULL;
}

const char *kssd_array_status_string(kssd_array_status_t status)
{
    switch (status) {
    case KSSD_ARRAY_OK:
        return "success";
    case KSSD_ARRAY_INVALID_ARGUMENT:
        return "invalid argument";
    case KSSD_ARRAY_UNSUPPORTED_K:
        return "unsupported k";
    case KSSD_ARRAY_OUT_OF_MEMORY:
        return "out of memory";
    case KSSD_ARRAY_NOT_INITIALIZED:
        return "context is not initialized";
    case KSSD_ARRAY_INPUT_OUT_OF_RANGE:
        return "encoded k-mer is outside the 2k-bit input domain";
    case KSSD_ARRAY_ALREADY_INITIALIZED:
        return "context is already initialized";
    default:
        return "unknown status";
    }
}
