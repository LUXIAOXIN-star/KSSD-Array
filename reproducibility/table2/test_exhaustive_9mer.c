#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <kssd_array.h>

enum {
    METHOD_RANK_DERIVED = 0,
    METHOD_LOW_BIT_MASK,
    METHOD_DIRECT_OLD,
    METHOD_COUNT
};

enum {
    TABLE2_K = 9,
    TABLE2_TOTAL_INPUTS = 262144
};

typedef struct {
    const char *method;
    uint64_t total_inputs;
    uint64_t unique_outputs;
    uint64_t collisions;
    double collision_rate;
    uint64_t min_output;
    uint64_t max_output;
    uint64_t outputs_outside_domain;
} exhaustive_stats_t;

static int compare_uint64_numeric(const void *left, const void *right)
{
    const uint64_t a = *(const uint64_t *)left;
    const uint64_t b = *(const uint64_t *)right;
    return (a > b) - (a < b);
}

static uint64_t pow4(size_t bases)
{
    return UINT64_C(1) << (2U * bases);
}

/*
 * This intentionally lossy Table 2 ablation masks selected master values
 * instead of using rank-derived short permutations. It is not a library API.
 */
static uint64_t ablation_low_bit_mask_map(const kssd_array_t *context,
                                          uint64_t encoded_kmer)
{
    uint64_t result = UINT64_C(0);
    const uint16_t *master = context->master_permutation;
    const size_t master_length = context->layout.master_length;
    size_t consumed = 0U;
    size_t segment_index;

    for (segment_index = 0U;
         segment_index < context->layout.segment_count;
         ++segment_index) {
        const size_t segment_length =
            context->layout.segment_lengths[segment_index];
        const size_t remaining =
            context->layout.k - consumed - segment_length;
        const size_t output_shift = 2U * remaining;
        const uint64_t input_mask = pow4(segment_length) - UINT64_C(1);
        const size_t part =
            (size_t)((encoded_kmer >> output_shift) & input_mask);
        uint16_t mapped;

        if (segment_length == master_length) {
            mapped = master[part];
        } else {
            const size_t padded =
                part << (2U * (master_length - segment_length));
            const uint16_t mask =
                (uint16_t)(pow4(segment_length) - UINT64_C(1));
            mapped = (uint16_t)(master[padded] & mask);
        }
        result |= (uint64_t)mapped << output_shift;
        consumed += segment_length;
    }
    return result;
}

/*
 * This intentionally incorrect historical Table 2 ablation indexes the master
 * table directly for short segments. It is not a library API.
 */
static uint64_t ablation_direct_old_map(const kssd_array_t *context,
                                        uint64_t encoded_kmer)
{
    uint64_t result = UINT64_C(0);
    size_t consumed = 0U;
    size_t segment_index;

    for (segment_index = 0U;
         segment_index < context->layout.segment_count;
         ++segment_index) {
        const size_t segment_length =
            context->layout.segment_lengths[segment_index];
        const size_t remaining =
            context->layout.k - consumed - segment_length;
        const size_t output_shift = 2U * remaining;
        const uint64_t input_mask = pow4(segment_length) - UINT64_C(1);
        const size_t part =
            (size_t)((encoded_kmer >> output_shift) & input_mask);
        const uint16_t mapped = context->master_permutation[part];

        result |= (uint64_t)mapped << output_shift;
        consumed += segment_length;
    }
    return result;
}

static uint64_t map_method(const kssd_array_t *context,
                           uint64_t encoded_kmer,
                           int method)
{
    if (method == METHOD_RANK_DERIVED) {
        return kssd_array_map_unchecked(context, encoded_kmer);
    }
    if (method == METHOD_LOW_BIT_MASK) {
        return ablation_low_bit_mask_map(context, encoded_kmer);
    }
    return ablation_direct_old_map(context, encoded_kmer);
}

static int collect_stats(const kssd_array_t *context,
                         int method,
                         size_t input_count,
                         exhaustive_stats_t *stats)
{
    const uint64_t domain_max = pow4(context->layout.k) - UINT64_C(1);
    uint64_t *outputs;
    size_t input;
    size_t unique;

    if (stats == NULL || input_count == 0U) {
        return 0;
    }
    outputs = (uint64_t *)malloc(input_count * sizeof(*outputs));
    if (outputs == NULL) {
        return 0;
    }

    stats->total_inputs = (uint64_t)input_count;
    stats->min_output = UINT64_MAX;
    stats->max_output = UINT64_C(0);
    stats->outputs_outside_domain = UINT64_C(0);

    for (input = 0U; input < input_count; ++input) {
        const uint64_t output =
            map_method(context, (uint64_t)input, method);
        outputs[input] = output;
        if (output < stats->min_output) {
            stats->min_output = output;
        }
        if (output > stats->max_output) {
            stats->max_output = output;
        }
        if (output > domain_max) {
            ++stats->outputs_outside_domain;
        }
    }

    qsort(outputs, input_count, sizeof(*outputs), compare_uint64_numeric);
    unique = 1U;
    for (input = 1U; input < input_count; ++input) {
        if (outputs[input] != outputs[input - 1U]) {
            ++unique;
        }
    }
    free(outputs);

    stats->unique_outputs = (uint64_t)unique;
    stats->collisions = stats->total_inputs - stats->unique_outputs;
    stats->collision_rate =
        (double)stats->collisions / (double)stats->total_inputs;
    return 1;
}

