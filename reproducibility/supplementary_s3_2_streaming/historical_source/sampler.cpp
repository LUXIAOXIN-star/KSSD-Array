#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/resource.h>
#include <sched.h>
#include <openssl/sha.h>
#include "kssd_array.h"
#include "tools.h"
extern "C" void* ld_mod_init(size_t,size_t);
extern "C" size_t ld_mod_sample(void*,const uint8_t*,size_t,uint64_t*);
extern "C" void ld_mod_destroy(void*);
using Clock=std::chrono::steady_clock;
using Run=std::pair<size_t,size_t>;
static std::array<uint8_t,256> make_lut(){std::array<uint8_t,256>a;a.fill(255);a['A']=0;a['C']=1;a['G']=2;a['T']=3;return a;}
static const auto lut=make_lut();
static double secs(Clock::time_point a){return std::chrono::duration<double>(Clock::now()-a).count();}
static void require(bool v,const char*s){if(!v)throw std::runtime_error(s);}
static std::string digest(const void*p,size_t n){unsigned char h[32];SHA256((const unsigned char*)p,n,h);std::ostringstream s;for(auto c:h)s<<std::hex<<std::setw(2)<<std::setfill('0')<<(int)c;return s.str();}
struct Node{uint64_t score;size_t pos;};
template<bool Greedy> size_t sample_order(const std::vector<uint8_t>&dna,size_t k,size_t w,const kssd_array_t&ctx,const std::vector<uint64_t>&table,size_t k0,uint64_t*out){
 const uint64_t mask=(1ULL<<(2*k))-1,bmask=(1ULL<<k)-1,tailmask=(1ULL<<(k-k0))-1;
 uint64_t encoded=0,lo=0,hi=0;size_t runlen=0,used=0,last=SIZE_MAX;
 std::deque<Node> q;
 for(size_t i=0;i<dna.size();++i){uint8_t c=lut[dna[i]];
  if(c>3){encoded=lo=hi=0;runlen=0;q.clear();last=SIZE_MAX;continue;}
  if constexpr(Greedy){lo=((lo<<1)|(c&1))&bmask;hi=((hi<<1)|(c>>1))&bmask;}
  else{encoded=((encoded<<2)|c)&mask;}
  ++runlen;if(runlen<k)continue;
  uint64_t score;
  if constexpr(Greedy){uint64_t ext=(table[lo>>(k-k0)]<<(k-k0))|(lo&tailmask);score=(ext<<k)|hi;}
  else{score=kssd_array_map_unchecked(&ctx,encoded);}
  size_t pos=i+1-k;
  while(!q.empty()&&q.back().score>score)q.pop_back();q.push_back({score,pos});
  if(runlen<k+w-1)continue;
  size_t begin=pos+1-w;while(q.front().pos<begin)q.pop_front();size_t selected=q.front().pos;
  if(last!=selected){out[used++]=selected;last=selected;}
 }
 return used;
}
struct Stats{uint64_t valid=0,kmers=0,windows=0,count=0,gaps=0;std::vector<uint64_t> hist;double gapmean=0,median=0,p95=0,p99=0;size_t maxgap=0;};
static double quantile(const std::vector<uint64_t>&h,uint64_t n,double q){if(!n)return 0;double index=(n-1)*q;uint64_t lower=(uint64_t)index,upper=(uint64_t)std::ceil(index),cum=0;double a=0,b=0;bool got=false;for(size_t x=0;x<h.size();++x){auto next=cum+h[x];if(!got&&next>lower){a=x;got=true;}if(next>upper){b=x;break;}cum=next;}return a+(b-a)*(index-lower);}
static Stats check(const std::vector<Run>&runs,size_t k,size_t w,const uint64_t*out,size_t count){
 Stats s;s.count=count;s.hist.resize(w+1);size_t j=0;uint64_t sumgap=0;
 for(auto [begin,end]:runs){size_t len=end-begin;s.valid+=len;if(len>=k)s.kmers+=len-k+1;if(len>=k+w-1)s.windows+=len-k-w+2;
  size_t oldj=j;uint64_t last=SIZE_MAX;
  while(j<count&&out[j]<end){uint64_t p=out[j];require(p>=begin&&p+k<=end,"position crosses invalid base or out of range");require(len>=k+w-1,"selection in invalid short window");
   if(j==oldj)require(p<begin+w,"uncovered first window");
   else{require(p>last,"duplicate or unsorted output");size_t gap=p-last;require(gap<=w,"uncovered interior window");s.hist[gap]++;sumgap+=gap;s.gaps++;s.maxgap=std::max(s.maxgap,gap);}
   last=p;j++;
  }
  if(len>=k+w-1){require(j>oldj,"missing eligible run");require(last>=end-k-w+1,"uncovered last window");}
  else require(j==oldj,"short run emitted position");
 }
 require(j==count,"position outside valid runs");s.gapmean=s.gaps?double(sumgap)/s.gaps:0;s.median=quantile(s.hist,s.gaps,.5);s.p95=quantile(s.hist,s.gaps,.95);s.p99=quantile(s.hist,s.gaps,.99);return s;
}
static long rss(){rusage r{};getrusage(RUSAGE_SELF,&r);return r.ru_maxrss;}
int main(int argc,char**argv){try{
 require(argc==8,"usage: method k w raw_dna output_prefix repetitions third_party_root");
 const std::string method=argv[1],input=argv[4],prefix=argv[5],third=argv[7];size_t k=std::stoul(argv[2]),w=std::stoul(argv[3]),reps=std::stoul(argv[6]);
 require((method=="KSSD"||method=="GreedyMini"||method=="mod-minimizer")&&k>=1&&k<=31&&w>0&&w<=50&&reps>0,"invalid args");
 require(!std::filesystem::exists(prefix+".json")&&!std::filesystem::exists(prefix+".positions.u64"),"refuse existing outputs");
 auto load_start=Clock::now();std::ifstream f(input,std::ios::binary|std::ios::ate);require(bool(f),"input open");size_t n=(size_t)f.tellg();require(n>0&&n<=300000000,"input exceeds authorized maximum 300Mb");f.seekg(0);std::vector<uint8_t> dna(n);f.read((char*)dna.data(),n);require(bool(f),"input read");double io_sec=secs(load_start);
 std::vector<Run> runs;size_t start=0;for(size_t i=0;i<=n;++i){if(i<n&&lut[dna[i]]<4)continue;if(i>start)runs.push_back({start,i});start=i+1;}
 auto alloc=Clock::now();std::vector<uint64_t> out(n,0);double output_allocation=secs(alloc);
 kssd_array_t ctx=KSSD_ARRAY_CONTEXT_INIT;std::vector<uint64_t> table;void* mod=nullptr;size_t k0=k;
 auto setup=Clock::now();
 if(method=="KSSD")require(kssd_array_init(&ctx,k,42)==KSSD_ARRAY_OK,"KSSD init");
 else if(method=="GreedyMini"){k0=w==20?12:15;require(k>=k0&&(w==5||w==10||w==20),"unsupported greedy pair");table=load_vector_from_file(third+"/GreedyMini/minimizer loading example/w"+std::to_string(w)+"_k"+std::to_string(k0)+".gm");require(table.size()==(1ULL<<k0),"order size");for(auto r:table)require(r<=table.size(),"rank out of range");}
 else mod=ld_mod_init(k,w);
 double setup_seconds=secs(setup);std::vector<double> times;std::vector<std::string> checksums;size_t expected_count=0;Stats stats;double warmup_seconds=0;
 for(size_t rep=0;rep<=reps;++rep){auto a=Clock::now();size_t count;
  if(method=="KSSD")count=sample_order<false>(dna,k,w,ctx,table,k0,out.data());
  else if(method=="GreedyMini")count=sample_order<true>(dna,k,w,ctx,table,k0,out.data());
  else count=ld_mod_sample(mod,dna.data(),dna.size(),out.data());
  double elapsed=secs(a);require(count<=n,"output capacity");
  // All verification, checksum, statistics, and file IO occur after stopping timer.
  auto s=check(runs,k,w,out.data(),count);auto h=digest(out.data(),count*sizeof(uint64_t));
  if(rep==0){expected_count=count;stats=s;warmup_seconds=elapsed;}else{require(count==expected_count&&h==checksums.front(),"nondeterministic output");times.push_back(elapsed);}
  checksums.push_back(h);
  std::cerr<<method<<" k="<<k<<" w="<<w<<" rep="<<rep<<" seconds="<<elapsed<<" count="<<count<<"\n";
 }
 std::ofstream p(prefix+".positions.u64",std::ios::binary);p.write((char*)out.data(),expected_count*sizeof(uint64_t));require(bool(p),"output write");p.close();
 std::ofstream j(prefix+".json");j<<std::setprecision(17)<<"{\n\"method\":\""<<method<<"\",\"k\":"<<k<<",\"w\":"<<w<<",\"bases\":"<<n<<",\"valid_bases\":"<<stats.valid<<",\"valid_kmers\":"<<stats.kmers<<",\"valid_windows\":"<<stats.windows<<",\"valid_runs\":"<<runs.size()<<",\"selected_count\":"<<expected_count<<",\"density\":"<<(stats.kmers?double(expected_count)/stats.kmers:0)<<",\"density_factor\":"<<(stats.kmers?double(expected_count)*(w+1)/stats.kmers:0)<<",\"mean_spacing\":"<<stats.gapmean<<",\"median_spacing\":"<<stats.median<<",\"p95_spacing\":"<<stats.p95<<",\"p99_spacing\":"<<stats.p99<<",\"max_gap\":"<<stats.maxgap<<",\"gap_count\":"<<stats.gaps<<",\"peak_process_rss_kib\":"<<rss()<<",\"warmup_seconds\":"<<warmup_seconds<<",\"method_setup_seconds\":"<<setup_seconds<<",\"output_allocation_seconds\":"<<output_allocation<<",\"input_io_seconds\":"<<io_sec<<",\"cpu\":"<<sched_getcpu()<<",\"output_sha256\":\""<<checksums.front()<<"\",\"output_bytes\":"<<expected_count*8<<",\"runtime_seconds\":[";
 for(size_t x=0;x<times.size();++x){if(x)j<<',';j<<times[x];}j<<"],\"checksums\":[";for(size_t x=0;x<checksums.size();++x){if(x)j<<',';j<<'\"'<<checksums[x]<<'\"';}j<<"],\"gap_histogram\":[";for(size_t x=0;x<stats.hist.size();++x){if(x)j<<',';j<<stats.hist[x];}j<<"]}\n";require(bool(j),"json write");
 if(mod)ld_mod_destroy(mod);kssd_array_destroy(&ctx);return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
