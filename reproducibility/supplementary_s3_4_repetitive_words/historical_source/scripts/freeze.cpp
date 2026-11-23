#include "frozen_tables.hpp"
#include <iostream>
int main(int argc,char**argv){try{if(argc!=3)throw std::runtime_error("usage: freeze k output.bin");int k=std::stoi(argv[1]);kssd_array_t ctx=KSSD_ARRAY_CONTEXT_INIT;
 if(kssd_array_init(&ctx,k,42)!=KSSD_ARRAY_OK)throw std::runtime_error("production init failed");
 save_frozen(ctx,argv[2]);LoadedKssd loaded(argv[2],k);uint64_t comparisons=0,table_entries=0;
 for(size_t s=1;s<=ctx.layout.master_length;s++)for(size_t i=0;i<ctx.permutation_sizes[s];i++){if(ctx.permutations[s][i]!=loaded.ctx.permutations[s][i])throw std::runtime_error("table mismatch");table_entries++;}
 uint64_t mask=k==32?~uint64_t(0):(uint64_t(1)<<(2*k))-1,state=1234567;
 uint64_t n=k<=9?(uint64_t(1)<<(2*k)):100000;
 for(uint64_t i=0;i<n;i++){state=state*6364136223846793005ULL+1442695040888963407ULL;uint64_t x=(k<=9?i:state)&mask,out=0;if(kssd_array_map(&ctx,x,&out)!=KSSD_ARRAY_OK||out!=loaded(x)||out!=kssd_array_map_unchecked(&loaded.ctx,x))throw std::runtime_error("score mismatch");comparisons++;}
 std::cout<<"PASS k="<<k<<" seed=42 tables="<<table_entries<<" score_comparisons="<<comparisons<<"\n";
 if(k==2){std::cout<<"R2:";for(int i=0;i<16;i++)std::cout<<' '<<ctx.master_permutation[i];std::cout<<"\nAG="<<loaded(2)<<" GC="<<loaded(9)<<" CA="<<loaded(4)<<'\n';}
 kssd_array_destroy(&ctx);return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
