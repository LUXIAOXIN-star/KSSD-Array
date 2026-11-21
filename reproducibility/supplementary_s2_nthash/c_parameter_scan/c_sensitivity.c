#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <kssd_array.h>

#ifndef K
#define K 21
#endif
#ifndef SEGMENT_CAP
#define SEGMENT_CAP 8
#endif
#if K < 1 || K > 32 || SEGMENT_CAP < 1 || SEGMENT_CAP > 8
#error "invalid K or SEGMENT_CAP"
#endif

#define MAX_SEGMENTS 8U
#define MAX_LENGTH 8U
#if K == 32
#define DOMAIN_MASK UINT64_MAX
#else
#define DOMAIN_MASK ((UINT64_C(1) << (2U * K)) - UINT64_C(1))
#endif

typedef struct { uint16_t value; uint16_t index; } rank_pair_t;

typedef struct {
    size_t segment_count;
    size_t lengths[MAX_SEGMENTS];
    size_t master_length;
    uint16_t *tables[MAX_LENGTH + 1U];
    size_t sizes[MAX_LENGTH + 1U];
    size_t master_bytes;
    size_t derived_bytes;
    size_t persistent_bytes;
    size_t cumulative_allocated_bytes;
    size_t peak_live_bytes;
} cap_context_t;

typedef struct {
    uint64_t allocation_ns;
    uint64_t master_generation_ns;
    uint64_t derived_construction_ns;
    uint64_t total_ns;
} init_timing_t;

typedef struct {
    uint64_t *values;
    size_t count;
    size_t valid_bases;
    size_t ambiguous_bases;
    uint64_t checksum;
} encoded_input_t;

typedef struct {
    double seconds;
    uint64_t tsc_cycles;
    uint64_t checksum;
    size_t count;
} timing_t;

typedef struct {
    timing_t timing;
    uint64_t position_checksum;
    uint64_t score_checksum;
    size_t selected;
} window_t;

static volatile uint64_t phase3_sink;

static uint64_t monotonic_ns(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) +
           (uint64_t)value.tv_nsec;
}

static uint64_t read_tsc_begin(void) {
#if defined(__x86_64__) || defined(__i386__)
    unsigned low, high;
    __asm__ volatile("lfence\n\trdtsc" : "=a"(low), "=d"(high) :: "memory");
    return ((uint64_t)high << 32U) | low;
#else
    return 0;
#endif
}

static uint64_t read_tsc_end(void) {
#if defined(__x86_64__) || defined(__i386__)
    unsigned low, high, auxiliary;
    __asm__ volatile("rdtscp\n\tlfence" : "=a"(low), "=d"(high), "=c"(auxiliary) :: "memory");
    (void)auxiliary;
    return ((uint64_t)high << 32U) | low;
#else
    return 0;
#endif
}

static uint64_t splitmix_value(uint64_t value) {
    value = (value ^ (value >> 30U)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27U)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31U);
}

static uint64_t splitmix_next(uint64_t *state) {
    *state += UINT64_C(0x9e3779b97f4a7c15);
    return splitmix_value(*state);
}

static int compare_pair(const void *left, const void *right) {
    const rank_pair_t *a = (const rank_pair_t *)left;
    const rank_pair_t *b = (const rank_pair_t *)right;
    if (a->value != b->value) return (a->value > b->value) - (a->value < b->value);
    return (a->index > b->index) - (a->index < b->index);
}

static size_t pow4_size(size_t length) { return (size_t)1U << (2U * length); }

static void layout_context(cap_context_t *context) {
    size_t quotient, remainder, index;
    context->segment_count = ((size_t)K + SEGMENT_CAP - 1U) / SEGMENT_CAP;
    quotient = (size_t)K / context->segment_count;
    remainder = (size_t)K % context->segment_count;
    for (index = 0; index < context->segment_count; ++index)
        context->lengths[index] = quotient + (index < remainder ? 1U : 0U);
    context->master_length = context->lengths[0];
}

static void *timed_malloc(size_t bytes, init_timing_t *timing) {
    const uint64_t start = monotonic_ns();
    void *memory = malloc(bytes);
    timing->allocation_ns += monotonic_ns() - start;
    return memory;
}

