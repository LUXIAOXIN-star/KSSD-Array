/* Compile separately for KSSD_ARRAY_FIXED_K=21 and =31.
 * The caller supplies validated uppercase A/C/G/T and allocated u64 output.
 * Only the forward encoded k-mer is mapped. No reverse complement, score
 * truncation, permutation modification, per-key FFI, or prototype kernel. */
#include <stddef.h>
#include <stdint.h>
#include "kssd_array_fast.h"

#if KSSD_ARRAY_FIXED_K != 21 && KSSD_ARRAY_FIXED_K != 31
#error "This independent driver supports fixed k21 and k31 only"
#endif
#define SD_JOIN_INNER(a, b) a##b
#define SD_JOIN(a, b) SD_JOIN_INNER(a, b)
#define SD_K KSSD_ARRAY_FIXED_K
#define SD_SCORE_FN SD_JOIN(sd_kssd_scores_, SD_K)

static inline uint64_t sd_base_code(uint8_t c)
{
    return c == 'C' ? UINT64_C(1) : c == 'G' ? UINT64_C(2) :
           c == 'T' ? UINT64_C(3) : UINT64_C(0);
}

size_t SD_SCORE_FN(const void *opaque, const uint8_t *dna, size_t n,
                   uint64_t *out, size_t capacity)
{
    const kssd_array_t *ctx = opaque;
    if (ctx == NULL || ctx->layout.k != SD_K) return SIZE_MAX;
    if (n < SD_K) return 0;
    if (dna == NULL || out == NULL || capacity < n - SD_K + 1) return SIZE_MAX;
    const uint64_t mask = (UINT64_C(1) << (2 * SD_K)) - UINT64_C(1);
    uint64_t forward = 0;
    for (size_t i = 0; i < SD_K - 1; ++i)
        forward = (forward << 2) | sd_base_code(dna[i]);
    for (size_t i = SD_K - 1; i < n; ++i) {
        forward = ((forward << 2) | sd_base_code(dna[i])) & mask;
        out[i - SD_K + 1] = kssd_array_fast_with_tables(forward, ctx);
    }
    return n - SD_K + 1;
}
