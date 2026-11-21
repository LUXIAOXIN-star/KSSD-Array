/* Isolated three-method, fixed-k score-only driver.
 * Algorithm/input definitions are included unchanged from frozen Phase 1.
 * Build with function/data sections and --gc-sections: unused original modes
 * are deliberately never entered by this driver.
 */
#define main gx_original_phase1_main
#include "original_phase1/phase1_benchmark.c"
#undef main

#include <sys/stat.h>
#include "gxhash_wrapper/gxhash_wrapper.h"

/* Compiled separately from the same pinned v0.8.3 source without INLINE_ALL. */
extern uint64_t GX_REF_XXH3_64bits(const void *input, size_t length);

#if defined(__GNUC__) || defined(__clang__)
#define GX_NOINLINE __attribute__((noinline))
#else
#define GX_NOINLINE
#endif

#define GX_ALIGNMENT ((size_t)64)
#define GX_PADDING ((size_t)64)
#define GX_VALIDATE_N ((size_t)100003)

typedef struct {
    void *allocation;
    uint64_t *words;
    size_t count;
    size_t bytes;
} gx_words_t;

static void gx_json_string(const char *text)
{
    const unsigned char *p = (const unsigned char *)text;
    putchar('"');
    for (; *p; ++p) {
        if (*p == '"' || *p == '\\') {
            putchar('\\');
            putchar((int)*p);
        } else if (*p < 32U) {
            printf("\\u%04x", (unsigned)*p);
        } else {
            putchar((int)*p);
        }
    }
    putchar('"');
}

static int gx_fail(const char *message)
{
    fputs("{\"status\":\"FAIL\",\"exit_code\":1,\"k\":", stdout);
    printf("%d,\"error\":", K);
    gx_json_string(message);
    fputs("}\n", stdout);
    fprintf(stderr, "score_driver: %s\n", message);
    return EXIT_FAILURE;
}

static int gx_little_endian(void)
{
    const uint64_t word = UINT64_C(1);
    return sizeof(uint64_t) == 8U && *(const unsigned char *)&word == 1U;
}

static int gx_parse_u64(const char *text, uint64_t *value)
{
    char *end = NULL;
    unsigned long long parsed;
    const char *p;
    if (text == NULL || *text == '\0') return 0;
    for (p = text; *p; ++p) if (*p < '0' || *p > '9') return 0;
    errno = 0;
    parsed = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' ||
        parsed > (unsigned long long)UINT64_MAX) return 0;
    *value = (uint64_t)parsed;
    return 1;
}

static int gx_parse_count(const char *text, size_t *value)
{
    uint64_t parsed;
    if (!gx_parse_u64(text, &parsed) || parsed > (uint64_t)SIZE_MAX) return 0;
    *value = (size_t)parsed;
    return 1;
}

static int gx_allocate_words(gx_words_t *buffer, size_t count)
{
    size_t total;
    memset(buffer, 0, sizeof(*buffer));
    if (count > (SIZE_MAX - 2U * GX_PADDING) / sizeof(uint64_t)) return 0;
    buffer->bytes = count * sizeof(uint64_t);
    total = buffer->bytes + 2U * GX_PADDING;
    if (posix_memalign(&buffer->allocation, GX_ALIGNMENT, total) != 0) return 0;
    /* Active pointer is itself 64-byte aligned. At least 16 initialized bytes
     * exist on both sides; the actual padding is64 on each side. */
    memset(buffer->allocation, 0, total);
    buffer->words = (uint64_t *)((unsigned char *)buffer->allocation + GX_PADDING);
    buffer->count = count;
    return 1;
}

static void gx_free_words(gx_words_t *buffer)
{
    free(buffer->allocation);
    memset(buffer, 0, sizeof(*buffer));
}

static int gx_padding_is_zero(const gx_words_t *buffer)
{
    const unsigned char *base = (const unsigned char *)buffer->allocation;
    const unsigned char *tail = (const unsigned char *)buffer->words + buffer->bytes;
    size_t i;
    for (i = 0U; i < GX_PADDING; ++i) {
        if (base[i] != 0U || tail[i] != 0U) return 0;
    }
    return 1;
}

/* Exactly one batch call is timed. No score output array is written. */
GX_NOINLINE uint64_t batch_kssd(const uint64_t *values, size_t count,
                              const kssd_array_t *context)
{
    uint64_t sum = UINT64_C(0);
    size_t i;
    for (i = 0U; i < count; ++i) {
        const uint64_t score = kssd_array_fast_with_tables(values[i], context);
        sum += score ^ (uint64_t)i;
    }
    return sum;
}

