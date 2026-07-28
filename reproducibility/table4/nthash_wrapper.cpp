#include "nthash_wrapper.h"

#include <nthash/nthash.hpp>

#include <new>

struct table4_nthash_handle {
    nthash::NtHash value;

    table4_nthash_handle(const char *sequence,
                         size_t sequence_length,
                         unsigned k)
        : value(sequence, sequence_length, 1U,
                static_cast<nthash::typedefs::K_TYPE>(k)) {}
};

table4_nthash_handle_t *table4_nthash_create(const char *sequence,
                                             size_t sequence_length,
                                             unsigned k) {
    if (sequence == nullptr || k == 0U || k > 32U ||
        sequence_length < static_cast<size_t>(k)) {
        return nullptr;
    }
    return new (std::nothrow) table4_nthash_handle(sequence, sequence_length,
                                                   k);
}

void table4_nthash_destroy(table4_nthash_handle_t *handle) {
    delete handle;
}

int table4_nthash_roll(table4_nthash_handle_t *handle) {
    return handle != nullptr && handle->value.roll() ? 1 : 0;
}

uint64_t table4_nthash_current(const table4_nthash_handle_t *handle) {
    return handle->value.hashes()[0];
}
