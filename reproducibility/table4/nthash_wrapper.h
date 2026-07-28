#ifndef TABLE4_NTHASH_WRAPPER_H
#define TABLE4_NTHASH_WRAPPER_H

#include <stddef.h>
#include <stdint.h>

/*
 * The opaque handle owns one nthash::NtHash instance. The caller keeps the
 * sequence buffer alive until table4_nthash_destroy() and must call roll
 * successfully before reading the current hash.
 */
typedef struct table4_nthash_handle table4_nthash_handle_t;

table4_nthash_handle_t *table4_nthash_create(const char *sequence,
                                             size_t sequence_length,
                                             unsigned k);
void table4_nthash_destroy(table4_nthash_handle_t *handle);
int table4_nthash_roll(table4_nthash_handle_t *handle);
uint64_t table4_nthash_current(const table4_nthash_handle_t *handle);

#endif
