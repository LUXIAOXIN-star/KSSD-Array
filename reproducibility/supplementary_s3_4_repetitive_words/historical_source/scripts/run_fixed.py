from pathlib import Path
import json,subprocess,sys,time,hashlib
from concurrent.futures import ThreadPoolExecutor
R=Path(__file__).resolve().parents[1]
phase=sys.argv[1] if len(sys.argv)>1 else 'primary'
ws={'primary':[20],'sensitivity10':[10],'sensitivity50':[50]}[phase]
methods=(['kssd_repo','xor','mul','mul64','affine','affine64','salted_mul','salted_mul64','mix64','minimap_hash','identity'] if phase=='primary' else ['kssd_repo','xor','mul','mul64','salted_mul64'])
inputs=json.loads((R/'input_manifest.json').read_text())
config_bytes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in (R/'configs').iterdir()if p.is_file()}
jobs=[]
for dataset in inputs:
 for rec in dataset['records']:
  for w in ws:
   id=f"{phase}_{dataset['label']}_{rec['accession']}_w{w}"
   out=R/'results'/f'{id}.csv';log=R/'logs'/f'{id}.log'
   cmd=[str(R/'build/analyze'),'--cache',str(R/'cache'/f"{dataset['label']}_k21"/f"{rec['accession']}.bin"),'--configs',str(R/'configs'),'--label',dataset['label'],'--record',rec['accession'],'--out',str(out),'--seeds','42','--ws',str(w),'--eval-w',str(w),'--tie','left','--methods',','.join(methods),'--distinct','1']
   jobs.append((id,cmd,out,log))
def job(t):
 id,cmd,out,log=t;start=time.time()
 with log.open('w')as f:
  p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(f'{id} failed with {p.returncode}')
 return {'job':id,'command':cmd,'operational_seconds':time.time()-start,'status':p.returncode,'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
with ThreadPoolExecutor(max_workers=2)as ex:
 results=list(ex.map(job,jobs))
assert config_bytes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in (R/'configs').iterdir()if p.is_file()},'a frozen configuration changed'
(R/'logs'/f'{phase}_manifest.json').write_text(json.dumps({'phase':phase,'warning':'Concurrent instrumented diagnostic jobs; durations are not comparative performance timings.','config_sha256':config_bytes,'jobs':results},indent=2))
print(phase,'completed',len(results),'jobs; all configuration bytes unchanged')