GX_NOINLINE uint64_t batch_xxh3(const uint64_t *values, size_t count)
{
    uint64_t sum = UINT64_C(0);
    size_t i;
    for (i = 0U; i < count; ++i) {
        const uint64_t value = values[i];
        const uint64_t score = XXH3_64bits(&value, sizeof(value));
        sum += score ^ (uint64_t)i;
    }
    return sum;
}

static int gx_prepare(const char *path, const char *expected_text,
                      const char *output_path)
{
    encoded_input_t input;
    size_t expected;
    int descriptor;
    FILE *output;
    int ok;
    if (!gx_parse_count(expected_text, &expected) || expected < (size_t)K)
        return gx_fail("invalid expected valid-base count");
    /* Original loader, original forward encoding, original input checksum. */
    if (!read_first_fasta_record(path, expected, &input))
        return gx_fail("original first-record loader failed");
    descriptor = open(output_path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (descriptor < 0) {
        free(input.values);
        return gx_fail("cannot create new encoded output; existing files are refused");
    }
    output = fdopen(descriptor, "wb");
    if (output == NULL) {
        close(descriptor);
        free(input.values);
        return gx_fail("cannot open encoded output stream; partial file retained");
    }
    ok = fwrite(input.values, sizeof(uint64_t), input.count, output) == input.count;
    if (fflush(output) != 0) ok = 0;
    if (fclose(output) != 0) ok = 0;
    if (!ok) {
        free(input.values);
        return gx_fail("encoded output write failed; partial file retained");
    }
    printf("{\"status\":\"PASS\",\"exit_code\":0,\"k\":%d,"
           "\"count\":%zu,\"valid_bases\":%zu,\"ambiguous_bases\":%zu,"
           "\"input_checksum\":\"%" PRIu64 "\",\"output_bytes\":%zu,"
           "\"format\":\"raw-little-endian-u64\"}\n", K, input.count,
           input.valid_bases, input.ambiguous_bases, input.checksum,
           input.count * sizeof(uint64_t));
    free(input.values);
    return EXIT_SUCCESS;
}

static int gx_read_encoded(const char *path, size_t count, gx_words_t *buffer,
                           uint64_t expected_input)
{
    FILE *input;
    struct stat st;
    uint64_t observed = UINT64_C(0);
    size_t i;
    int extra;
    if (!gx_allocate_words(buffer, count)) return 0;
    input = fopen(path, "rb");
    if (input == NULL) goto fail;
    if (fstat(fileno(input), &st) != 0 || !S_ISREG(st.st_mode) ||
        st.st_size < 0 || (uint64_t)st.st_size != (uint64_t)buffer->bytes) {
        fclose(input);
        goto fail;
    }
    if (fread(buffer->words, sizeof(uint64_t), count, input) != count) {
        fclose(input);
        goto fail;
    }
    extra = fgetc(input);
    if (extra != EOF || ferror(input)) {
        fclose(input);
        goto fail;
    }
    if (fclose(input) != 0) goto fail;
    /* Untimed full-domain/checksum traversal also touches every input page. */
    for (i = 0U; i < count; ++i) {
        if ((buffer->words[i] & ~PHASE1_DOMAIN_MASK) != UINT64_C(0)) goto fail;
        observed = checksum_update(observed, buffer->words[i], i);
    }
    if (observed != expected_input || !gx_padding_is_zero(buffer)) goto fail;
    return 1;
fail:
    gx_free_words(buffer);
    return 0;
}

static int gx_run(const char *method, const char *path, const char *count_text,
                  const char *input_text, const char *expected_text)
{
    gx_words_t input;
    kssd_array_t context;
    initialization_measurement_t setup;
    size_t count;
    uint64_t input_checksum;
    uint64_t expected;
    uint64_t actual = UINT64_C(0);
    uint64_t cpu_begin, cpu_end, wall_begin, wall_end;
    int method_id;
    int automatic = strcmp(expected_text, "auto") == 0;
    int initialized = 0;
    if (strcmp(method, "kssd") == 0) method_id = 0;
    else if (strcmp(method, "xxh3") == 0) method_id = 1;
    else if (strcmp(method, "gxhash") == 0) method_id = 2;
    else return gx_fail("method must be kssd, xxh3, or gxhash");
    if (!gx_parse_count(count_text, &count) || count == 0U ||
        !gx_parse_u64(input_text, &input_checksum) ||
        (!automatic && !gx_parse_u64(expected_text, &expected)))
        return gx_fail("invalid decimal count/input checksum/expected score checksum");
    if (automatic && method_id != 2)
        return gx_fail("auto is allowed only for gxhash warmup reference");
    if (!gx_read_encoded(path, count, &input, input_checksum))
        return gx_fail("encoded input size/domain/checksum/padding validation failed");
    memset(&context, 0, sizeof(context));
    if (method_id == 0) {
        if (!initialize_variant(&context, TABLE_RANK_DERIVED, &setup)) {
            gx_free_words(&input);
            return gx_fail("original rank-derived KSSD initialization failed");
        }
        initialized = 1;
    }
    if (automatic) expected = gxhash64_reference_batch(input.words, count);
    /* Switch and all allocation/read/setup/reference work are outside timers.
     * All three cases bracket one direct whole-array batch call identically. */
#define GX_TIME_BATCH(EXPRESSION) do {                                        \
        __asm__ volatile("" ::: "memory");                                   \
        cpu_begin = process_cpu_nanoseconds();                               \
        wall_begin = monotonic_nanoseconds();                                \
        actual = (EXPRESSION);                                               \
        wall_end = monotonic_nanoseconds();                                  \
        cpu_end = process_cpu_nanoseconds();                                 \
        __asm__ volatile("" ::: "memory");                                   \
    } while (0)
    switch (method_id) {
    case 0: GX_TIME_BATCH(batch_kssd(input.words, count, &context)); break;
    case 1: GX_TIME_BATCH(batch_xxh3(input.words, count)); break;
    default: GX_TIME_BATCH(gxhash64_batch(input.words, count)); break;
    }
#undef GX_TIME_BATCH
    phase1_sink ^= actual;
    if (initialized) kssd_array_destroy(&context);
    if (actual != expected || !gx_padding_is_zero(&input)) {
        fprintf(stderr, "actual=%" PRIu64 " expected=%" PRIu64 "\n", actual, expected);
        gx_free_words(&input);
        return gx_fail("score checksum or padding validation failed");
    }
    gx_free_words(&input);
    printf("{\"status\":\"PASS\",\"exit_code\":0,\"method\":");
    gx_json_string(method);
    printf(",\"k\":%d,\"count\":%zu,\"input_checksum\":\"%" PRIu64
           "\",\"checksum\":\"%" PRIu64 "\",\"expected_checksum\":\"%" PRIu64
           "\",\"expected_checksum_mode\":\"%s\",\"warmup_reference_ran\":%s,"
           "\"time_s\":%.9f,\"cpu_s\":%.9f,\"seed\":%u,"
           "\"input_message_bytes\":8,\"alignment_bytes\":64,"
           "\"leading_padding_bytes\":64,\"trailing_padding_bytes\":64,"
           "\"timing_boundary\":\"one whole-array scoring batch plus modular checksum; no score-array store\"}\n",
           K, count, input_checksum, actual, expected,
           automatic ? "warmup_reference" : "manifest", automatic ? "true" : "false",
           (double)(wall_end - wall_begin) / 1.0e9,
           (double)(cpu_end - cpu_begin) / 1.0e9,
           method_id == 1 ? 0U : 42U);
    return EXIT_SUCCESS;
}

