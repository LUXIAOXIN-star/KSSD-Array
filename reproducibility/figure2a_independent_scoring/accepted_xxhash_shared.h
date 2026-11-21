#ifndef PHASE1_ACCEPTED_XXHASH_SHARED_H
#define PHASE1_ACCEPTED_XXHASH_SHARED_H

#include <stddef.h>
#include <stdint.h>

/* Direct aliases preserve the accepted one-PLT-call loop boundary. */
uint64_t phase1_accepted_xxh3_shared_direct(
    const void *input, size_t length, uint64_t seed)
    __asm__("XXH3_64bits_withSeed");
uint64_t phase1_accepted_xxh64_shared_direct(
    const void *input, size_t length, uint64_t seed)
    __asm__("XXH64");
unsigned phase1_accepted_xxhash_version_direct(void)
    __asm__("XXH_versionNumber");

#endif
