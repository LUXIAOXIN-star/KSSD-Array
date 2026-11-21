#!/usr/bin/env python3
"""Isolated Phase3 ntHash benchmark; explicit inputs and new output required.

The smoke mode uses a user-supplied small FASTA and compares score/selection
checksums to a separate slow oracle. Formal mode is explicit and executes the
original 40 practical conditions with five paired repeats per process.
"""
import argparse,csv,hashlib,json,os,pathlib,random,subprocess,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
PACKAGE=HERE.parents[1]
SRC=HERE/'frozen_worktree'; NTHASH=HERE/'third_party/nthash'
SYNTH='a7eca29bdfa06ff373048fffa7a90139afc98acfa938a8ec0a98459608045962'
HUMAN='df6e4918316e05a9cc1fd29c352841d3678b607d7a436819cd43371b52c814c0'
KS=(15,19,21,24,31);WS=(5,10,20,50)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def fail(msg):raise RuntimeError(msg)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--mode',choices=['smoke','formal'],required=True)
 p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--cpu',type=int,required=True)
 p.add_argument('--input',type=pathlib.Path);p.add_argument('--input-sha256')
 p.add_argument('--synthetic',type=pathlib.Path);p.add_argument('--human',type=pathlib.Path)
 a=p.parse_args();out=a.out.expanduser().resolve();output_parent=out.parent
 if out.exists():fail('output already exists')
 if not output_parent.is_dir():fail('output parent missing')
 if out==PACKAGE or PACKAGE in out.parents:fail('output must be outside source package')
 if a.cpu not in os.sched_getaffinity(0):fail('requested CPU not allowed')
 if a.mode=='smoke':
  if not a.input or not a.input_sha256 or a.synthetic or a.human:fail('smoke requires --input and --input-sha256 only')
  paths=[('SMOKE',a.input.expanduser().resolve(strict=True),a.input_sha256.lower())]
 else:
  if not a.synthetic or not a.human or a.input or a.input_sha256:fail('formal requires --synthetic and --human only')
  paths=[('Synthetic_300_Mb',a.synthetic.expanduser().resolve(strict=True),SYNTH),('GRCh38.p14_chr1',a.human.expanduser().resolve(strict=True),HUMAN)]
 for name,path,expected in paths:
  if not path.is_file() or path.is_symlink():fail('input must be a regular file')
  if out==path.parent or path.parent in out.parents:fail('output must be outside input directory')
  if sha(path)!=expected:fail('input SHA-256 mismatch: '+name)
 source_records=json.loads((HERE/'SOURCE_IDENTITIES.json').read_text())['sources']
 for row in source_records:
  path=HERE/row['path']
  if not path.is_file() or sha(path)!=row['sha256']:fail('source identity mismatch: '+row['path'])
 # Exclusive directory creation leaves partial logs in place on failure.
 out.mkdir(exist_ok=False);logs=out/'logs';logs.mkdir();build=out/'build';build.mkdir()
 manifest={'mode':a.mode,'cpu':a.cpu,'input':[{ 'dataset':n,'path':str(path),'sha256':h} for n,path,h in paths],
 'source':source_records,'launcher_sha256':sha(pathlib.Path(__file__).resolve()),'oracle_sha256':sha(HERE/'oracle_small.cpp'),'nthash':'2.4.0 c26bd4572a19de81e30d55042dbd33c1fd21d4b6','ks':list(KS),'ws':list(WS),'seed':42,'repeats':5,'repeat_unit':'paired technical repeats in one process','condition_order':'random.Random(42).shuffle','commands':[],'status':'STARTED'}
 def save():
  (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 def run(cmd,name):
  cmd=[str(x) for x in cmd];res=subprocess.run(cmd,cwd=str(build),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  (logs/(name+'.stdout')).write_text(res.stdout);(logs/(name+'.stderr')).write_text(res.stderr)
  manifest['commands'].append({'argv':cmd,'exit_code':res.returncode,'stdout':'logs/'+name+'.stdout','stderr':'logs/'+name+'.stderr'});save()
  if res.returncode:fail(name+' failed with exit '+str(res.returncode))
  return res.stdout
 try:
  manifest['compiler_c']=run(['cc','--version'],'cc_version').splitlines()[0]
  manifest['compiler_cxx']=run(['c++','--version'],'cxx_version').splitlines()[0]
  flags=['-O3','-march=native','-DNDEBUG','-Wall','-Wextra','-Wpedantic'];c=['-std=c11']+flags;cpp=['-std=c++17']+flags
  for name in ('kssd_array','permutation'):
   run(['cc',*c,'-I'+str(SRC/'include'),'-c',SRC/'src'/(name+'.c'),'-o',build/(name+'.o')],'compile_'+name)
  run(['ar','rcs',build/'libkssd_array.a',build/'kssd_array.o',build/'permutation.o'],'archive_kssd')
  for name in ('kmer','seed'):
   run(['c++',*cpp,'-I'+str(NTHASH/'include'),'-c',NTHASH/'src'/(name+'.cpp'),'-o',build/(name+'.o')],'compile_nthash_'+name)
  run(['ar','rcs',build/'libnthash.a',build/'kmer.o',build/'seed.o'],'archive_nthash')
  ks=(21,) if a.mode=='smoke' else KS
  for k in ks:
   bin=build/('practical_k'+str(k))
   run(['c++',*cpp,'-DK='+str(k),'-I'+str(SRC/'include'),'-I'+str(NTHASH/'include'),SRC/'reproducibility/reviewer_phase3/practical_nthash.cpp',build/'libkssd_array.a',build/'libnthash.a','-lz','-o',bin],'compile_practical_k'+str(k))
   val=run(['taskset','-c',a.cpu,bin,'--validate'],'validate_k'+str(k))
   if '\tPASS\t' not in val:fail('original fixture did not report PASS')
  if a.mode=='smoke':
   k=21;w=20;bin=build/'practical_k21';oracle=build/'oracle_small'
   run(['c++',*cpp,'-DK=21','-I'+str(SRC/'include'),'-I'+str(NTHASH/'include'),HERE/'oracle_small.cpp',build/'libkssd_array.a',build/'libnthash.a','-lz','-o',oracle],'compile_oracle')
   result=run(['taskset','-c',a.cpu,bin,paths[0][1],'SMOKE',w,5],'smoke_practical')
   expected=run([oracle,paths[0][1],w],'smoke_oracle')
   oracle_rows={r[0]:r for r in csv.reader(expected.splitlines(),delimiter='\t')};actual=[r for r in csv.reader(result.splitlines(),delimiter='\t') if r and r[0]=='PRACTICAL']
   if len(actual)!=10 or set(oracle_rows)!={'KSSD-Array','ntHash'}:fail('incorrect result row count or methods')
   for r in actual:
    ref=oracle_rows[r[6]]
    if int(r[14])!=int(ref[1]) or int(r[15])!=int(ref[2]) or [int(x,16) for x in r[17:20]]!=[int(x,16) for x in ref[3:6]]:fail('oracle checksum/count mismatch for '+r[6])
   manifest['small_oracle']='PASS: 10 method records against direct per-k-mer and O(nw) selector';manifest['status']='SMOKE_PASS'
  else:
   jobs=[(n,k,w,path) for n,path,_ in paths for k in KS for w in WS];random.Random(42).shuffle(jobs)
   raw=[]
   for idx,(label,k,w,path) in enumerate(jobs):
    s=run(['taskset','-c',a.cpu,build/('practical_k'+str(k)),path,label,w,5],'formal_'+str(idx).zfill(2))
    parsed=list(csv.reader(s.splitlines(),delimiter='\t'))
    rows=[r for r in parsed if r and r[0]=='PRACTICAL']
    meta=[r for r in parsed if r and r[0]=='META']
    expected_bases=300000000 if label=='Synthetic_300_Mb' else 230481012
    if len(meta)!=1 or int(meta[0][5])!=expected_bases:fail('unexpected processed valid base count in job '+str(idx))
    if len(rows)!=10:fail('unexpected number of method rows in job '+str(idx))
    for method in ('KSSD-Array','ntHash'):
     group=[r for r in rows if r[6]==method]
     if len(group)!=5 or {int(r[4]) for r in group}!={1,2,3,4,5} or len({tuple(r[14:20]) for r in group})!=1:fail('repetition or checksum inconsistency in job '+str(idx)+' '+method)
    raw.extend(rows)
   with (out/'practical_raw.tsv').open('x',newline='') as f:
    wr=csv.writer(f,delimiter='\t');wr.writerow(['record','dataset','k','w','repeat','order','method','score_seconds','window_seconds','total_seconds','score_M_per_s','window_M_per_s','score_cycles','window_cycles','scores','windows','selected','score_checksum','position_checksum','selected_score_checksum']);wr.writerows(raw)
   manifest['status']='FORMAL_COMPLETE';manifest['conditions']=len(jobs);manifest['raw_method_rows']=len(raw)
  save();print(json.dumps({'status':manifest['status'],'output':str(out)}))
 except BaseException as e:
  manifest['status']='FAILED';manifest['error']=str(e);save();raise
if __name__=='__main__':main()
