#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Deterministic reconstruction of the six tiny public smoke fixtures.
 *
 * The accepted fixtures were originally written as literal test records during
 * workflow construction; they were not produced by the historical random.c
 * program that generated AEEE.fasta.  This source keeps the fixture design
 * visible: repeated motifs, named sequence blocks, truth-derived BED points,
 * and explicit S2 test read names.  It does not contain serialized fixture
 * files or an encoded binary payload.
 */

enum { FIXTURE_SEED = 42 };

static int output_path(char *buffer, size_t size, const char *root,
                       const char *relative)
{
    int written = snprintf(buffer, size, "%s/%s", root, relative);
    if (written < 0 || (size_t)written >= size) {
        fputs("fixture output path is too long\n", stderr);
        return -1;
    }
    return 0;
}

static FILE *open_output(const char *root, const char *relative)
{
    char path[4096];
    FILE *stream;

    if (output_path(path, sizeof(path), root, relative) != 0) {
        return NULL;
    }
    stream = fopen(path, "wb");
    if (stream == NULL) {
        fprintf(stderr, "cannot create %s: %s\n", path, strerror(errno));
    }
    return stream;
}

static int close_output(FILE *stream, const char *relative)
{
    if (ferror(stream) != 0 || fclose(stream) != 0) {
        fprintf(stderr, "cannot finish %s\n", relative);
        return -1;
    }
    return 0;
}

static int put_repeat(FILE *stream, const char *motif, size_t repetitions)
{
    size_t index;
    for (index = 0; index < repetitions; ++index) {
        if (fputs(motif, stream) == EOF) {
            return -1;
        }
    }
    return 0;
}

static int put_wrapped_motifs(FILE *stream,
                              const char *left_motif, size_t left_repetitions,
                              const char *middle_motif, size_t middle_repetitions,
                              const char *right_motif, size_t right_repetitions,
                              size_t width)
{
    const char *motifs[3] = {left_motif, middle_motif, right_motif};
    const size_t counts[3] = {
        left_repetitions, middle_repetitions, right_repetitions
    };
    size_t column = 0;
    size_t group;

    for (group = 0; group < 3; ++group) {
        size_t repetition;
        size_t motif_length = strlen(motifs[group]);
        for (repetition = 0; repetition < counts[group]; ++repetition) {
            size_t base;
            for (base = 0; base < motif_length; ++base) {
                if (fputc(motifs[group][base], stream) == EOF) {
                    return -1;
                }
                ++column;
                if (column == width) {
                    if (fputc('\n', stream) == EOF) {
                        return -1;
                    }
                    column = 0;
                }
            }
        }
    }
    if (column != 0 && fputc('\n', stream) == EOF) {
        return -1;
    }
    return 0;
}

static int write_figure3(const char *root)
{
    static const char relative[] =
        "reproducibility/figure3/fixtures/figure3_smoke.fa";
    FILE *stream = open_output(root, relative);
    if (stream == NULL) {
        return -1;
    }
    if (fputs(">smoke_first_record\n", stream) == EOF ||
        put_wrapped_motifs(stream, "ACGT", 50, "N", 12, "TGCA", 50, 64) != 0 ||
        fputs(">ignored_second_record\n", stream) == EOF ||
        put_repeat(stream, "GATTACA", 20) != 0 ||
        fputc('\n', stream) == EOF) {
        fclose(stream);
        return -1;
    }
    return close_output(stream, relative);
}

