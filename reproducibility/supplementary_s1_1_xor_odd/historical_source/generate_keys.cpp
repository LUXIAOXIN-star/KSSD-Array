#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using U=uint64_t;
constexpr U MASK=(U(1)<<42)-1;
int base(char c){switch(c){case 'A':case 'a':return 0;case 'C':case 'c':return 1;case 'G':case 'g':return 2;case 'T':case 't':return 3;default:return -1;}}
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("usage: generate_keys REFERENCE_FASTA OUTPUT_KEYS");
 std::ifstream in(argv[1]);std::fstream out(argv[2],std::ios::binary|std::ios::out|std::ios::trunc);
 if(!in||!out)throw std::runtime_error("missing input/output");
 out.write("KN21NAT1",8);U total=0;out.write(reinterpret_cast<const char*>(&total),8);
 U f=0,rc=0,chrom_words=0,chrom_bases=0;int valid=0;std::string line,id;
 std::vector<U>buffer;buffer.reserve(1<<20);std::vector<std::string>ids;std::vector<U>counts,lengths;
 auto flush=[&](){out.write(reinterpret_cast<const char*>(buffer.data()),buffer.size()*8);if(!out)throw std::runtime_error("output write");buffer.clear();};
 auto close_chrom=[&](){if(!id.empty()){ids.push_back(id);counts.push_back(chrom_words);lengths.push_back(chrom_bases);}};
 while(std::getline(in,line)){
  if(line.empty())continue;
  if(line[0]=='>'){close_chrom();id=line.substr(1);id=id.substr(0,id.find_first_of(" \t\r"));f=rc=chrom_words=chrom_bases=0;valid=0;continue;}
  if(id.empty())throw std::runtime_error("FASTA sequence before header");
  for(char c:line){if(c=='\r'||c==' '||c=='\t')continue;chrom_bases++;int b=base(c);
   if(b<0){f=rc=0;valid=0;continue;}
   f=((f<<2)|U(b))&MASK;rc=(rc>>2)|(U(3-b)<<40);valid++;
   if(valid>=21){buffer.push_back(std::min(f,rc));total++;chrom_words++;if(buffer.size()==buffer.capacity())flush();}
  }
 }
 close_chrom();flush();out.seekp(8);out.write(reinterpret_cast<const char*>(&total),8);out.close();
 if(ids!=std::vector<std::string>{"chr21","chr22"}||total!=79246416ULL)throw std::runtime_error("reference scope/count mismatch");
 std::cout<<"{\"total_keys\":"<<total<<",\"records\":[";
 for(size_t i=0;i<ids.size();i++){if(i)std::cout<<',';std::cout<<"{\"id\":\""<<ids[i]<<"\",\"bases\":"<<lengths[i]<<",\"valid_canonical21_positions\":"<<counts[i]<<'}';}
 std::cout<<"]}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
