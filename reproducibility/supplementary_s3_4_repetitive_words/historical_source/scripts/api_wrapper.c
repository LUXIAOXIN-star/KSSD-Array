#include <stdlib.h>
#include "kssd_array.h"
void *retry_context(unsigned k, unsigned long long seed, int rng) {
 kssd_array_t *p=(kssd_array_t*)calloc(1,sizeof(*p));
 if(!p)return NULL;
 if(kssd_array_init_with_rng(p,k,(uint64_t)seed,(kssd_array_rng_t)rng)!=KSSD_ARRAY_OK){free(p);return NULL;}
 return p;
}
unsigned long long retry_score(void *p,unsigned long long x){return kssd_array_map_unchecked((kssd_array_t*)p,(uint64_t)x);}
void retry_free(void*p){if(p){kssd_array_destroy((kssd_array_t*)p);free(p);}}
