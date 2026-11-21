#include <stdint.h>

#include <kssd_array.h>

int main(void)
{
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    uint64_t mapped = 0;
    int failed = 0;

    if (kssd_array_init(&context, 9, KSSD_ARRAY_DEFAULT_SEED) !=
        KSSD_ARRAY_OK) {
        return 1;
    }
    failed = kssd_array_map(&context, UINT64_C(0x12345), &mapped) !=
             KSSD_ARRAY_OK;
    kssd_array_destroy(&context);
    return failed;
}