static int gx_validate(void)
{
    gx_words_t input, scores;
    kssd_array_t context;
    initialization_measurement_t setup;
    uint64_t seed = UINT64_C(0x475856414c323032);
    uint64_t expected_kssd = UINT64_C(0), expected_xxh3 = UINT64_C(0);
    size_t i, count = 0U;
    size_t tails_checked = 0U;
    const size_t tails[] = {0U, 1U, 2U, 3U, 5U, 7U, 9U, 15U, 17U, 31U, 33U, 65U, GX_VALIDATE_N};
    int ok = 1;
    if (!gx_allocate_words(&input, GX_VALIDATE_N))
        return gx_fail("validation input allocation failed");
    if (!gx_allocate_words(&scores, GX_VALIDATE_N)) {
        gx_free_words(&input);
        return gx_fail("validation score allocation failed");
    }
    memset(&context, 0, sizeof(context));
    if (!initialize_variant(&context, TABLE_RANK_DERIVED, &setup)) {
        gx_free_words(&input); gx_free_words(&scores);
        return gx_fail("validation original KSSD setup failed");
    }
    input.words[count++] = UINT64_C(0);
    input.words[count++] = PHASE1_DOMAIN_MASK;
    input.words[count++] = UINT64_C(1);
    input.words[count++] = PHASE1_DOMAIN_MASK - UINT64_C(1);
    input.words[count++] = UINT64_C(0x5555555555555555) & PHASE1_DOMAIN_MASK;
    input.words[count++] = UINT64_C(0xaaaaaaaaaaaaaaaa) & PHASE1_DOMAIN_MASK;
    for (i = 0U; i < 2U * (size_t)K; ++i) {
        input.words[count++] = UINT64_C(1) << i;
        input.words[count++] = PHASE1_DOMAIN_MASK ^ (UINT64_C(1) << i);
    }
    {
        size_t consumed = 0U, segment;
        for (segment = 0U; segment < context.layout.segment_count; ++segment) {
            size_t shift;
            consumed += context.layout.segment_lengths[segment];
            shift = 2U * ((size_t)K - consumed);
            if (shift != 0U) {
                const uint64_t boundary = UINT64_C(1) << shift;
                input.words[count++] = boundary - UINT64_C(1);
                input.words[count++] = boundary;
                input.words[count++] = boundary + UINT64_C(1);
            }
        }
    }
    for (; count < GX_VALIDATE_N; ++count)
        input.words[count] = splitmix64_next_local(&seed) & PHASE1_DOMAIN_MASK;
    for (i = 0U; i < input.count; ++i) {
        const uint64_t value = input.words[i];
        uint64_t checked = UINT64_C(0);
        const uint64_t fast = kssd_array_fast_with_tables(value, &context);
        const uint64_t inline_xxh3 = XXH3_64bits(&value, sizeof(value));
        const uint64_t reference_xxh3 = GX_REF_XXH3_64bits(&value, sizeof(value));
        if (kssd_array_map(&context, value, &checked) != KSSD_ARRAY_OK ||
            fast != checked || inline_xxh3 != reference_xxh3 ||
            inline_xxh3 != XXH3_64bits_withSeed(&value, sizeof(value), UINT64_C(0))) {
            fprintf(stderr, "C score validation failed at index%zu\n", i);
            ok = 0; break;
        }
        expected_kssd += checked ^ (uint64_t)i;
        expected_xxh3 += reference_xxh3 ^ (uint64_t)i;
    }
    if (ok && (batch_kssd(input.words, input.count, &context) != expected_kssd ||
               batch_xxh3(input.words, input.count) != expected_xxh3)) ok = 0;
    if (ok && !gxhash64_official_vectors_ok()) ok = 0;
    if (ok && !gxhash64_validate_scores(input.words, input.count, scores.words)) ok = 0;
    if (ok) {
        for (i = 0U; i < input.count; ++i) {
            if (scores.words[i] != gxhash64_reference_score(input.words[i])) {
                fprintf(stderr, "gxhash score validation failed at index%zu\n", i);
                ok = 0; break;
            }
        }
    }
    for (i = 0U; ok && i < sizeof(tails) / sizeof(tails[0]); ++i) {
        const size_t n = tails[i];
        uint64_t ks = UINT64_C(0), xs = UINT64_C(0);
        size_t j;
        for (j = 0U; j < n; ++j) {
            const uint64_t value = input.words[j];
            ks += kssd_array_fast_with_tables(value, &context) ^ (uint64_t)j;
            xs += GX_REF_XXH3_64bits(&value, sizeof(value)) ^ (uint64_t)j;
        }
        if (batch_kssd(input.words, n, &context) != ks ||
            batch_xxh3(input.words, n) != xs ||
            gxhash64_batch(input.words, n) != gxhash64_reference_batch(input.words, n)) ok = 0;
        ++tails_checked;
    }
    if (!gx_padding_is_zero(&input) || !gx_padding_is_zero(&scores)) ok = 0;
    kssd_array_destroy(&context);
    gx_free_words(&input); gx_free_words(&scores);
    if (!ok) return gx_fail("small score/core/reference/batch-tail validation failed");
    printf("{\"status\":\"PASS\",\"exit_code\":0,\"mode\":\"validate\","
           "\"k\":%d,\"tested_values\":%zu,\"tail_cases\":%zu,"
           "\"KSSD_fast_vs_checked\":true,\"XXH3_inline_vs_noninline\":true,"
           "\"XXH3_unseeded_vs_seed0\":true,\"gxhash_direct_vs_padded_reference\":true,"
           "\"gxhash_official_vectors\":true,\"padding_intact\":true,"
           "\"score_output_store_in_formal\":false}\n", K, GX_VALIDATE_N, tails_checked);
    return EXIT_SUCCESS;
}

int main(int argc, char **argv)
{
    if (!gx_little_endian()) return gx_fail("requires little-endian uint64 platform");
    if (argc == 2 && strcmp(argv[1], "--validate") == 0) return gx_validate();
    if (argc == 5 && strcmp(argv[1], "--prepare") == 0)
        return gx_prepare(argv[2], argv[3], argv[4]);
    if (argc == 7 && strcmp(argv[1], "--run") == 0)
        return gx_run(argv[2], argv[3], argv[4], argv[5], argv[6]);
    return gx_fail("usage: --prepare FASTA EXPECTED_BASES NEW_U64 | --run METHOD U64 COUNT INPUTSUM EXPECTEDSCORE | --validate");
}
