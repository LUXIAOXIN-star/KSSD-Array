#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <unordered_map>
#include <limits>
#include <chrono>
#include "kssd_array.h"
#include "kssd_array_inline.h"
using U=uint64_t;
inline U kmask(int k){return k==32?~U(0):(U(1)<<(2*k))-1;}
inline U mix64(U x){x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);}
struct RNG{U x;explicit RNG(U s):x(s){}U next(){x+=0x9e3779b97f4a7c15ULL;return mix64(x);}};
inline U mmhash(U x,U mask){x=(~x+(x<<21))&mask;x^=x>>24;x=((x+(x<<3))+(x<<8))&mask;x^=x>>14;x=((x+(x<<2))+(x<<4))&mask;x^=x>>28;return (x+(x<<31))&mask;}
inline int base(char c){switch(c){case'A':case'a':return 0;case'C':case'c':return 1;case'G':case'g':return 2;case'T':case't':return 3;default:return -1;}}
#include "frozen_tables.hpp"
#include <memory>
inline std::string fixed_config_dir="configs";
struct Hasher{
 int type,k;U mask,salt,a,b,salt64,a64,b64;
 std::unique_ptr<LoadedKssd> loaded;
 Hasher(const std::string&m,int kk,U seed):k(kk),mask(kmask(k)){
  if(seed!=42)throw std::runtime_error("only frozen configuration 42 allowed");
  std::ifstream f(fixed_config_dir+"/fixed_parameters.txt");
  if(!(f>>salt64>>a64>>b64)||!(a64&1))throw std::runtime_error("fixed parameters missing or invalid");
  salt=salt64&mask;a=a64&mask;b=b64&mask;
  if(m=="kssd_repo"){type=0;loaded=std::make_unique<LoadedKssd>(fixed_config_dir+"/kssd_k"+std::to_string(k)+"_seed42.bin",k);}
  else if(m=="xor")type=1;else if(m=="mul")type=2;else if(m=="affine")type=3;else if(m=="salted_mul")type=4;else if(m=="mix64")type=5;else if(m=="minimap_hash")type=6;else if(m=="identity")type=7;
  else if(m=="mul64"){type=8;salt=salt64;a=a64;b=b64;}
  else if(m=="affine64"){type=9;salt=salt64;a=a64;b=b64;}
  else if(m=="salted_mul64"){type=10;salt=salt64;a=a64;b=b64;}
  else throw std::runtime_error("bad method "+m);
 }
 Hasher(const Hasher&)=delete;
 U operator()(U x)const{switch(type){case 0:return (*loaded)(x);case 1:return x^salt;case 2:return (x*a)&mask;case 3:return (x*a+b)&mask;case 4:return ((x^salt)*a)&mask;case 5:return mix64(x^salt);case 6:return mmhash(x,mask);case 7:return x;case 8:return x*a64;case 9:return x*a64+b64;case 10:return (x^salt64)*a64;default:throw std::runtime_error("unknown method");}}
};
struct Block{U beg,end;};
struct Record{std::string id,header,seq;std::vector<U>x;std::vector<uint32_t>freq;std::vector<uint8_t>flags;std::vector<Block>blocks;int k=0;};
inline std::vector<Record> readfa(const std::string&path){std::ifstream f(path);if(!f)throw std::runtime_error("open "+path);std::vector<Record>r;std::string line;while(std::getline(f,line)){if(line.empty())continue;if(line[0]=='>'){Record q;q.header=line.substr(1);q.id=q.header.substr(0,q.header.find_first_of(" \t\r"));r.push_back(std::move(q));}else{if(r.empty())throw std::runtime_error("missing header");for(char c:line)if(c!=' '&&c!='\t'&&c!='\r')r.back().seq+=c;}}return r;}
template<class F>void foreach_kmer(const std::string&s,int k,F emit){U f=0,rc=0,mask=kmask(k);int valid=0;for(size_t i=0;i<s.size();++i){int b=base(s[i]);if(b<0){valid=0;f=rc=0;continue;}f=((f<<2)|b)&mask;rc=(rc>>2)|(U(3-b)<<(2*(k-1)));if(++valid>=k)emit(std::min(f,rc));}}
inline void encode(Record&r,int k){r.k=k;r.x.clear();r.flags.clear();r.blocks.clear();r.x.reserve(r.seq.size());r.flags.reserve(r.seq.size());U f=0,rc=0,mask=kmask(k),beg=0;int valid=0;int count[4]={0,0,0,0};double h[33];h[0]=0;for(int j=1;j<=k;j++){double p=double(j)/k;h[j]=-p*std::log2(p);}for(char c:r.seq){int b=base(c);if(b<0){if(r.x.size()>beg)r.blocks.push_back({beg,r.x.size()});beg=r.x.size();valid=0;f=rc=0;std::fill(count,count+4,0);continue;}if(valid>=k){int old=(f>>(2*(k-1)))&3;--count[old];}++count[b];f=((f<<2)|b)&mask;rc=(rc>>2)|(U(3-b)<<(2*(k-1)));if(++valid>=k){U id=std::min(f,rc);r.x.push_back(id);double e=h[count[0]]+h[count[1]]+h[count[2]]+h[count[3]];bool homo=*std::max_element(count,count+4)==k;r.flags.push_back(uint8_t(e<1.2)|(uint8_t(homo)<<1)|(uint8_t(id==0)<<2));}}if(r.x.size()>beg)r.blocks.push_back({beg,r.x.size()});}
template<class T>void writevec(std::ofstream&f,const std::vector<T>&v){f.write((const char*)v.data(),std::streamsize(v.size()*sizeof(T)));}
template<class T>void readvec(std::ifstream&f,std::vector<T>&v,size_t n){v.resize(n);f.read((char*)v.data(),std::streamsize(n*sizeof(T)));}
inline void save_record(const Record&r,const std::string&path){std::ofstream f(path,std::ios::binary);if(!f)throw std::runtime_error("write "+path);U magic=0x4b53534442494f31ULL,k=r.k,n=r.x.size(),nb=r.blocks.size();f.write((char*)&magic,8);f.write((char*)&k,8);f.write((char*)&n,8);f.write((char*)&nb,8);writevec(f,r.blocks);writevec(f,r.x);writevec(f,r.freq);writevec(f,r.flags);if(!f)throw std::runtime_error("write failed "+path);}
inline Record load_record(const std::string&path){Record r;std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error("open "+path);U magic,k,n,nb;f.read((char*)&magic,8);f.read((char*)&k,8);f.read((char*)&n,8);f.read((char*)&nb,8);if(!f||magic!=0x4b53534442494f31ULL||k<1||k>32)throw std::runtime_error("invalid cache");r.k=int(k);readvec(f,r.blocks,nb);readvec(f,r.x,n);readvec(f,r.freq,n);readvec(f,r.flags,n);if(!f)throw std::runtime_error("short cache");return r;}
inline std::vector<int> ints(const std::string&s){std::vector<int>a;std::stringstream ss(s);std::string t;while(std::getline(ss,t,','))a.push_back(std::stoi(t));return a;}
inline std::vector<std::string> strings(const std::string&s){std::vector<std::string>a;std::stringstream ss(s);std::string t;while(std::getline(ss,t,','))a.push_back(t);return a;}
