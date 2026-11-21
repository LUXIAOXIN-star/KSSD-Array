pub mod cli;
pub mod validation;

use std::{collections::VecDeque, ffi::c_void, ptr::NonNull, time::Instant};
use seq_hash::{KmerHasher, NtHasher, packed_seq::{AsciiSeq, PackedSeqVec, SeqVec, PaddedIt, ChunkIt, u32x8, intrinsics::transpose}};

pub type Result<T> = std::result::Result<T,String>;
pub const KS:[usize;3]=[19,21,31];
pub const STRICT_WS:[usize;3]=[9,19,49];
pub const WEAK_WS:[usize;3]=[10,20,50];

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub enum Mode { Strict, Weak }
impl Mode { pub fn name(self)->&'static str {match self {Self::Strict=>"strict",Self::Weak=>"weak"}} }
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub enum Method { Kssd, SeqHash, SimdMinimizers }
impl Method {
    pub fn name(self)->&'static str {match self {Self::Kssd=>"kssd",Self::SeqHash=>"seq-hash",Self::SimdMinimizers=>"simd-minimizers"}}
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub enum Experiment { A,B,C }
impl Experiment {pub fn name(self)->&'static str {match self {Self::A=>"rolling_score_benchmark",Self::B=>"common_selector_benchmark",Self::C=>"end_to_end_benchmark"}}}

#[derive(Clone)]
pub struct Dna { bytes:Vec<u8> }
impl Dna {
    pub fn new(bytes:Vec<u8>)->Result<Self> {
        if bytes.len()>=u32::MAX as usize {return Err("sequence exceeds the frozen u32 coordinate limit".into());}
        if bytes.iter().any(|b|!matches!(b,b'A'|b'C'|b'G'|b'T')) {return Err("DNA must contain only uppercase A/C/G/T; ambiguity is not silently deleted".into());}
        Ok(Self{bytes})
    }
    pub fn bytes(&self)->&[u8]{&self.bytes}
    pub fn len(&self)->usize{self.bytes.len()}
    pub fn is_empty(&self)->bool{self.bytes.is_empty()}
    pub fn reverse_complement(&self)->Self {
        Self{bytes:self.bytes.iter().rev().map(|b|match b {b'A'=>b'T',b'C'=>b'G',b'G'=>b'C',_=>b'A'}).collect()}
    }
}
pub fn parse_input(raw:&[u8],limit:usize)->Result<Dna> {
    let mut seq=vec![];let mut records=0;let mut plain=false;
    for line in raw.split(|&b|b==b'\n'){
        let line=line.strip_suffix(b"\r").unwrap_or(line);
        if line.is_empty(){continue}
        if line[0]==b'>' {
            records+=1;
            if records>1 || plain {return Err("single-record FASTA or plain DNA required; multiple records are never concatenated".into());}
            continue
        }
        if records==0 {plain=true;}
        for b in line.iter().filter(|b|!b.is_ascii_whitespace()){
            let b=b.to_ascii_uppercase();
            if !matches!(b,b'A'|b'C'|b'G'|b'T') {return Err("non-ACGT input rejected; no ambiguity joining or silent remapping".into());}
            if seq.len()>=limit {return Err(format!("input exceeds {limit} bases; large runs require explicit --allow-large"));}
            seq.push(b);
        }
    }
    Dna::new(seq)
}
pub fn score_count(n:usize,k:usize)->usize {n.checked_sub(k).map_or(0,|x|x+1)}
pub fn window_count(n:usize,k:usize,w:usize)->usize {n.checked_sub(k+w-1).map_or(0,|x|x+1)}
pub fn validate_params(k:usize,w:Option<usize>,mode:Mode)->Result<()> {
    if !KS.contains(&k){return Err("frozen k matrix is {19,21,31}".into())}
    if let Some(w)=w {
        let allowed=if mode==Mode::Strict {STRICT_WS}else{WEAK_WS};
        if !allowed.contains(&w){return Err(format!("frozen {} w matrix is {allowed:?}",mode.name()))}
        if mode==Mode::Strict && (k+w-1)%2!=1 {return Err("strict canonical requires odd k+w-1".into())}
    }
    Ok(())
}

unsafe extern "C" {
    fn review_context_create(k:usize,seed:u64)->*mut c_void;
    fn review_context_destroy(ctx:*mut c_void);
    fn review_reference_map(ctx:*const c_void,word:u64,score:*mut u64)->i32;
    fn review_table_checksum(ctx:*const c_void)->u64;
    fn review_scores_19(ctx:*const c_void,s:*const u8,n:usize,out:*mut u64,cap:usize)->usize;
    fn review_scores_21(ctx:*const c_void,s:*const u8,n:usize,out:*mut u64,cap:usize)->usize;
    fn review_scores_31(ctx:*const c_void,s:*const u8,n:usize,out:*mut u64,cap:usize)->usize;
    fn review_minimizers_19(ctx:*const c_void,s:*const u8,n:usize,w:usize,strict:i32,out:*mut u32,cap:usize)->usize;
    fn review_minimizers_21(ctx:*const c_void,s:*const u8,n:usize,w:usize,strict:i32,out:*mut u32,cap:usize)->usize;
    fn review_minimizers_31(ctx:*const c_void,s:*const u8,n:usize,w:usize,strict:i32,out:*mut u32,cap:usize)->usize;
}
pub struct Kssd {ctx:NonNull<c_void>, k:usize}
impl Kssd {
    pub fn new(k:usize)->Result<Self>{
        validate_params(k,None,Mode::Strict)?;
        let ctx=NonNull::new(unsafe{review_context_create(k,42)}).ok_or("KSSD table initialization failed")?;
        Ok(Self{ctx,k})
    }
    pub fn table_checksum(&self)->u64 {unsafe{review_table_checksum(self.ctx.as_ptr())}}
    pub fn reference_word(&self,word:u64)->Result<u64>{
        let mut score=0;
        let rc=unsafe{review_reference_map(self.ctx.as_ptr(),word,&mut score)};
        if rc!=0 {return Err(format!("original checked mapping rejected word: {rc}"))}
        Ok(score)
    }
    pub fn scores(&self,dna:&Dna)->Result<Vec<u64>> {
        let count=score_count(dna.len(),self.k);let mut v=vec![0;count];
        let f=match self.k {19=>review_scores_19,21=>review_scores_21,31=>review_scores_31,_=>unreachable!()};
        let got=unsafe{f(self.ctx.as_ptr(),dna.bytes().as_ptr(),dna.len(),v.as_mut_ptr(),v.len())};
        if got!=count {return Err("KSSD score adapter returned a wrong count".into())}
        Ok(v)
    }
    pub fn minimizers(&self,dna:&Dna,w:usize,mode:Mode)->Result<Vec<u32>> {
        validate_params(self.k,Some(w),mode)?;
        if window_count(dna.len(),self.k,w)==0{return Ok(vec![])}
        let mut v=Vec::<u32>::with_capacity(score_count(dna.len(),self.k));
        let f=match self.k {19=>review_minimizers_19,21=>review_minimizers_21,31=>review_minimizers_31,_=>unreachable!()};
        let count=unsafe{f(self.ctx.as_ptr(),dna.bytes().as_ptr(),dna.len(),w,i32::from(mode==Mode::Strict),v.as_mut_ptr(),v.capacity())};
        if count>v.capacity(){return Err("KSSD minimizer adapter failed".into())}
        // SAFETY: the audited C function initializes exactly count entries;
        // capacity is checked on both sides, and all inputs are validated DNA.
        unsafe{v.set_len(count)};
        Ok(v)
    }
}
impl Drop for Kssd {fn drop(&mut self){unsafe{review_context_destroy(self.ctx.as_ptr())}}}

// Losslessly widen and transpose public SIMD lanes directly to the common u64
// score stream. No full u32 intermediate and no per-k-mer cross-language call.
// Lane ordering follows the frozen packed-seq PaddedIt contract.
pub fn collect_u64(p:PaddedIt<impl ChunkIt<u32x8>>)->Vec<u64>{
    let PaddedIt{it,padding}=p;let len=it.len();
    let mut out=vec![0u64;len*8];let mut matrix=[u32x8::splat(0);8];let mut filled=0;
    for x in it {
        matrix[filled%8]=x;filled+=1;
        if filled%8==0 {
            let t=transpose(matrix);
            for lane in 0..8 {
                let arr=t[lane].to_array();let start=lane*len+filled-8;
                for j in 0..8 {out[start+j]=u64::from(arr[j]);}
            }
        }
    }
    let tail=filled%8;
    if tail!=0 {
        let t=transpose(matrix);
        for lane in 0..8 {
            let arr=t[lane].to_array();let start=lane*len+filled-tail;
            for j in 0..tail {out[start+j]=u64::from(arr[j]);}
        }
    }
    out.truncate(out.len()-padding);out
}

pub struct Engine {pub k:usize,pub kssd:Kssd,nt:NtHasher<true>,published_nt:simd_minimizers::seq_hash::NtHasher<true>}
impl Engine {
    pub fn new(k:usize)->Result<Self>{
        Ok(Self{k,kssd:Kssd::new(k)?,nt:NtHasher::<true>::new(k),published_nt:simd_minimizers::seq_hash::NtHasher::<true>::new(k)})
    }
    pub fn scores(&self,dna:&Dna,method:Method)->Result<Vec<u64>>{
        match method {
            Method::Kssd=>self.kssd.scores(dna),
            Method::SeqHash=>{
                if dna.len()<self.k {return Ok(vec![])}
                Ok(collect_u64(self.nt.hash_kmers_simd(AsciiSeq(dna.bytes()),1)))
            },
            Method::SimdMinimizers=>Err("use seq-hash for score-only A/B".into())
        }
    }
    pub fn published_scores(&self,dna:&Dna)->Vec<u64>{
        use simd_minimizers::seq_hash::KmerHasher;
        self.published_nt.hash_kmers_scalar(AsciiSeq(dna.bytes())).map(u64::from).collect()
    }
    pub fn scalar_nt_scores(&self,dna:&Dna)->Vec<u64>{self.nt.hash_kmers_scalar(AsciiSeq(dna.bytes())).map(u64::from).collect()}
    pub fn end_to_end(&self,dna:&Dna,method:Method,w:usize,mode:Mode)->Result<Vec<u32>>{
        validate_params(self.k,Some(w),mode)?;
        if window_count(dna.len(),self.k,w)==0{return Ok(vec![])}
        match method {
            Method::Kssd=>self.kssd.minimizers(dna,w,mode),
            Method::SimdMinimizers=>{
                let packed=PackedSeqVec::from_ascii(dna.bytes());
                let mut out=vec![];
                if mode==Mode::Strict {
                    simd_minimizers::canonical_minimizers(self.k,w).hasher(&self.published_nt).run(packed.as_slice(),&mut out);
                }else{
                    simd_minimizers::minimizers(self.k,w).hasher(&self.published_nt).run(packed.as_slice(),&mut out);
                }
                Ok(out)
            },
            Method::SeqHash=>Err("C uses method=simd-minimizers".into())
        }
    }
}

// Shared for BOTH methods in B; scores are always u64, with no truncation.
pub fn common_selector(dna:&Dna,scores:&[u64],k:usize,w:usize,mode:Mode)->Result<Vec<u32>>{
    validate_params(k,Some(w),mode)?;
    if scores.len()!=score_count(dna.len(),k){return Err("selector score count mismatch".into())}
    let mut out=vec![];
    let mut left=VecDeque::<usize>::with_capacity(w);
    let mut right=VecDeque::<usize>::with_capacity(w);
    let span=k+w-1;let mut tg=0usize;
    if mode==Mode::Strict && dna.len()>=span {tg=dna.bytes()[..span].iter().filter(|b|matches!(b,b'T'|b'G')).count();}
    for i in 0..scores.len(){
        while left.front().is_some_and(|&j|j+w<=i){left.pop_front();}
        while left.back().is_some_and(|&j|scores[j]>scores[i]){left.pop_back();}
        left.push_back(i);
        if mode==Mode::Strict {
            while right.front().is_some_and(|&j|j+w<=i){right.pop_front();}
            while right.back().is_some_and(|&j|scores[j]>=scores[i]){right.pop_back();}
            right.push_back(i);
        }
        if i+1>=w {
            let start=i+1-w;
            if mode==Mode::Strict && start>0 {
                tg-=usize::from(matches!(dna.bytes()[start-1],b'T'|b'G'));
                tg+=usize::from(matches!(dna.bytes()[start+span-1],b'T'|b'G'));
            }
            let pos=if mode==Mode::Weak || 2*tg>span {*left.front().unwrap()}else{*right.front().unwrap()} as u32;
            if out.last()!=Some(&pos){out.push(pos);}
        }
    }
    Ok(out)
}

pub struct Timed<T>{pub value:T,pub seconds:Option<f64>}
pub fn run_stage<T>(measure:bool,f:impl FnOnce()->Result<T>)->Result<Timed<T>>{
    if measure {
        let start=Instant::now();let value=f()?;std::hint::black_box(&value);
        Ok(Timed{value,seconds:Some(start.elapsed().as_secs_f64())})
    }else{Ok(Timed{value:f()?,seconds:None})}
}
pub fn checksum_u64(values:&[u64])->u64{
    values.iter().enumerate().fold(0u64,|h,(i,&v)|h.rotate_left(7).wrapping_add(v^(i as u64).wrapping_mul(0x9e3779b97f4a7c15)))
}
pub fn checksum_positions(values:&[u32])->u64{
    values.iter().enumerate().fold(0u64,|h,(i,&v)|h.rotate_left(7).wrapping_add(u64::from(v)^(i as u64).wrapping_mul(0x9e3779b97f4a7c15)))
}