static int write_csv(const char *path,
                     const exhaustive_stats_t stats[METHOD_COUNT])
{
    FILE *output = fopen(path, "w");
    int method;

    if (output == NULL) {
        fprintf(stderr, "cannot open CSV output: %s\n", path);
        return 0;
    }
    fprintf(output,
            "method,total_inputs,unique_outputs,collisions,collision_rate,"
            "min_output,max_output,outputs_outside_2k_domain\n");
    for (method = 0; method < METHOD_COUNT; ++method) {
        fprintf(output,
                "%s,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%.8f,%" PRIu64
                ",%" PRIu64 ",%" PRIu64 "\n",
                stats[method].method,
                stats[method].total_inputs,
                stats[method].unique_outputs,
                stats[method].collisions,
                stats[method].collision_rate,
                stats[method].min_output,
                stats[method].max_output,
                stats[method].outputs_outside_domain);
    }
    if (fclose(output) != 0) {
        fprintf(stderr, "cannot close CSV output: %s\n", path);
        return 0;
    }
    return 1;
}

static int verify_expected(const exhaustive_stats_t stats[METHOD_COUNT])
{
    const uint64_t expected_unique[METHOD_COUNT] = {
        UINT64_C(262144), UINT64_C(183296), UINT64_C(117760)};
    const uint64_t expected_collisions[METHOD_COUNT] = {
        UINT64_C(0), UINT64_C(78848), UINT64_C(144384)};
    int method;

    for (method = 0; method < METHOD_COUNT; ++method) {
        if (stats[method].total_inputs != UINT64_C(262144) ||
            stats[method].unique_outputs != expected_unique[method] ||
            stats[method].collisions != expected_collisions[method] ||
            stats[method].min_output != UINT64_C(0) ||
            stats[method].max_output != UINT64_C(262143) ||
            stats[method].outputs_outside_domain != UINT64_C(0)) {
            fprintf(stderr,
                    "unexpected exhaustive result for %s: total=%" PRIu64
                    " unique=%" PRIu64 " collisions=%" PRIu64
                    " range=[%" PRIu64 ",%" PRIu64 "] outside=%" PRIu64
                    "\n",
                    stats[method].method,
                    stats[method].total_inputs,
                    stats[method].unique_outputs,
                    stats[method].collisions,
                    stats[method].min_output,
                    stats[method].max_output,
                    stats[method].outputs_outside_domain);
            return 0;
        }
    }
    return 1;
}

static int parse_input_count(const char *text, size_t *input_count)
{
    char *end = NULL;
    unsigned long long value;

    errno = 0;
    value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value == 0ULL ||
        value > (unsigned long long)TABLE2_TOTAL_INPUTS) {
        return 0;
    }
    *input_count = (size_t)value;
    return 1;
}

int main(int argc, char **argv)
{
    static const char *method_names[METHOD_COUNT] = {
        "rank-derived", "low-bit-mask", "direct-old"};
    kssd_array_t context = KSSD_ARRAY_CONTEXT_INIT;
    exhaustive_stats_t stats[METHOD_COUNT];
    const char *csv_path = NULL;
    size_t input_count = (size_t)TABLE2_TOTAL_INPUTS;
    int argument;
    int method;
    int ok = 1;

    for (argument = 1; argument < argc; ++argument) {
        if (strcmp(argv[argument], "--csv") == 0 && argument + 1 < argc) {
            csv_path = argv[++argument];
        } else if (strcmp(argv[argument], "--limit") == 0 &&
                   argument + 1 < argc &&
                   parse_input_count(argv[argument + 1], &input_count)) {
            ++argument;
        } else {
            fprintf(stderr,
                    "usage: %s [--csv PATH] [--limit INPUT_COUNT]\n",
                    argv[0]);
            return EXIT_FAILURE;
        }
    }

    if (kssd_array_init(&context,
                        (size_t)TABLE2_K,
                        KSSD_ARRAY_DEFAULT_SEED) != KSSD_ARRAY_OK) {
        fputs("failed to initialize KSSD-Array for k=9\n", stderr);
        return EXIT_FAILURE;
    }

    memset(stats, 0, sizeof(stats));
    for (method = 0; method < METHOD_COUNT; ++method) {
        stats[method].method = method_names[method];
        if (!collect_stats(&context, method, input_count, &stats[method])) {
            fprintf(stderr, "failed to collect statistics for %s\n",
                    method_names[method]);
            ok = 0;
            break;
        }
        printf("%s: total=%" PRIu64 " unique=%" PRIu64
               " collisions=%" PRIu64 " rate=%.6f%% min=%" PRIu64
               " max=%" PRIu64 " outside=%" PRIu64 "\n",
               stats[method].method,
               stats[method].total_inputs,
               stats[method].unique_outputs,
               stats[method].collisions,
               stats[method].collision_rate * 100.0,
               stats[method].min_output,
               stats[method].max_output,
               stats[method].outputs_outside_domain);
    }

    if (ok && input_count == (size_t)TABLE2_TOTAL_INPUTS &&
        !verify_expected(stats)) {
        ok = 0;
    }
    if (ok && input_count != (size_t)TABLE2_TOTAL_INPUTS) {
        puts("smoke mode: manuscript counts were not asserted");
    }
    if (ok && csv_path != NULL && !write_csv(csv_path, stats)) {
        ok = 0;
    }

    kssd_array_destroy(&context);
    if (ok) {
        puts(input_count == (size_t)TABLE2_TOTAL_INPUTS
                 ? "exhaustive 9-mer validation: PASS"
                 : "9-mer smoke validation: PASS");
    }
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