static int initialize_context(cap_context_t *context, init_timing_t *timing) {
    const uint64_t total_start = monotonic_ns();
    uint64_t rng = UINT64_C(42);
    size_t live = 0, index, length;
    memset(context, 0, sizeof(*context));
    memset(timing, 0, sizeof(*timing));
    layout_context(context);
    {
        const size_t size = pow4_size(context->master_length);
        const size_t bytes = size * sizeof(uint16_t);
        uint16_t *master = (uint16_t *)timed_malloc(bytes, timing);
        uint64_t start;
        if (master == NULL) return 0;
        context->tables[context->master_length] = master;
        context->sizes[context->master_length] = size;
        context->master_bytes = bytes;
        context->persistent_bytes = bytes;
        context->cumulative_allocated_bytes = bytes;
        live = bytes;
        context->peak_live_bytes = live;
        start = monotonic_ns();
        for (index = 0; index < size; ++index) master[index] = (uint16_t)index;
        for (index = size - 1U; index > 0U; --index) {
            const size_t selected = (size_t)(splitmix_next(&rng) % (uint64_t)(index + 1U));
            const uint16_t temporary = master[index];
            master[index] = master[selected];
            master[selected] = temporary;
        }
        timing->master_generation_ns = monotonic_ns() - start;
    }
    for (length = 1U; length < context->master_length; ++length) {
        const size_t size = pow4_size(length);
        const size_t pair_bytes = size * sizeof(rank_pair_t);
        const size_t table_bytes = size * sizeof(uint16_t);
        rank_pair_t *pairs = (rank_pair_t *)timed_malloc(pair_bytes, timing);
        uint16_t *table = (uint16_t *)timed_malloc(table_bytes, timing);
        uint64_t start;
        if (pairs == NULL || table == NULL) {
            free(pairs); free(table); return 0;
        }
        context->cumulative_allocated_bytes += pair_bytes + table_bytes;
        if (live + pair_bytes + table_bytes > context->peak_live_bytes)
            context->peak_live_bytes = live + pair_bytes + table_bytes;
        start = monotonic_ns();
        for (index = 0; index < size; ++index) {
            pairs[index].value = context->tables[context->master_length]
                [index << (2U * (context->master_length - length))];
            pairs[index].index = (uint16_t)index;
        }
        qsort(pairs, size, sizeof(*pairs), compare_pair);
        for (index = 0; index < size; ++index)
            table[pairs[index].index] = (uint16_t)index;
        timing->derived_construction_ns += monotonic_ns() - start;
        free(pairs);
        context->tables[length] = table;
        context->sizes[length] = size;
        context->derived_bytes += table_bytes;
        context->persistent_bytes += table_bytes;
        live += table_bytes;
    }
    timing->total_ns = monotonic_ns() - total_start;
    return 1;
}

static void destroy_context(cap_context_t *context) {
    size_t length;
    for (length = 1U; length <= context->master_length; ++length)
        free(context->tables[length]);
    memset(context, 0, sizeof(*context));
}

#if defined(__GNUC__) || defined(__clang__)
__attribute__((always_inline))
#endif
static inline uint64_t map_cap(uint64_t key, const cap_context_t *context) {
    const size_t segment_count = ((size_t)K + SEGMENT_CAP - 1U) / SEGMENT_CAP;
    const size_t quotient = (size_t)K / segment_count;
    const size_t remainder = (size_t)K % segment_count;
    size_t consumed = 0, segment_index;
    uint64_t result = 0;
    for (segment_index = 0; segment_index < segment_count; ++segment_index) {
        const size_t length = quotient + (segment_index < remainder ? 1U : 0U);
        const size_t remaining = (size_t)K - consumed - length;
        const size_t width = 2U * length;
        const uint64_t mask = (UINT64_C(1) << width) - 1U;
        const uint64_t segment = (key >> (2U * remaining)) & mask;
        result = (result << width) | context->tables[length][(size_t)segment];
        consumed += length;
    }
    return result;
}

static int validate_context(const cap_context_t *context) {
    size_t length, index;
    for (length = 1U; length <= context->master_length; ++length) {
        const size_t size = context->sizes[length];
        unsigned char *seen = (unsigned char *)calloc(size, 1U);
        if (seen == NULL) return 0;
        for (index = 0; index < size; ++index) {
            const uint16_t value = context->tables[length][index];
            if ((size_t)value >= size || seen[value] != 0) { free(seen); return 0; }
            seen[value] = 1;
        }
        free(seen);
    }
#if SEGMENT_CAP == 8
    {
        kssd_array_t public_context = KSSD_ARRAY_CONTEXT_INIT;
        if (kssd_array_init(&public_context, K, UINT64_C(42)) != KSSD_ARRAY_OK) return 0;
        for (length = 1U; length <= context->master_length; ++length) {
            size_t public_size = 0;
            const uint16_t *public_table = kssd_array_permutation(&public_context, length, &public_size);
            if (public_size != context->sizes[length] ||
                memcmp(public_table, context->tables[length], public_size * sizeof(uint16_t)) != 0) {
                kssd_array_destroy(&public_context); return 0;
            }
        }
        for (index = 0; index < 100000U; ++index) {
            const uint64_t key = splitmix_value((uint64_t)index) & DOMAIN_MASK;
            if (map_cap(key, context) != kssd_array_map_unchecked(&public_context, key)) {
                kssd_array_destroy(&public_context); return 0;
            }
        }
        kssd_array_destroy(&public_context);
    }
#endif
    return 1;
}

