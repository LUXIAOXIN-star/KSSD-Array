/* Independent forward-only benchmark context; frozen core is unchanged. */
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include "kssd_array.h"

void *sd_kssd_create(size_t k)
{
    if (k != 21 && k != 31) return NULL;
    kssd_array_t *ctx = calloc(1, sizeof(*ctx));
    if (ctx == NULL) return NULL;
    if (kssd_array_init(ctx, k, UINT64_C(42)) != KSSD_ARRAY_OK) {
        kssd_array_destroy(ctx);
        free(ctx);
        return NULL;
    }
    return ctx;
}

void sd_kssd_destroy(void *opaque)
{
    kssd_array_t *ctx = opaque;
    if (ctx != NULL) {
        kssd_array_destroy(ctx);
        free(ctx);
    }
}

int sd_kssd_reference(const void *opaque, uint64_t word, uint64_t *score)
{
    return kssd_array_map((const kssd_array_t *)opaque, word, score);
}

/* Retained allocated u16 table payload only, not context/allocator/setup peak.
 * The master table appears in exactly its own segment-length slot, so it is
 * counted once. The frozen API returns NULL/zero for absent segment lengths. */
size_t sd_kssd_table_bytes(const void *opaque)
{
    const kssd_array_t *ctx = opaque;
    if (ctx == NULL) return 0;
    size_t total = 0;
    for (size_t s = 1; s <= KSSD_ARRAY_SEGMENT_CAP; ++s) {
        size_t count = 0;
        const uint16_t *table = kssd_array_permutation(ctx, s, &count);
        if (table != NULL) total += count * sizeof(*table);
    }
    return total;
}
