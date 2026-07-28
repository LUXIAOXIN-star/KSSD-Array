#ifndef KSSD_ARRAY_PERMUTATION_H
#define KSSD_ARRAY_PERMUTATION_H

#include <stddef.h>
#include <stdint.h>

#include "kssd_array.h"

kssd_array_status_t kssd_array_pow4(size_t segment_length, size_t *result);

kssd_array_status_t kssd_array_build_master(uint16_t **master,
                                            size_t *master_size,
                                            size_t master_length,
                                            uint64_t seed,
                                            kssd_array_rng_t rng);

kssd_array_status_t kssd_array_derive_permutation(const uint16_t *master,
                                                  size_t master_length,
                                                  size_t segment_length,
                                                  uint16_t **derived,
                                                  size_t *derived_size);

#endif