static int base_code(int character, uint8_t *code) {
    switch (character) {
    case 'A': case 'a': *code = 0; return 1;
    case 'C': case 'c': *code = 1; return 1;
    case 'G': case 'g': *code = 2; return 1;
    case 'T': case 't': *code = 3; return 1;
    default: return 0;
    }
}

static int read_input(const char *path, encoded_input_t *input) {
    FILE *file = fopen(path, "rb");
    uint64_t rolling = 0;
    size_t rolling_bases = 0, capacity = 1U << 20U;
    int line_start = 1, header = 0, found = 0, character;
    memset(input, 0, sizeof(*input));
    if (file == NULL) return 0;
    input->values = (uint64_t *)malloc(capacity * sizeof(uint64_t));
    if (input->values == NULL) { fclose(file); return 0; }
    setvbuf(file, NULL, _IOFBF, 1U << 20U);
    while ((character = fgetc(file)) != EOF) {
        if (line_start && character == '>') {
            if (found) break;
            found = 1; header = 1; line_start = 0; continue;
        }
        if (character == '\n' || character == '\r') {
            line_start = 1; header = 0; continue;
        }
        line_start = 0;
        if (!found || header) continue;
        {
            uint8_t code;
            if (!base_code(character, &code)) { ++input->ambiguous_bases; continue; }
            ++input->valid_bases;
            ++rolling_bases;
            rolling = ((rolling << 2U) | code) & DOMAIN_MASK;
            if (rolling_bases >= (size_t)K) {
                if (input->count == capacity) {
                    uint64_t *grown;
                    capacity *= 2U;
                    grown = (uint64_t *)realloc(input->values, capacity * sizeof(uint64_t));
                    if (grown == NULL) { fclose(file); free(input->values); return 0; }
                    input->values = grown;
                }
                input->values[input->count] = rolling;
                input->checksum ^= splitmix_value(rolling ^
                    ((uint64_t)input->count * UINT64_C(0x9e3779b97f4a7c15)));
                ++input->count;
            }
        }
    }
    fclose(file);
    return found && input->count > 0;
}

static timing_t score_loop(const encoded_input_t *input,
                           const cap_context_t *context,
                           uint64_t *output) {
    size_t index;
    uint64_t checksum = 0;
    const uint64_t tsc_start = read_tsc_begin();
    const uint64_t wall_start = monotonic_ns();
    for (index = 0; index < input->count; ++index) {
        const uint64_t score = map_cap(input->values[index], context);
        if (output != NULL) output[index] = score;
        checksum ^= splitmix_value(score ^
            ((uint64_t)index * UINT64_C(0x9e3779b97f4a7c15)));
    }
    {
        const uint64_t wall_end = monotonic_ns();
        const uint64_t tsc_end = read_tsc_end();
        timing_t result = {(double)(wall_end - wall_start) / 1.0e9,
                           tsc_end - tsc_start, checksum, input->count};
        phase3_sink ^= checksum;
        return result;
    }
}

static window_t window_loop(const uint64_t *scores, size_t count,
                            size_t width, size_t *deque) {
    window_t result;
    size_t front = 0, back = 0, index;
    uint64_t wall_start, wall_end, tsc_start, tsc_end;
    memset(&result, 0, sizeof(result));
    tsc_start = read_tsc_begin(); wall_start = monotonic_ns();
    for (index = 0; index < count; ++index) {
        while (front < back && deque[front] + width <= index) ++front;
        while (front < back && scores[deque[back - 1U]] > scores[index]) --back;
        deque[back++] = index;
        if (index + 1U >= width) {
            const size_t start = index + 1U - width;
            const size_t position = deque[front];
            result.position_checksum ^= splitmix_value((uint64_t)position ^
                ((uint64_t)start * UINT64_C(0xd6e8feb86659fd93)));
            result.score_checksum ^= splitmix_value(scores[position] ^
                ((uint64_t)start * UINT64_C(0x9e3779b97f4a7c15)));
            ++result.selected;
        }
    }
    wall_end = monotonic_ns(); tsc_end = read_tsc_end();
    result.timing.seconds = (double)(wall_end - wall_start) / 1.0e9;
    result.timing.tsc_cycles = tsc_end - tsc_start;
    result.timing.checksum = result.position_checksum ^ result.score_checksum;
    result.timing.count = result.selected;
    phase3_sink ^= result.timing.checksum;
    return result;
}

