#include <stdio.h>
#include <stdlib.h>

#include "minimap.h"
#include "mmpriv.h"

mm_idx_t *mm_idx_init(int w, int k, int b, int flag);

int main(void)
{
    static const char ambiguous[] = "ACGTACGTNACGTACGT";
    static const char joined[] = "ACGTACGTACGTACGT";
    mm128_v ambiguous_values = {0, 0, NULL};
    mm128_v joined_values = {0, 0, NULL};
    mm_idx_t *index = mm_idx_init(1, 9, 8, 0);

    if (index == NULL) {
        fputs("cannot initialize index context\n", stderr);
        return EXIT_FAILURE;
    }
    mm_sketch(NULL, ambiguous, (int)(sizeof(ambiguous) - 1U),
              1, 9, 0, 0, index->kssd_array, &ambiguous_values);
    mm_sketch(NULL, joined, (int)(sizeof(joined) - 1U),
              1, 9, 0, 0, index->kssd_array, &joined_values);
    printf("AMBIGUOUS_MINIMIZERS=%zu\n", ambiguous_values.n);
    printf("JOINED_MINIMIZERS=%zu\n", joined_values.n);

    free(ambiguous_values.a);
    free(joined_values.a);
    mm_idx_destroy(index);
    return ambiguous_values.n == 0U && joined_values.n > 0U
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
