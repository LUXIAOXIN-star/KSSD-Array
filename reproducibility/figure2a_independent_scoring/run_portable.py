#!/usr/bin/env python3
"""Run one isolated Figure 2a scoring condition using supplied frozen sources.

The historical phase1 source and its declared dependencies are included in
this directory. This wrapper checks identities, builds only in a fresh output
directory and never runs make clean.
"""
import argparse,ctypes,ctypes.util,hashlib,json,os,platform,shutil,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
CORE={'include/kssd_array.h':'3ae49f9ef0ba3f1f87b8076f173b7904fc2d7910539b8362849984b5e2b5c68c','include/kssd_array_fast.h':'b64c3a14b9df415dcc73eebde920c113518fec46b26862b848491b4ca3cde5f4','include/kssd_array_inline.h':'7830431d6ebbb99c4833458a3f2863ed6f11de86dbd74378d583690955c285bf','src/kssd_array.c':'ce897b959e7ecdad52987af46ada62c2634172472176c90d9c344e0cfa9a9491','src/permutation.c':'7c2f7b42d17630d64d09bff88626a34c5e730cffa0531e370e9216dc432f9192','src/permutation.h':'3c67601c47b0246c58e5961e0a1b2c1e1fc8f2ad08298ce7c31ddd102317ff5b'}
PHASE={'phase1_benchmark.c':'6356f0ecc301afc03813fdfd95a58f4b8ca49c53db9892e3efa46aec3a4e4a63','accepted_xxhash_shared.c':'0c44fe2694f5ca8d263a8da6a3d9c3ccce02b8649c7f8ec887a42feea8a26996','accepted_xxhash_shared.h':'4af115c9bb2b42e6a09f71934693dbf99305ad243448eca672eb3e25080183b4','third_party/xxhash-v0.8.3/xxhash.h':'17973c0dc49d9854ca26caa191f0e12f7a424b68858d9a78de3860d959d85e4b'}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--phase1-dir',type=Path,required=True,help='frozen Phase 1 source directory (this directory may be used)')
 p.add_argument('--fasta',type=Path,required=True);p.add_argument('--fasta-sha256',required=True)
 p.add_argument('--expected-valid-bases',type=int,required=True);p.add_argument('--dataset',required=True)
 p.add_argument('--output',type=Path,required=True);p.add_argument('--k',type=int,choices=[16,19,21,24,31],required=True)
 p.add_argument('--repeats',type=int,default=5);p.add_argument('--warmup',type=int,choices=[0,1],default=1);p.add_argument('--cpu',type=int)
 p.add_argument('--cc',default='cc');a=p.parse_args();src=a.phase1_dir.expanduser().resolve(strict=True);inp=a.fasta.expanduser().resolve(strict=True);out=a.output.expanduser().resolve()
 if not src.is_dir() or not inp.is_file() or digest(inp)!=a.fasta_sha256.lower():p.error('source directory or FASTA SHA mismatch')
 if out.exists() or any(out==x or x in out.parents for x in (ROOT,src,inp.parent)):p.error('output must be new and outside source and input directories')
 if a.expected_valid_bases<a.k or not 1<=a.repeats<=1000:p.error('invalid length or repeat count')
 if '\t' in a.dataset or '\n' in a.dataset or not a.dataset:p.error('dataset label must be nonempty single field')
 if a.cpu is not None and a.cpu not in os.sched_getaffinity(0):p.error('CPU not allowed by current affinity')
 for folder,files in [(ROOT,CORE),(src,PHASE)]:
  for n,h in files.items():
   if not (folder/n).is_file() or digest(folder/n)!=h:p.error('frozen source SHA mismatch: '+n)
 libname=ctypes.util.find_library('xxhash')
 if not libname:p.error('shared xxHash unavailable')
 lib=ctypes.CDLL(libname);lib.XXH_versionNumber.restype=ctypes.c_uint
 if lib.XXH_versionNumber()!=703:p.error('requires original shared xxHash 0.7.3')
 for exe in (a.cc,'ar'):
  if not shutil.which(exe):p.error('missing executable: '+exe)
 out.mkdir(parents=True,exist_ok=False);work=out/'work';work.mkdir();(out/'logs').mkdir()
 m={'status':'RUNNING','start_utc':datetime.now(timezone.utc).isoformat(),'protocol':'Figure2a preencoded score only; historical full method set',
 'input_sha256':digest(inp),'expected_valid_bases':a.expected_valid_bases,'dataset':a.dataset,'k':a.k,'repeats':a.repeats,'warmup':a.warmup,'cpu':a.cpu,
 'allowed_cpus':sorted(os.sched_getaffinity(0)),'source_sha256':{'core':CORE,'phase1':PHASE},'shared_xxhash_version':703,
 'platform':platform.platform(),'commands':[],'note':'one-condition run; technical repeats within one process; SHA-verified source directory supplied by reader'}
 def save():(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 def run(cmd,name):
  m['commands'].append(cmd);save();r=subprocess.run(cmd,cwd=work,capture_output=True,text=True)
  (out/'logs'/(name+'.json')).write_text(json.dumps({'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2)+'\n')
  if r.returncode:raise RuntimeError(name+' failed: see logs')
  return r.stdout
 save()
 try:
  m['compiler_version']=run([a.cc,'--version'],'compiler').splitlines()[0]
  for folder,files in ((ROOT,CORE),(src,PHASE)):
   for n,h in files.items():
    dst=work/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(folder/n,dst)
    if digest(dst)!=h:raise RuntimeError('copy SHA mismatch: '+n)
  for n in ('kssd_array','permutation'):
   run([a.cc,'-Iinclude','-O3','-march=native','-std=c11','-Wall','-Wextra','-Wpedantic','-fPIC','-c','src/'+n+'.c','-o',n+'.o'],'compile_'+n)
  run(['ar','rcs','libkssd_array.a','kssd_array.o','permutation.o'],'archive')
  run([a.cc,'-O3','-march=native','-std=c11','-Wall','-Wextra','-Wpedantic','-fopenmp','-DK='+str(a.k),'-Iinclude','-Isrc','-I.',
   'phase1_benchmark.c','accepted_xxhash_shared.c','-L.','-Wl,-Bstatic','-lkssd_array','-Wl,-Bdynamic','-lxxhash','-lm','-fopenmp','-o','benchmark'],'compile_driver')
  m['binary_sha256']=digest(work/'benchmark')
  if shutil.which('ldd'):
   linked=run(['ldd',str(work/'benchmark')],'linked_libraries')
   row=next((x for x in linked.splitlines() if 'libxxhash.so.0 =>' in x),'')
   if not row:raise RuntimeError('expected dynamic shared xxHash not found')
   target=Path(row.split('=>',1)[1].strip().split()[0])
   if not target.is_file():raise RuntimeError('cannot resolve linked xxHash library')
   m['resolved_xxhash_path']=str(target.resolve());m['resolved_xxhash_sha256']=digest(target)
  command=[str(work/'benchmark'),'--mode','mapping','--input',str(inp),'--dataset',a.dataset,'--expected-valid-bases',str(a.expected_valid_bases),'--widths','10,20,50','--threads','1,2,4,8,16','--repeats',str(a.repeats),'--warmup',str(a.warmup)]
  if a.cpu is not None:command=['taskset','-c',str(a.cpu)]+command
  text=run(command,'run');meta=[x.split('\t') for x in text.splitlines() if x.startswith('META\t')];raw=[x.split('\t') for x in text.splitlines() if x.startswith('MAPPING\t')]
  if len(meta)!=1 or int(meta[0][2])!=a.k or int(meta[0][3])!=a.expected_valid_bases or int(meta[0][7])!=803 or int(meta[0][8])!=703:raise RuntimeError('input metadata, k or xxHash versions mismatch')
  if len(raw)!=15*a.repeats:raise RuntimeError('unexpected method/technical-repeat count')
  needed={'KSSD-Array-RankDerived','XXH3-pinned-inline','XXH64-pinned-inline','MurmurHash3','wyhash'}
  per={}
  for row in raw:
   if len(row)<19 or int(row[2])!=a.k or int(row[7])!=a.expected_valid_bases-a.k+1:raise RuntimeError('mapping output fields/count mismatch')
   key=(row[5],int(row[3]));per[key]=row[-3:]
  if not all((name,n) in per for name in needed for n in range(1,a.repeats+1)):raise RuntimeError('missing required method/repetition')
  for name in {key[0] for key in per}:
   if len({tuple(per[(name,n)]) for n in range(1,a.repeats+1)})!=1:raise RuntimeError('checksum mismatch across repeats: '+name)
  m.update({'status':'PASS_CONDITION','mapping_rows':len(raw),'input_checksum':meta[0][6],'results':{'/'.join(map(str,k)):v for k,v in per.items()},'end_utc':datetime.now(timezone.utc).isoformat()});save()
  print('PASS: Figure 2a isolated condition; output:',out)
 except Exception as e:
  m.update({'status':'FAILED','error':str(e)});save();print('FAILED:',e,file=sys.stderr);return 1
 return 0
if __name__=='__main__':sys.exit(main())
