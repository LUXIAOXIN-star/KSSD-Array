/* Compiled separately for k=19,21,31. Original scoring code is included unchanged. */
#include <stdlib.h>
#include <stdint.h>
#include "kssd_array_fast.h"
#define JOIN_(a,b) a##b
#define JOIN(a,b) JOIN_(a,b)
#define SCORE_FN JOIN(review_scores_,KSSD_ARRAY_FIXED_K)
#define MINI_FN JOIN(review_minimizers_,KSSD_ARRAY_FIXED_K)
#define K KSSD_ARRAY_FIXED_K

static inline uint64_t code(uint8_t c) {
    return c == 'C' ? 1 : c == 'G' ? 2 : c == 'T' ? 3 : 0;
}
static inline uint64_t advance_score(const kssd_array_t *ctx, uint8_t c,
                                    uint64_t *fw, uint64_t *rc) {
    const uint64_t mask = (UINT64_C(1) << (2*K)) - 1;
    const uint64_t b = code(c);
    *fw = ((*fw << 2) | b) & mask;
    *rc = (*rc >> 2) | ((3-b) << (2*(K-1)));
    return kssd_array_fast_with_tables(*fw < *rc ? *fw : *rc, ctx);
}

size_t SCORE_FN(const void *opaque, const uint8_t *dna, size_t n,
                uint64_t *out, size_t capacity) {
    const kssd_array_t *ctx = opaque;
    if (!ctx || ctx->layout.k != K) return SIZE_MAX;
    if (n < K) return 0;
    if (capacity < n-K+1) return SIZE_MAX;
    uint64_t fw=0, rc=0;
    /* Prefix encoding needs no score; each complete k-mer is scored once. */
    for (size_t i=0; i<K-1; ++i) {
        uint64_t b=code(dna[i]);
        fw=(fw<<2)|b;
        rc=(rc>>2)|((3-b)<<(2*(K-1)));
    }
    for (size_t i=K-1; i<n; ++i) out[i-K+1]=advance_score(ctx,dna[i],&fw,&rc);
    return n-K+1;
}

typedef struct { uint64_t score; uint32_t pos; } Node;
typedef struct { Node *buf; size_t front,len,cap; } Queue;
static inline Node *first(Queue *q) { return &q->buf[q->front]; }
static inline Node *last(Queue *q) { return &q->buf[(q->front+q->len-1)%q->cap]; }
static inline void push(Queue *q, uint64_t score, uint32_t pos, size_t w, int right) {
    while (q->len && (size_t)first(q)->pos+w<=pos) {
        q->front=(q->front+1)%q->cap; --q->len;
    }
    while (q->len && (right ? last(q)->score>=score : last(q)->score>score)) --q->len;
    q->buf[(q->front+q->len)%q->cap]=(Node){score,pos};
    ++q->len;
}

size_t MINI_FN(const void *opaque, const uint8_t *dna, size_t n,
              size_t w, int strict, uint32_t *out, size_t capacity) {
    const kssd_array_t *ctx=opaque;
    if (!ctx || ctx->layout.k!=K || !w || w>32767 || n>=UINT32_MAX) return SIZE_MAX;
    const size_t span=K+w-1;
    if (strict && !(span&1)) return SIZE_MAX;
    if (n<span) return 0;
    if (capacity<n-K+1) return SIZE_MAX;
    Node *storage=malloc(sizeof(Node)*w*(strict?2:1));
    if (!storage) return SIZE_MAX;
    Queue left={storage,0,0,w}, right={strict?storage+w:NULL,0,0,w};
    uint64_t fw=0,rc=0;
    size_t tg=0,used=0;
    for (size_t i=0;i<n;++i) {
        if (strict) {
            tg += dna[i]=='T' || dna[i]=='G';
            if (i>=span) tg -= dna[i-span]=='T' || dna[i-span]=='G';
        }
        if (i<K-1) {
            uint64_t b=code(dna[i]);
            fw=(fw<<2)|b;rc=(rc>>2)|((3-b)<<(2*(K-1)));
            continue;
        }
        uint64_t score=advance_score(ctx,dna[i],&fw,&rc);
        uint32_t pos=(uint32_t)(i-K+1);
        push(&left,score,pos,w,0);
        if (strict) push(&right,score,pos,w,1);
        if (i+1>=span) {
            uint32_t chosen=(!strict || 2*tg>span)?first(&left)->pos:first(&right)->pos;
            if (!used || out[used-1]!=chosen) out[used++]=chosen;
        }
    }
    free(storage);
    return used;
}