static int write_table4(const char *root)
{
    static const char relative[] =
        "reproducibility/table4/fixtures/table4_smoke.fa";
    /* Named blocks preserve the accepted line layout and visible N-boundary. */
    static const char *const primary_blocks[] = {
        "ACGTGCTAGCTAGGCTAACCGTTAGCGTACGATCGTACCTGATCGTAGCTAGGCTAATCGGATCCTAGCATCGATG",
        "TTACCGGATGCTAGCTTACGATCGGCTAACGTAGCATTCGATGGCATCGTAGGCTAACCTGATCGTACGATGCTA",
        "CGTAGGATCCGATGCTAACCGTAGCTAGCATGCTAGGCTAACGTNNNNNNNNNNTCGATGCTAGCATCGGATACGT",
        "GCTAACCGATCGTAGCTAGGATCGTACCGGATGCTAGCTAACGTTAGCATCGATGGCTAACGTAGCTAGGATCGA",
    };
    FILE *stream = open_output(root, relative);
    size_t index;
    if (stream == NULL) {
        return -1;
    }
    if (fputs(">table4_smoke_primary deterministic_first_record\n", stream) == EOF) {
        fclose(stream);
        return -1;
    }
    for (index = 0; index < sizeof(primary_blocks) / sizeof(primary_blocks[0]); ++index) {
        if (fprintf(stream, "%s\n", primary_blocks[index]) < 0) {
            fclose(stream);
            return -1;
        }
    }
    if (fputs(">table4_smoke_ignored second_record_must_not_be_benchmarked\n", stream) == EOF ||
        put_repeat(stream, "TTTTCCCCAAAAGGGG", 4) != 0 ||
        fputc('\n', stream) == EOF) {
        fclose(stream);
        return -1;
    }
    return close_output(stream, relative);
}

static int write_reference(const char *root)
{
    static const char relative[] =
        "reproducibility/minimap2/fixtures/reference.fa";
    static const char mixed_motif[] =
        "ACGTTGCAAGTCGATCGTACCTGATGCCATGACCTAGTCGATGCTAGGCTA";
    static const char ambiguous_motif[] =
        "TTGACCGTACGATGCTAGCTAGGCTAACCGTAGCTAGTCGATCGTACGATGC";
    static const char hpc_probe[] = "ACGTACGTGCACTGACTG";
    FILE *stream = open_output(root, relative);
    if (stream == NULL) {
        return -1;
    }
    if (fputs(">reference_mixed\n", stream) == EOF ||
        put_repeat(stream, mixed_motif, 5) != 0 || fputc('\n', stream) == EOF ||
        fputs(">reference_ambiguous\n", stream) == EOF ||
        put_repeat(stream, ambiguous_motif, 1) != 0 ||
        put_repeat(stream, "N", 20) != 0 ||
        put_repeat(stream, ambiguous_motif, 2) != 0 || fputc('\n', stream) == EOF ||
        fputs(">reference_homopolymer\n", stream) == EOF ||
        put_repeat(stream, "A", 20) != 0 || put_repeat(stream, "C", 20) != 0 ||
        put_repeat(stream, "G", 20) != 0 || put_repeat(stream, "T", 20) != 0 ||
        put_repeat(stream, hpc_probe, 2) != 0 ||
        put_repeat(stream, "A", 16) != 0 || put_repeat(stream, "C", 16) != 0 ||
        put_repeat(stream, "G", 16) != 0 || put_repeat(stream, "T", 16) != 0 ||
        fputc('\n', stream) == EOF) {
        fclose(stream);
        return -1;
    }
    return close_output(stream, relative);
}

