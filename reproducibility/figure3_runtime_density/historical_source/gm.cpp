// Interface adaptation only. Original GreedyMini order and loader are unchanged.
#include <cstdint>
#include <cstddef>
#include <vector>
#include <fstream>
#include <iostream>
#include <string>
#include <algorithm>
#include <stdexcept>
#include <sys/resource.h>
#include <sched.h>
#include <openssl/sha.h>
#include "gm_loader_exact.inc"

struct Gm { std::vector<uint64_t> rank; };
extern "C" void* sd_gm_create(const char* filename) {
    try {
        auto* p=new Gm{load_vector_from_file(filename)};
        if(p->rank.size()!=4096 || *std::max_element(p->rank.begin(),p->rank.end())>4096) {
            delete p; return nullptr;
        }
        return p;
    } catch(...) {return nullptr;}
}
extern "C" void sd_gm_destroy(void* p){delete static_cast<Gm*>(p);}
extern "C" size_t sd_gm_table_bytes(const void* p){return static_cast<const Gm*>(p)->rank.size()*sizeof(uint64_t);}
extern "C" size_t sd_gm_rank_count(const void* p){return static_cast<const Gm*>(p)->rank.size();}
extern "C" uint64_t sd_gm_rank(const void* p,size_t x){return static_cast<const Gm*>(p)->rank.at(x);}
extern "C" size_t sd_gm_scores(const void* opaque,const uint8_t* dna,size_t n,size_t k,uint64_t* out,size_t cap){
    if(!opaque || (k!=21 && k!=31) || (n>=k && cap<n-k+1))return SIZE_MAX;
    if(n<k)return 0;
    const auto& rank=static_cast<const Gm*>(opaque)->rank;
    const uint64_t mask=(UINT64_C(1)<<k)-1;
    const size_t tail=k-12;
    const uint64_t tailmask=(UINT64_C(1)<<tail)-1;
    uint64_t lo=0,hi=0;
    for(size_t i=0;i<n;++i){
        const uint8_t c=dna[i]=='C'?1:dna[i]=='G'?2:dna[i]=='T'?3:0;
        lo=((lo<<1)|(c&1))&mask; hi=((hi<<1)|(c>>1))&mask;
        if(i+1>=k){
            // Author-documented binary prefix extension BEFORE DNA extension.
            // Low bit plane -> GM prefix12 + lexicographic suffix; high plane -> lex.
            // Rank4096 is the upstream unselected marker, retained without changes.
            const uint64_t ext=(rank[lo>>tail]<<tail)|(lo&tailmask);
            out[i+1-k]=(ext<<k)|hi;
        }
    }
    return n-k+1;
}
extern "C" long sd_rss_kib(){rusage r{};getrusage(RUSAGE_SELF,&r);return r.ru_maxrss;}
extern "C" int sd_cpu(){return sched_getcpu();}
extern "C" void sd_sha256(const void* p,size_t n,uint8_t* out){SHA256(static_cast<const uint8_t*>(p),n,out);}
