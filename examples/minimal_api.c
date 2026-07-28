#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <kssd_array.h>

static int encode_kmer(const char *sequence, size_t k, uint64_t *encoded)
{
    uint64_t value = UINT64_C(0);
    size_t index;

    if (sequence == NULL || encoded == NULL || strlen(sequence) != k) {
        return 0;
    }
    for (index = 0U; index < k; ++index) {
        uint64_t code;
        switch (sequence[index]) {
        case 'A':
            code = UINT64_C(0);
            break;
        case 'C':
            code = UINT64_C(1);
            break;
        case 'G':
            code = UINT64_C(2);
            break;
        case 'T':
            code = UINT64_C(3);
            break;
        default:
            return 0;
        }
        value = (value << 2U) | code;
    }
    *encoded = value;
    return 1;
}

int main(void)
{
    static const char sequence[] = "ACGTACGTAC";
    const size_t k = sizeof(sequence) - 1U;
    const uint64_t seed = KSSD_ARRAY_DEFAULT_SEED;
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    uint64_t encoded = UINT64_C(0);
    uint64_t mapped = UINT64_C(0);
    uint64_t domain_size;
    kssd_array_status_t status;

    if (!encode_kmer(sequence, k, &encoded)) {
        fputs("input must contain exactly k uppercase A/C/G/T bases\n", stderr);
        return 1;
    }

    status = kssd_array_init(&context, k, seed);
    if (status != KSSD_ARRAY_OK) {
        fprintf(stderr, "initialization failed: %s\n",
                kssd_array_status_string(status));
        return 1;
    }

    status = kssd_array_map(&context, encoded, &mapped);
    if (status != KSSD_ARRAY_OK) {
        fprintf(stderr, "mapping failed: %s\n",
                kssd_array_status_string(status));
        kssd_array_destroy(&context);
        return 1;
    }

    domain_size = UINT64_C(1) << (2U * k);
    printf("sequence: %s\n", sequence);
    printf("k: %zu\n", k);
    printf("seed: %" PRIu64 "\n", seed);
    printf("encoded: 0x%" PRIx64 "\n", encoded);
    printf("mapped: %" PRIu64 "\n", mapped);
    printf("output width: %zu bits\n", 2U * k);
    printf("output domain: [0, %" PRIu64 ")\n", domain_size);

    kssd_array_destroy(&context);
    return 0;
}
