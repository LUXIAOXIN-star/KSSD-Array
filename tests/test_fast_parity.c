#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include <kssd_array.h>
#include <kssd_array_fast.h>

static uint64_t next_value(uint64_t *state)
{
    uint64_t value;

    *state += UINT64_C(0x9e3779b97f4a7c15);
    value = *state;
    value = (value ^ (value >> 30U)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27U)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31U);
}

static uint64_t input_mask(void)
{
#if KSSD_ARRAY_FIXED_K == 32
    return UINT64_MAX;
#else
    return (UINT64_C(1) << (2U * KSSD_ARRAY_FIXED_K)) - UINT64_C(1);
#endif
}

int main(void)
{
    static const uint64_t seeds[] = {
        UINT64_C(0), UINT64_C(1), KSSD_ARRAY_DEFAULT_SEED,
        UINT64_C(0x123456789abcdef0)};
    const uint64_t mask = input_mask();
    size_t seed_index;

    for (seed_index = 0U; seed_index < sizeof(seeds) / sizeof(seeds[0]);
         ++seed_index) {
        kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
        uint64_t stream = seeds[seed_index] ^ UINT64_C(0xd1b54a32d192ed03);
        size_t input_index;

        if (kssd_array_init(&context,
                            (size_t)KSSD_ARRAY_FIXED_K,
                            seeds[seed_index]) != KSSD_ARRAY_OK) {
            fprintf(stderr, "context initialization failed for k=%d\n",
                    KSSD_ARRAY_FIXED_K);
            return 1;
        }

        for (input_index = 0U; input_index < 4096U; ++input_index) {
            uint64_t input;
            uint64_t core;
            uint64_t fast;

            switch (input_index) {
            case 0U:
                input = UINT64_C(0);
                break;
            case 1U:
                input = UINT64_C(1) & mask;
                break;
            case 2U:
                input = mask;
                break;
            case 3U:
                input = mask >> 1U;
                break;
            case 4U:
                input = UINT64_C(0x0123456789abcdef) & mask;
                break;
            case 5U:
                input = UINT64_C(0xfedcba9876543210) & mask;
                break;
            default:
                input = next_value(&stream) & mask;
                break;
            }

            core = kssd_array_map_unchecked(&context, input);
            fast = kssd_array_fast_with_tables(input, &context);
            if (core != fast) {
                fprintf(stderr,
                        "fast-path mismatch: k=%d seed=%" PRIu64
                        " input=%" PRIu64 " core=%" PRIu64
                        " fast=%" PRIu64 "\n",
                        KSSD_ARRAY_FIXED_K,
                        seeds[seed_index],
                        input,
                        core,
                        fast);
                kssd_array_destroy(&context);
                return 1;
            }
        }
        kssd_array_destroy(&context);
    }

    printf("fast-path parity passed for k=%d\n", KSSD_ARRAY_FIXED_K);
    return 0;
}
