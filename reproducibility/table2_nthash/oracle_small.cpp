#include <kssd_array.h>
#include <nthash/nthash.hpp>
#include <algorithm>
#include <cstdint>
#include <cctype>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>
#ifndef K
#define K 21
#endif
static uint64_t mix(uint64_t x){x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);return x^(x>>31);}
static unsigned code(char c){return c=='A'?0:c=='C'?1:c=='G'?2:3;}
int main(int argc,char **argv){
 if(argc!=3) return 2; std::ifstream f(argv[1]);if(!f)return 3; std::string line,s;bool record=false;
 while(std::getline(f,line)){if(!line.empty()&&line[0]=='>'){if(record)break;record=true;continue;}if(!record)continue;for(unsigned char c:line){char u=std::toupper(c);if(u=='A'||u=='C'||u=='G'||u=='T')s+=u;}}
 const size_t w=std::stoull(argv[2]);if(s.size()<K || w==0 || w>s.size()-K+1)return 4;
 kssd_array_t c=KSSD_ARRAY_CONTEXT_INIT;if(kssd_array_init(&c,K,42)!=KSSD_ARRAY_OK)return 5;
 const size_t n=s.size()-K+1;std::vector<uint64_t>a(n),b(n);
 for(size_t i=0;i<n;++i){uint64_t fw=0,rv=0;for(size_t j=0;j<K;++j){fw=(fw<<2)|code(s[i+j]);rv=(rv<<2)|(3-code(s[i+K-1-j]));}
  uint64_t x;if(kssd_array_map(&c,std::min(fw,rv),&x)!=KSSD_ARRAY_OK)return 6;a[i]=x;
  nthash::NtHash nt(s.data()+i,K,1U,static_cast<nthash::typedefs::K_TYPE>(K));if(!nt.roll())return 7;b[i]=nt.hashes()[0];}
 for(unsigned method=0;method<2;++method){auto &v=method?b:a;uint64_t score=0,pos=0,val=0;
  for(size_t i=0;i<n;++i)score^=mix(v[i]^(i*UINT64_C(0x9e3779b97f4a7c15)));
  for(size_t i=0;i+w<=n;++i){size_t best=i;for(size_t j=i+1;j<i+w;++j)if(v[j]<v[best])best=j;
   pos^=mix(best^(i*UINT64_C(0xd6e8feb86659fd93)));val^=mix(v[best]^(i*UINT64_C(0x9e3779b97f4a7c15)));}
  std::cout<<(method?"ntHash":"KSSD-Array")<<'\t'<<n<<'\t'<<n-w+1<<'\t'<<std::hex<<score<<'\t'<<pos<<'\t'<<val<<std::dec<<'\n';}
 kssd_array_destroy(&c);return 0;
}
