#include "kernels.h"
using U=uint64_t;
constexpr U MASK42=(U(1)<<42)-1,XOR_MASK=2363035971221ULL,ODD=2949826092126892291ULL;
// Each kernel has the same call boundary, disjoint input/output layout and store.
// No per-key method dispatch or checksum is present inside these timed loops.
// All scores are the unchanged native fixed mappings from fixed_config.json.
#define ATTR __attribute__((noinline,noipa))
ATTR void score_kssd(const U* __restrict in,U* __restrict out,size_t n,const uint16_t* __restrict p){for(size_t i=0;i<n;i++){U x=in[i];out[i]=(U(p[x>>28])<<28)|(U(p[(x>>14)&16383])<<14)|p[x&16383];}}
ATTR void score_xor(const U* __restrict in,U* __restrict out,size_t n,const uint16_t*){for(size_t i=0;i<n;i++)out[i]=in[i]^XOR_MASK;}
ATTR void score_bare42(const U* __restrict in,U* __restrict out,size_t n,const uint16_t*){for(size_t i=0;i<n;i++)out[i]=(in[i]*ODD)&MASK42;}
ATTR void score_bare64(const U* __restrict in,U* __restrict out,size_t n,const uint16_t*){for(size_t i=0;i<n;i++)out[i]=in[i]*ODD;}
ATTR void copy_control(const U* __restrict in,U* __restrict out,size_t n,const uint16_t*){for(size_t i=0;i<n;i++)out[i]=in[i];}
