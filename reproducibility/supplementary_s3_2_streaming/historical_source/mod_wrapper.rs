use minimizers::{Params,SamplingScheme};
use minimizers::order::RandomO;
use minimizers::schemes::{ModP,M};
struct Handle { scheme:Box<dyn SamplingScheme> }
#[no_mangle]
pub extern "C" fn ld_mod_init(k:usize,w:usize)->*mut std::ffi::c_void {
 let scheme=ModP{r:4,t:0,lr:false,params:Box::new(M(RandomO))}.build(w,k,4);
 Box::into_raw(Box::new(Handle{scheme})) as *mut std::ffi::c_void
}
#[no_mangle]
pub unsafe extern "C" fn ld_mod_destroy(h:*mut std::ffi::c_void){drop(Box::from_raw(h as *mut Handle));}
fn decode(c:u8)->Option<u8>{match c{b'A'=>Some(0),b'C'=>Some(1),b'G'=>Some(2),b'T'=>Some(3),_=>None}}
#[no_mangle]
pub unsafe extern "C" fn ld_mod_sample(h:*mut std::ffi::c_void,dna:*const u8,n:usize,out:*mut u64)->usize{
 let h=&*(h as *const Handle);let raw=std::slice::from_raw_parts(dna,n);let sink=std::slice::from_raw_parts_mut(out,n);
 let mut used=0;let mut i=0;let mut text=Vec::new();
 while i<n {
  while i<n && decode(raw[i]).is_none(){i+=1;}
  let start=i;text.clear();
  while i<n {if let Some(c)=decode(raw[i]){text.push(c);i+=1;}else{break;}}
  if text.len()<h.scheme.l(){continue;}
  let winners=h.scheme.stream(&text);let mut last=usize::MAX;
  for x in winners {if x!=last {sink[used]=(start+x) as u64;used+=1;last=x;}}
 }
 used
}
