#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <kssd_array.h>
#include <kssd_array_inline.h>

#define RANDOM_CASES_PER_K 100000U
#define EXHAUSTIVE_MAX_K 9U

static uint64_t next_value(uint64_t *state)
{
    uint64_t value;

    *state += UINT64_C(0x9e3779b97f4a7c15);
    value = *state;
    value = (value ^ (value >> 30U)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27U)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31U);
}

static uint64_t input_mask(size_t k)
{
    return k == KSSD_ARRAY_MAX_K
               ? UINT64_MAX
               : (UINT64_C(1) << (2U * k)) - UINT64_C(1);
}

static int compare_one(const kssd_array_t *context,
                       const kssd_array_inline_plan_t *plan,
                       size_t k,
                       kssd_array_rng_t rng,
                       uint64_t input,
                       const char *case_kind,
                       size_t case_index)
{
    const uint64_t generic = kssd_array_map_unchecked(context, input);
    const uint64_t inlined = kssd_array_inline_map_unchecked(plan, input);

    if (generic != inlined) {
        fprintf(stderr,
                "runtime-inline mismatch: k=%zu rng=%d kind=%s index=%zu "
                "input=%" PRIu64 " generic=%" PRIu64 " inline=%" PRIu64
                "\n",
                k, (int)rng, case_kind, case_index, input, generic, inlined);
        return 0;
    }
    return 1;
}

static int test_plan_errors(void)
{
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    kssd_array_inline_plan_t plan = KSSD_ARRAY_INLINE_PLAN_INIT;
    kssd_array_inline_plan_t zero = KSSD_ARRAY_INLINE_PLAN_INIT;

    if (kssd_array_inline_plan_init(NULL, &context) !=
            KSSD_ARRAY_INVALID_ARGUMENT ||
        kssd_array_inline_plan_init(&plan, NULL) !=
            KSSD_ARRAY_INVALID_ARGUMENT ||
        kssd_array_inline_plan_init(&plan, &context) !=
            KSSD_ARRAY_NOT_INITIALIZED ||
        memcmp(&plan, &zero, sizeof(plan)) != 0) {
        fprintf(stderr, "runtime-inline plan error handling failed\n");
        return 0;
    }
    return 1;
}

static int test_context(size_t k, kssd_array_rng_t rng)
{
    static const uint64_t fixed_values[] = {
        UINT64_C(0),
        UINT64_C(1),
        UINT64_C(0x0123456789abcdef),
        UINT64_C(0xfedcba9876543210),
        UINT64_C(0xaaaaaaaaaaaaaaaa),
        UINT64_C(0x5555555555555555)};
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    kssd_array_inline_plan_t plan = KSSD_ARRAY_INLINE_PLAN_INIT;
    const uint64_t mask = input_mask(k);
    uint64_t stream = UINT64_C(0xd1b54a32d192ed03) ^
                      ((uint64_t)k << 32U) ^ (uint64_t)rng;
    size_t index;

    if (kssd_array_init_with_rng(&context,
                                 k,
                                 KSSD_ARRAY_DEFAULT_SEED,
                                 rng) != KSSD_ARRAY_OK) {
        fprintf(stderr, "context initialization failed: k=%zu rng=%d\n",
                k, (int)rng);
        return 0;
    }
    if (kssd_array_inline_plan_init(&plan, &context) != KSSD_ARRAY_OK ||
        plan.segment_count != context.layout.segment_count) {
        fprintf(stderr, "plan initialization failed: k=%zu rng=%d\n",
                k, (int)rng);
        kssd_array_destroy(&context);
        return 0;
    }

    for (index = 0U;
         index < sizeof(fixed_values) / sizeof(fixed_values[0]);
         ++index) {
        if (!compare_one(&context, &plan, k, rng,
                         fixed_values[index] & mask, "fixed", index)) {
            kssd_array_destroy(&context);
            return 0;
        }
    }
    if (!compare_one(&context, &plan, k, rng, mask, "maximum", 0U) ||
        !compare_one(&context, &plan, k, rng, mask >> 1U,
                     "half-maximum", 0U) ||
        !compare_one(&context, &plan, k, rng,
                     mask == 0U ? 0U : mask - UINT64_C(1),
                     "maximum-minus-one", 0U)) {
        kssd_array_destroy(&context);
        return 0;
    }

    for (index = 0U; index < plan.segment_count; ++index) {
        const size_t shift = plan.input_shifts[index];
        const uint64_t low_boundary = UINT64_C(1) << shift;
        const uint64_t high_boundary =
            plan.input_masks[index] << shift;

        if (!compare_one(&context, &plan, k, rng,
                         low_boundary & mask, "segment-low", index) ||
            !compare_one(&context, &plan, k, rng,
                         high_boundary & mask, "segment-high", index)) {
            kssd_array_destroy(&context);
            return 0;
        }
    }

    if (k <= EXHAUSTIVE_MAX_K) {
        const uint64_t domain_size = UINT64_C(1) << (2U * k);
        uint64_t input;

        for (input = UINT64_C(0); input < domain_size; ++input) {
            if (!compare_one(&context, &plan, k, rng, input,
                             "exhaustive", (size_t)input)) {
                kssd_array_destroy(&context);
                return 0;
            }
        }
    }

    for (index = 0U; index < RANDOM_CASES_PER_K; ++index) {
        const uint64_t input = next_value(&stream) & mask;

        if (!compare_one(&context, &plan, k, rng, input,
                         "random", index)) {
            kssd_array_destroy(&context);
            return 0;
        }
    }

    printf("runtime-inline parity passed: k=%zu rng=%d segments=%zu "
           "random=%u exhaustive=%s\n",
           k, (int)rng, plan.segment_count,
           (unsigned)RANDOM_CASES_PER_K,
           k <= EXHAUSTIVE_MAX_K ? "yes" : "no");
    kssd_array_destroy(&context);
    return 1;
}

int main(void)
{
    static const kssd_array_rng_t rngs[] = {
        KSSD_ARRAY_RNG_SPLITMIX64,
        KSSD_ARRAY_RNG_GLIBC_COMPAT};
    size_t rng_index;
    size_t k;

    if (!test_plan_errors()) {
        return 1;
    }
    for (rng_index = 0U; rng_index < sizeof(rngs) / sizeof(rngs[0]);
         ++rng_index) {
        for (k = 1U; k <= KSSD_ARRAY_MAX_K; ++k) {
            if (!test_context(k, rngs[rng_index])) {
                return 1;
            }
        }
    }
    puts("runtime-inline parity passed for k=1..32 and both RNG modes");
    return 0;
}
