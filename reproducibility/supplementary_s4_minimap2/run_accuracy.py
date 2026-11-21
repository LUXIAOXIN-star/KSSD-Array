#!/usr/bin/env python3
"""Safely launch the recorded truth-origin analysis with external inputs.

No data are downloaded and no mapping benchmark is run. This wrapper checks
source identities and dependencies and forces a fresh output directory. It
cannot verify or replace missing original BAM, ART truth or reference inputs.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'reproducibility/minimap2/alignment_consistency_truth_origin'
EXPECTED={'run_corrected_s2_metrics.py':'426068083e3a6ae2469fc1635c708331d2e1de81f5e945603db75e83777e9dc9','s2_core.py':'aa9d10dc3a0f8f2e9228b332baff8d3b67ee7ff8516ff9de24544aae68465437','config.json':'00a0ff8f18d9b7fd941cfed27018b9eb791b77f2a0f1ff57645861174b0a4592'}
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--data-root',type=Path,required=True)
 p.add_argument('--accepted-dir',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True,help='new directory outside source and input roots')
 p.add_argument('--execute',action='store_true',help='run analysis after checks; default is check only')
 a=p.parse_args();out=a.output.expanduser().resolve();roots=[ROOT]
 if out.exists():p.error('output already exists; choose a new directory')
 if not out.parent.is_dir():p.error('output parent must exist')
 for path in (a.data_root,a.accepted_dir):
  try:resolved=path.expanduser().resolve(strict=True)
  except FileNotFoundError:p.error('input directory does not exist: '+str(path))
  if not resolved.is_dir():p.error('input path is not a directory: '+str(path))
  roots.append(resolved)
 if any(out==root or root in out.parents for root in roots):p.error('output must be outside source and input directories')
 errors=[]
 for name,expected in EXPECTED.items():
  path=WORK/name
  if not path.is_file():errors.append('missing retained historical source: '+name)
  elif digest(path)!=expected:errors.append('source checksum mismatch: '+name)
 if not (WORK/'tests/test_s2_core.py').is_file():errors.append('missing workflow unit tests')
 if (WORK/'config.json').is_file() and digest(WORK/'config.json')==EXPECTED['config.json']:
  config=json.loads((WORK/'config.json').read_text())
  required=[(roots[1]/config['art_readme_relative_path'],config['art_readme_size_bytes']), (roots[1]/config['art_aln2bed_relative_path'],config['art_aln2bed_size_bytes'])]
  for dataset in config['datasets']:
   for prefix in ('reference','repeat_bed'):required.append((roots[1]/dataset[prefix+'_relative_path'],dataset[prefix+'_size_bytes']))
   for condition in dataset['conditions']:
    for prefix in ('fastq','truth_tsv','truth_aln'):required.append((roots[1]/condition[prefix+'_relative_path'],condition[prefix+'_size_bytes']))
    for token in ('original','kssd-array'):
     for suffix in ('','-repeats'):
      required.append((roots[2]/'alignments'/f"{dataset['key']}-{int(condition['read_length'])}bp-{token}{suffix}.bam",None))
  for name in ('output_sha256.tsv','supplementary_alignment_raw.csv','supplementary_table_s2.csv'):required.append((roots[2]/name,None))
  for path,size in required:
   if not path.is_file():errors.append('required input missing: '+str(path))
   elif size is not None and path.stat().st_size!=int(size):errors.append('input size mismatch: '+str(path))
 if not shutil.which('samtools'):errors.append('samtools not available on PATH')
 check=subprocess.run([sys.executable,'-B','-c','import numpy; from scipy.stats import binom_test'],capture_output=True,text=True)
 if check.returncode:errors.append('compatible NumPy/SciPy unavailable; scipy.stats.binom_test must exist')
 if errors:
  for error in errors:print('BLOCKED: '+error,file=sys.stderr)
  return 2
 print('Source, dependency, file presence and recorded input-size checks passed; full BAM/truth/input SHA audit runs inside the retained analysis. No mapping is run.')
 if not a.execute:
  print('No analysis executed. Use --execute only with the correct inputs and a new output path.')
  return 0
 out.mkdir(exist_ok=False)
 cmd=[sys.executable,'-B',str(WORK/'run_corrected_s2_metrics.py'),'--config',str(WORK/'config.json'),'--data-root',str(roots[1]),'--accepted-dir',str(roots[2]),'--output-dir',str(out)]
 env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
 result=subprocess.run(cmd,cwd=out,env=env)
 if result.returncode:print('Analysis failed; partial output preserved at '+str(out),file=sys.stderr)
 return result.returncode
if __name__=='__main__':sys.exit(main())
