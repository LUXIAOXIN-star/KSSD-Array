#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

int main(int argc, char **argv)
{
    const char *sequence = "ACGTACGTTGCAACGT";
    enum { K = KSSD_ARRAY_FIXED_K };
    size_t sequence_length;
    size_t kmer_count;
    uint64_t *mapped;
    const uint64_t mask = (UINT64_C(1) << (2U * K)) - UINT64_C(1);
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    uint64_t rolling = UINT64_C(0);
    size_t valid_bases = 0U;
    size_t index;

    if (argc > 2) {
        fprintf(stderr, "usage: %s [DNA_SEQUENCE]\n", argv[0]);
        return 1;
    }
    if (argc == 2) {
        sequence = argv[1];
    }
    sequence_length = strlen(sequence);
    for (index = 0U; index < sequence_length; ++index) {
        uint64_t code = UINT64_C(0);
        if (!base_code(sequence[index], &code)) {
            fprintf(stderr, "invalid DNA base at offset %zu: expected A/C/G/T\n",
                    index);
            return 1;
        }
    }
    if (sequence_length < K) {
        fprintf(stderr, "sequence must contain at least %d bases\n", K);
        return 1;
    }
    kmer_count = sequence_length - K + 1U;
    if (kmer_count > SIZE_MAX / sizeof(*mapped)) {
        fputs("sequence is too long\n", stderr);
        return 1;
    }
    mapped = malloc(kmer_count * sizeof(*mapped));
    if (mapped == NULL) {
        fputs("score allocation failed\n", stderr);
        return 1;
    }

    if (kssd_array_init(&context, K, KSSD_ARRAY_DEFAULT_SEED) !=
        KSSD_ARRAY_OK) {
        fputs("context initialization failed\n", stderr);
        free(mapped);
        return 1;
    }

    for (index = 0U; index < sequence_length; ++index) {
        uint64_t code = UINT64_C(0);
        /* The complete sequence was validated before scoring. */
        (void)base_code(sequence[index], &code);
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
    free(mapped);
    return 0;
}
