#include "kernels.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <time.h>
#include <vector>
using U=uint64_t;
volatile U observed=0;
struct Buffer{U*ptr;size_t size;explicit Buffer(size_t n):ptr(nullptr),size(n){if(posix_memalign(reinterpret_cast<void**>(&ptr),64,n*sizeof(U)))throw std::bad_alloc();}~Buffer(){std::free(ptr);}};
std::array<uint16_t,16384>load_table(const char*path){std::ifstream f(path,std::ios::binary);std::array<uint16_t,16384>p;std::array<bool,16384>seen{};for(auto&x:p){unsigned char b[2];f.read(reinterpret_cast<char*>(b),2);x=U(b[0])|(U(b[1])<<8);if(!f||x>=16384||seen[x])throw std::runtime_error("invalid P7 table");seen[x]=true;}if(f.peek()!=EOF)throw std::runtime_error("P7 length");return p;}
double cpu_now(){timespec t;if(clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&t))throw std::runtime_error("CPU clock");return double(t.tv_sec)+double(t.tv_nsec)*1e-9;}
std::array<U,2>digest(const U*p,size_t n){U sum=0,x=0;for(size_t i=0;i<n;i++){sum+=p[i];x^=p[i]+U(i)*0x9e3779b97f4a7c15ULL;}observed=sum^x;return {sum,x};}
int main(int argc,char**argv){try{
 if(argc!=5)throw std::runtime_error("usage: hash_bench KEYS P7 OUTPUT_DIR BUILD_LABEL");
 std::ifstream in(argv[1],std::ios::binary);char magic[8];U n=0;in.read(magic,8);in.read(reinterpret_cast<char*>(&n),8);
 if(!in||std::string(magic,8)!="KN21NAT1"||n!=79246416ULL)throw std::runtime_error("natural keys header/count");
 Buffer input(n),output(n);in.read(reinterpret_cast<char*>(input.ptr),n*8);if(!in||in.peek()!=EOF)throw std::runtime_error("keys length");
 auto p=load_table(argv[2]);const std::array<Kernel,5>kernels={score_kssd,score_xor,score_bare42,score_bare64,copy_control};
 const std::array<std::string,5>names={"kssd_array","xor","bare42","bare64","copy_control"};
 std::string dir=argv[3],build=argv[4];
 std::ofstream measured(dir+"/timings_"+build+".csv"),samples(dir+"/score_samples_"+build+".csv"),warm(dir+"/warmup_"+build+".csv");
 if(!measured||!samples||!warm)throw std::runtime_error("output directory must exist");
 measured<<"build,dataset,cycle,position,order,method,n_keys,sweeps,n_evaluations,cpu_seconds,wall_seconds,cpu_ns_per_key,wall_ns_per_key,logical_read_write_GB_per_cpu_second,digest_sum_u64,digest_index_xor_u64\n"<<std::setprecision(17);
 samples<<"build,dataset,method,dataset_ordinal,input_ordinal,key,score\n";warm<<"build,dataset,method,n_keys,sweeps,digest_sum_u64,digest_index_xor_u64\n";
 Buffer hot_input(16384),hot_output(16384);
 for(U j=0;j<16384;j++)hot_input.ptr[j]=input.ptr[((2*j+1)*n)/(2*16384)];
 for(int dataset=0;dataset<2;dataset++){
  std::string dataset_name=dataset==0?"full_natural_stream":"private_cache_midpoint16384";
  U count=dataset==0?n:16384,sweeps=dataset==0?1:8192;
  U*keys=dataset==0?input.ptr:hot_input.ptr;U*values=dataset==0?output.ptr:hot_output.ptr;
  std::array<std::array<U,2>,5>expected;
  // One complete measured-size warmup per method/dataset. Digests and samples
  // occur outside all timers. All sweeps still execute the real output stores.
  for(int m=0;m<5;m++){
   for(U s=0;s<sweeps;s++){asm volatile("":::"memory");kernels[m](keys,values,count,p.data());}
   expected[m]=digest(values,count);warm<<build<<','<<dataset_name<<','<<names[m]<<','<<count<<','<<sweeps<<','<<expected[m][0]<<','<<expected[m][1]<<'\n';
   for(U z=0;z<4096;z++){U i=(z*(count-1))/4095;U ordinal=dataset==0?i:((2*i+1)*n)/(2*16384);samples<<build<<','<<dataset_name<<','<<names[m]<<','<<i<<','<<ordinal<<','<<keys[i]<<','<<values[i]<<'\n';}
  }
  std::array<int,4>order={0,1,2,3};int cycle=0;
  do{cycle++;std::string label;for(int m:order){if(!label.empty())label+='>';label+=names[m];}
   auto run=[&](int m,int position){asm volatile("":::"memory");double c0=cpu_now();auto w0=std::chrono::steady_clock::now();
    for(U s=0;s<sweeps;s++){asm volatile("":::"memory");kernels[m](keys,values,count,p.data());}
    auto w1=std::chrono::steady_clock::now();double c1=cpu_now();asm volatile("":::"memory");
    double cpu=c1-c0,wall=std::chrono::duration<double>(w1-w0).count();auto d=digest(values,count);if(d!=expected[m])throw std::runtime_error("measured output differs from full warmup digest");U evaluations=count*sweeps;
    measured<<build<<','<<dataset_name<<','<<cycle<<','<<position<<','<<label<<','<<names[m]<<','<<count<<','<<sweeps<<','<<evaluations<<','<<cpu<<','<<wall<<','<<cpu*1e9/evaluations<<','<<wall*1e9/evaluations<<','<<double(evaluations)*16/cpu/1e9<<','<<d[0]<<','<<d[1]<<'\n';measured.flush();};
   for(int pos=0;pos<4;pos++)run(order[pos],pos+1);
   // A load/store diagnostic, not a fifth hash baseline and not subtracted.
   run(4,5);std::cerr<<build<<' '<<dataset_name<<" completed balanced order "<<cycle<<"/24\n";
  }while(std::next_permutation(order.begin(),order.end()));
 }
 return 0;
}catch(const std::exception&e){std::cerr<<"ERROR: "<<e.what()<<'\n';return 1;}}
