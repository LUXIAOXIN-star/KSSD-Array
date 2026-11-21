#include <stdlib.h>
#include "kssd_array.h"

void *review_context_create(size_t k, uint64_t seed) {
    kssd_array_t *ctx = calloc(1, sizeof(*ctx));
    if (!ctx) return NULL;
    if (kssd_array_init(ctx, k, seed) != KSSD_ARRAY_OK) {
        kssd_array_destroy(ctx);
        free(ctx);
        return NULL;
    }
    return ctx;
}

void review_context_destroy(void *opaque) {
    kssd_array_t *ctx = opaque;
    if (ctx) { kssd_array_destroy(ctx); free(ctx); }
}

int review_reference_map(const void *opaque, uint64_t word, uint64_t *score) {
    return kssd_array_map(opaque, word, score);
}

uint64_t review_table_checksum(const void *opaque) {
    const kssd_array_t *ctx = opaque;
    uint64_t h = UINT64_C(14695981039346656037);
    for (size_t s = 1; s <= KSSD_ARRAY_SEGMENT_CAP; ++s) {
        size_t count = 0;
        const uint16_t *table = kssd_array_permutation(ctx, s, &count);
        for (size_t i = 0; i < count; ++i) {
            h = (h ^ (table[i] & 255)) * UINT64_C(1099511628211);
            h = (h ^ (table[i] >> 8)) * UINT64_C(1099511628211);
        }
    }
    return h;
}