static int write_query(const char *root)
{
    static const char relative[] =
        "reproducibility/minimap2/fixtures/query.fa";
    static const char mixed_motif[] =
        "ACGTTGCAAGTCGATCGTACCTGATGCCATGACCTAGTCGATGCTAGGCTA";
    static const char ambiguous_motif[] =
        "TTGACCGTACGATGCTAGCTAGGCTAACCGTAGCTAGTCGATCGTACGATGC";
    static const char ambiguous_suffix[] =
        "TAGCTAGGCTAACCGTAGCTAGTCGATCGTACGATGC";
    static const char hpc_probe[] = "ACGTACGTGCACTGACTG";
    char mixed_reference[(sizeof(mixed_motif) - 1U) * 5U + 1U];
    FILE *stream = open_output(root, relative);
    size_t repetition;
    if (stream == NULL) {
        return -1;
    }
    mixed_reference[0] = '\0';
    for (repetition = 0; repetition < 5; ++repetition) {
        strcat(mixed_reference, mixed_motif);
    }
    if (fputs(">query_mixed\n", stream) == EOF ||
        fwrite(mixed_reference + 12, 1, 141, stream) != 141 ||
        fputc('\n', stream) == EOF ||
        fputs(">query_ambiguous\n", stream) == EOF ||
        fputs(ambiguous_suffix, stream) == EOF || put_repeat(stream, "N", 5) != 0 ||
        fputs(ambiguous_motif, stream) == EOF || fputc('\n', stream) == EOF ||
        fputs(">query_homopolymer\n", stream) == EOF ||
        put_repeat(stream, "A", 12) != 0 || put_repeat(stream, "C", 12) != 0 ||
        put_repeat(stream, "G", 12) != 0 || put_repeat(stream, "T", 12) != 0 ||
        put_repeat(stream, hpc_probe, 2) != 0 || fputc('\n', stream) == EOF) {
        fclose(stream);
        return -1;
    }
    return close_output(stream, relative);
}

static int write_s2_reads(const char *root)
{
    static const char relative[] =
        "reproducibility/minimap2/alignment_consistency_truth_origin/fixtures/reads.fq";
    static const char *const names[] = {
        "q_plus", "q_minus", "q_unmapped", "q_wrong_strand",
        "q_wrong_ref", "q_wrong_pos", "q_duplicate",
    };
    FILE *stream = open_output(root, relative);
    size_t index;
    if (stream == NULL) {
        return -1;
    }
    for (index = 0; index < sizeof(names) / sizeof(names[0]); ++index) {
        if (fprintf(stream, "@%s\nACGTACGTAC\n+\nIIIIIIIIII\n", names[index]) < 0) {
            fclose(stream);
            return -1;
        }
    }
    return close_output(stream, relative);
}

static int write_s2_bed(const char *root)
{
    static const char relative[] =
        "reproducibility/minimap2/alignment_consistency_truth_origin/fixtures/repeats.bed";
    /* Points lie five bases into the accepted [100,110) and [790,800) truths. */
    static const struct {
        unsigned truth_start0;
        const char *label;
    } intervals[] = {
        {100U, "repeat_plus"},
        {790U, "repeat_minus"},
    };
    FILE *stream = open_output(root, relative);
    size_t index;
    if (stream == NULL) {
        return -1;
    }
    for (index = 0; index < sizeof(intervals) / sizeof(intervals[0]); ++index) {
        unsigned start = intervals[index].truth_start0 + 5U;
        if (fprintf(stream, "ref1\t%u\t%u\t%s\n",
                    start, start + 1U, intervals[index].label) < 0) {
            fclose(stream);
            return -1;
        }
    }
    return close_output(stream, relative);
}

static int parse_seed(const char *text, unsigned *seed)
{
    char *end = NULL;
    unsigned long value;
    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value > UINT32_MAX) {
        return -1;
    }
    *seed = (unsigned)value;
    return 0;
}

int main(int argc, char **argv)
{
    unsigned seed;
    if (argc != 3) {
        fprintf(stderr, "usage: %s OUTPUT_ROOT SEED\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (parse_seed(argv[2], &seed) != 0 || seed != FIXTURE_SEED) {
        fprintf(stderr, "fixture seed must be exactly %u\n", FIXTURE_SEED);
        return EXIT_FAILURE;
    }
    if (write_figure3(argv[1]) != 0 ||
        write_table4(argv[1]) != 0 ||
        write_reference(argv[1]) != 0 ||
        write_query(argv[1]) != 0 ||
        write_s2_reads(argv[1]) != 0 ||
        write_s2_bed(argv[1]) != 0) {
        return EXIT_FAILURE;
    }
    puts("GENERATED_FIXTURES=6");
    puts("FIXTURE_SEED=42");
    return EXIT_SUCCESS;
}
