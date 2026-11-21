#pragma once
#include <cstddef>
#include <cstdint>
using Kernel=void(*)(const uint64_t*,uint64_t*,size_t,const uint16_t*);
void score_kssd(const uint64_t*,uint64_t*,size_t,const uint16_t*);
void score_xor(const uint64_t*,uint64_t*,size_t,const uint16_t*);
void score_bare42(const uint64_t*,uint64_t*,size_t,const uint16_t*);
void score_bare64(const uint64_t*,uint64_t*,size_t,const uint16_t*);
void copy_control(const uint64_t*,uint64_t*,size_t,const uint16_t*);
