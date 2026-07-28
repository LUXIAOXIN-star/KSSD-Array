#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include <kssd_array.h>
#define KSSD_ARRAY_FIXED_K 5
#include <kssd_array_fast.h>

#define WINDOW_SIZE 4U

static int base_code(char base, uint64_t *code)
{
    switch (base) {
    case 'A':
        *code = UINT64_C(0);
        return 1;
    case 'C':
        *code = UINT64_C(1);
        return 1;
    case 'G':
        *code = UINT64_C(2);
        return 1;
    case 'T':
        *code = UINT64_C(3);
        return 1;
    default:
        return 0;
    }
}

int main(void)
{
    static const char sequence[] = "ACGTACGTTGCAACGT";
    enum { K = KSSD_ARRAY_FIXED_K };
    const size_t sequence_length = sizeof(sequence) - 1U;
    const size_t kmer_count = sequence_length - K + 1U;
    uint64_t mapped[sizeof(sequence) - K];
    const uint64_t mask = (UINT64_C(1) << (2U * K)) - UINT64_C(1);
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    uint64_t rolling = UINT64_C(0);
    size_t valid_bases = 0U;
    size_t index;

    if (kssd_array_init(&context, K, KSSD_ARRAY_DEFAULT_SEED) !=
        KSSD_ARRAY_OK) {
        fputs("context initialization failed\n", stderr);
        return 1;
    }

    for (index = 0U; index < sequence_length; ++index) {
        uint64_t code;
        if (!base_code(sequence[index], &code)) {
            /* Real callers should reset rolling state at an ambiguous base. */
            rolling = UINT64_C(0);
            valid_bases = 0U;
            continue;
        }
        rolling = ((rolling << 2U) | code) & mask;
        ++valid_bases;
        if (valid_bases >= K) {
            mapped[index - K + 1U] =
                kssd_array_fast_with_tables(rolling, &context);
        }
    }

    printf("sequence: %s\n", sequence);
    for (index = 0U; index + WINDOW_SIZE <= kmer_count; ++index) {
        size_t offset;
        size_t minimum_offset = 0U;
        for (offset = 1U; offset < WINDOW_SIZE; ++offset) {
            if (mapped[index + offset] < mapped[index + minimum_offset]) {
                minimum_offset = offset;
            }
        }
        printf("window %zu: position=%zu value=%" PRIu64 "\n",
               index,
               index + minimum_offset,
               mapped[index + minimum_offset]);
    }

    kssd_array_destroy(&context);
    return 0;
}
