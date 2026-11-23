#pragma once
// Transport wrapper only. Production permutation generation and scoring are unchanged.
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "kssd_array.h"
#include "kssd_array_inline.h"
inline void putle(std::ostream& f,uint64_t x,unsigned n){for(unsigned i=0;i<n;i++)f.put(char((x>>(8*i))&255));if(!f)throw std::runtime_error("write error");}
inline uint64_t getle(std::istream& f,unsigned n){uint64_t x=0;for(unsigned i=0;i<n;i++){int b=f.get();if(b==EOF)throw std::runtime_error("truncated frozen file");x|=uint64_t(uint8_t(b))<<(8*i);}return x;}
inline void save_frozen(const kssd_array_t&ctx,const std::string&file){
 if(!ctx.initialized)throw std::runtime_error("uninitialized context");
 std::ofstream f(file,std::ios::binary);if(!f)throw std::runtime_error("cannot save frozen file");
 f.write("KSDFIX01",8);putle(f,ctx.layout.k,4);putle(f,ctx.layout.master_length,4);putle(f,ctx.layout.segment_cap,4);putle(f,ctx.rng,4);putle(f,ctx.seed,8);
 for(size_t s=1;s<=ctx.layout.master_length;s++){putle(f,s,4);putle(f,ctx.permutation_sizes[s],8);for(size_t i=0;i<ctx.permutation_sizes[s];i++)putle(f,ctx.permutations[s][i],2);}
}
inline void load_frozen(kssd_array_t&ctx,const std::string&file,int requested_k){
 // Allocate the same public owning-context layout, without drawing any random numbers.
 if(ctx.initialized)throw std::runtime_error("context already initialized");
 std::ifstream f(file,std::ios::binary);if(!f)throw std::runtime_error("cannot open "+file);
 char magic[8];f.read(magic,8);if(!f||std::string(magic,8)!="KSDFIX01")throw std::runtime_error("bad frozen header");
 uint64_t k=getle(f,4),L=getle(f,4),cap=getle(f,4),rng=getle(f,4),seed=getle(f,8);
 if(k!=uint64_t(requested_k)||cap!=8||rng>1||kssd_array_layout(k,cap,&ctx.layout)!=KSSD_ARRAY_OK||L!=ctx.layout.master_length)throw std::runtime_error("wrong frozen layout");
 ctx.seed=seed;ctx.rng=kssd_array_rng_t(rng);
 try{
  for(size_t s=1;s<=L;s++){
   uint64_t ss=getle(f,4),n=getle(f,8);if(ss!=s||n!=(uint64_t(1)<<(2*s)))throw std::runtime_error("wrong table length");
   auto *p=(uint16_t*)std::malloc(n*sizeof(uint16_t));if(!p)throw std::bad_alloc();ctx.permutations[s]=p;ctx.permutation_sizes[s]=n;
   std::vector<bool>seen(n,false);for(size_t i=0;i<n;i++){uint64_t v=getle(f,2);if(v>=n||seen[v])throw std::runtime_error("not a permutation");seen[v]=true;p[i]=uint16_t(v);}
   if(s==L){ctx.master_permutation=p;ctx.master_size=n;}
  }
  if(f.peek()!=EOF){throw std::runtime_error("extra frozen data");}
  ctx.initialized=1;
 }catch(...){kssd_array_destroy(&ctx);throw;}
}
struct LoadedKssd{
 kssd_array_t ctx=KSSD_ARRAY_CONTEXT_INIT;
 kssd_array_inline_plan_t plan=KSSD_ARRAY_INLINE_PLAN_INIT;
 LoadedKssd(const std::string&file,int k){load_frozen(ctx,file,k);if(kssd_array_inline_plan_init(&plan,&ctx)!=KSSD_ARRAY_OK){kssd_array_destroy(&ctx);throw std::runtime_error("plan init failed");}}
 ~LoadedKssd(){kssd_array_destroy(&ctx);}LoadedKssd(const LoadedKssd&)=delete;
 uint64_t operator()(uint64_t x)const{return kssd_array_inline_map_unchecked(&plan,x);}
};