static int dump_tables(const cap_context_t *context, const char *directory) {
    size_t length;
    for (length = 1U; length <= context->master_length; ++length) {
        char path[4096];
        FILE *file;
        if (snprintf(path, sizeof(path), "%s/K%d_C%d_s%zu.uint16le.bin",
                     directory, K, SEGMENT_CAP, length) >= (int)sizeof(path)) return 0;
        file = fopen(path, "wb");
        if (file == NULL) return 0;
        if (fwrite(context->tables[length], sizeof(uint16_t),
                   context->sizes[length], file) != context->sizes[length] ||
            fclose(file) != 0) return 0;
    }
    return 1;
}

static void print_structure(const cap_context_t *context) {
    size_t index;
    printf("STRUCTURE\t%d\t%d\t%zu\t", K, SEGMENT_CAP, context->segment_count);
    for (index = 0; index < context->segment_count; ++index)
        printf("%s%zu", index == 0 ? "" : ",", context->lengths[index]);
    printf("\t%zu\t%zu\t%zu\t%zu\t%zu\t%zu\t16\n",
           context->segment_count, context->master_length,
           context->master_bytes, context->derived_bytes,
           context->persistent_bytes, context->peak_live_bytes);
}

int main(int argc, char **argv) {
    cap_context_t context;
    init_timing_t initial;
    unsigned repeat;
    if (!initialize_context(&context, &initial) || !validate_context(&context)) {
        fputs("context validation failed\n", stderr); return EXIT_FAILURE;
    }
    printf("VALIDATION\tC_bijection_and_seed_binding\tPASS\t%d\t%d\n", K, SEGMENT_CAP);
    print_structure(&context);
    if (argc >= 2 && strcmp(argv[1], "--init") == 0) {
        const unsigned repeats = argc == 3 ? (unsigned)strtoul(argv[2], NULL, 10) : 10U;
        for (repeat = 1; repeat <= repeats; ++repeat) {
            cap_context_t measured;
            init_timing_t timing;
            if (!initialize_context(&measured, &timing)) return EXIT_FAILURE;
            printf("INIT\t%d\t%d\t%u\t%" PRIu64 "\t%" PRIu64 "\t%" PRIu64
                   "\t%" PRIu64 "\t%zu\t%zu\t%zu\t%zu\t%zu\n",
                   K, SEGMENT_CAP, repeat, timing.allocation_ns,
                   timing.master_generation_ns, timing.derived_construction_ns,
                   timing.total_ns, measured.master_bytes, measured.derived_bytes,
                   measured.persistent_bytes, measured.cumulative_allocated_bytes,
                   measured.peak_live_bytes);
            destroy_context(&measured);
        }
    } else if (argc == 3 && strcmp(argv[1], "--dump-tables") == 0) {
        if (!dump_tables(&context, argv[2])) return EXIT_FAILURE;
    } else if (argc == 5 && strcmp(argv[1], "--run-all") == 0) {
        const char *dataset = argv[3];
        const unsigned repeats = (unsigned)strtoul(argv[4], NULL, 10);
        const size_t widths[] = {10U, 20U, 50U};
        encoded_input_t input;
        uint64_t *scores;
        size_t *deque;
        size_t width_index;
        if (!read_input(argv[2], &input)) return EXIT_FAILURE;
        scores = (uint64_t *)malloc(input.count * sizeof(uint64_t));
        deque = (size_t *)malloc(input.count * sizeof(size_t));
        if (scores == NULL || deque == NULL) return EXIT_FAILURE;
        printf("META\t%s\t%d\t%d\t%zu\t%zu\t%" PRIu64 "\n",
               dataset, K, SEGMENT_CAP, input.valid_bases, input.count, input.checksum);
        (void)score_loop(&input, &context, NULL);
        for (width_index = 0; width_index < 3U; ++width_index) {
            (void)score_loop(&input, &context, scores);
            (void)window_loop(scores, input.count, widths[width_index], deque);
        }
        for (repeat = 1; repeat <= repeats; ++repeat) {
            const timing_t mapping = score_loop(&input, &context, NULL);
            printf("C_MAPPING\t%s\t%d\t%d\t%u\t%zu\t%.12f\t%.9f\t%.9f"
                   "\t%" PRIu64 "\t%.9f\t%016" PRIx64 "\n",
                   dataset, K, SEGMENT_CAP, repeat, input.count,
                   mapping.seconds, mapping.seconds * 1.0e9 / input.count,
                   input.count / mapping.seconds / 1.0e6, mapping.tsc_cycles,
                   (double)mapping.tsc_cycles / input.count, mapping.checksum);
            for (width_index = 0; width_index < 3U; ++width_index) {
                const size_t width = widths[width_index];
                const timing_t score = score_loop(&input, &context, scores);
                const window_t window = window_loop(scores, input.count, width, deque);
                const double total = score.seconds + window.timing.seconds;
                printf("C_NEUTRAL\t%s\t%d\t%d\t%zu\t%u\t%zu\t%zu\t%.12f\t%.12f"
                       "\t%.12f\t%.9f\t%" PRIu64 "\t%" PRIu64 "\t%016" PRIx64
                       "\t%016" PRIx64 "\t%016" PRIx64 "\n",
                       dataset, K, SEGMENT_CAP, width, repeat, input.count,
                       window.selected, score.seconds, window.timing.seconds,
                       total, window.selected / total / 1.0e6,
                       score.tsc_cycles, window.timing.tsc_cycles, score.checksum,
                       window.position_checksum, window.score_checksum);
            }
        }
        free(scores); free(deque); free(input.values);
    } else if (argc == 7 && strcmp(argv[1], "--run") == 0) {
        const char *dataset = argv[3];
        const char *mode = argv[4];
        const size_t width = (size_t)strtoull(argv[5], NULL, 10);
        const unsigned repeats = (unsigned)strtoul(argv[6], NULL, 10);
        encoded_input_t input;
        uint64_t *scores = NULL;
        size_t *deque = NULL;
        if (!read_input(argv[2], &input)) return EXIT_FAILURE;
        printf("META\t%s\t%d\t%d\t%zu\t%zu\t%" PRIu64 "\n",
               dataset, K, SEGMENT_CAP, input.valid_bases, input.count, input.checksum);
        if (strcmp(mode, "mapping") == 0) {
            (void)score_loop(&input, &context, NULL);
            for (repeat = 1; repeat <= repeats; ++repeat) {
                const timing_t timing = score_loop(&input, &context, NULL);
                printf("C_MAPPING\t%s\t%d\t%d\t%u\t%zu\t%.12f\t%.9f\t%.9f"
                       "\t%" PRIu64 "\t%.9f\t%016" PRIx64 "\n",
                       dataset, K, SEGMENT_CAP, repeat, input.count,
                       timing.seconds, timing.seconds * 1.0e9 / input.count,
                       input.count / timing.seconds / 1.0e6, timing.tsc_cycles,
                       (double)timing.tsc_cycles / input.count, timing.checksum);
            }
        } else if (strcmp(mode, "neutral") == 0 && width > 0 && width <= input.count) {
            scores = (uint64_t *)malloc(input.count * sizeof(uint64_t));
            deque = (size_t *)malloc(input.count * sizeof(size_t));
            if (scores == NULL || deque == NULL) return EXIT_FAILURE;
            (void)score_loop(&input, &context, scores);
            (void)window_loop(scores, input.count, width, deque);
            for (repeat = 1; repeat <= repeats; ++repeat) {
                const timing_t score = score_loop(&input, &context, scores);
                const window_t window = window_loop(scores, input.count, width, deque);
                const double total = score.seconds + window.timing.seconds;
                printf("C_NEUTRAL\t%s\t%d\t%d\t%zu\t%u\t%zu\t%zu\t%.12f\t%.12f"
                       "\t%.12f\t%.9f\t%" PRIu64 "\t%" PRIu64 "\t%016" PRIx64
                       "\t%016" PRIx64 "\t%016" PRIx64 "\n",
                       dataset, K, SEGMENT_CAP, width, repeat, input.count,
                       window.selected, score.seconds, window.timing.seconds,
                       total, window.selected / total / 1.0e6,
                       score.tsc_cycles, window.timing.tsc_cycles, score.checksum,
                       window.position_checksum, window.score_checksum);
            }
        } else return EXIT_FAILURE;
        free(scores); free(deque); free(input.values);
    } else {
        fprintf(stderr, "usage: %s --init [N] | --dump-tables DIR | --run-all FASTA DATASET REPEATS | --run FASTA DATASET mapping|neutral W REPEATS\n", argv[0]);
        destroy_context(&context); return EXIT_FAILURE;
    }
    destroy_context(&context);
    return EXIT_SUCCESS;
}
