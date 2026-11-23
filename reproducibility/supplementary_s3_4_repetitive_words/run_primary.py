#!/usr/bin/env python3
"""Reproduce the Table S8 primary condition using frozen historical kernels."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from decimal import Decimal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / 'historical_source'
HISTORICAL = ROOT / 'benchmark_results/supplementary_s3_4_repetitive_words/fixed_per_record.csv'
EXPECT = ROOT / 'benchmark_results/supplementary_s3_4_repetitive_words/fixed_primary_nuclear.csv'
METHODS = ['kssd_repo', 'xor', 'mul', 'mul64']

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def checked_run(cmd, log, cwd):
    print('RUN', ' '.join(map(str, cmd)), flush=True)
    with log.open('w') as f:
        f.write('$ ' + ' '.join(map(str, cmd)) + '\n'); f.flush()
        result = subprocess.run(list(map(str, cmd)), cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
        f.write('\nexit_code=' + str(result.returncode) + '\n')
    if result.returncode:
        raise RuntimeError('Command failed; see ' + str(log))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--yeast', type=Path, required=True, help='Exact historical yeast FASTA or gzip')
    ap.add_argument('--arabidopsis', type=Path, required=True, help='Exact historical Arabidopsis FASTA or gzip')
    ap.add_argument('--out', type=Path, required=True, help='New output directory outside this repository')
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() or out == ROOT or ROOT in out.parents or out in ROOT.parents:
        raise SystemExit('Output must be a new directory outside the repository')
    inputs = {'yeast': args.yeast.resolve(), 'arabidopsis': args.arabidopsis.resolve()}
    if any(not p.is_file() or out in p.parents for p in inputs.values()):
        raise SystemExit('Input file missing or inside the output directory')
    out.mkdir(parents=True)
    for name in ('build','logs','cache','results','configs'):
        (out/name).mkdir()
    provenance = {'status':'STARTED', 'inputs':{}, 'k':21, 'w':20, 'tau':50,
                  'seed':42, 'tie':'left', 'methods':METHODS,
                  'description':'primary condition; all reference records determine frequency; nuclear rows form the summary'}
    (out/'run_manifest.json').write_text(json.dumps(provenance, indent=2)+'\n')
    with (SOURCE/'SOURCE_SHA256.tsv').open(newline='') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if sha(SOURCE/row['path']) != row['sha256']:
                raise RuntimeError('Frozen source checksum mismatch: ' + row['path'])
    datasets = json.loads((SOURCE/'input_manifest.json').read_text())
    for d in datasets:
        src = inputs[d['label']]
        with src.open('rb') as probe: is_gzip = probe.read(2) == b'\x1f\x8b'
        rawhash = sha(src)
        if is_gzip and rawhash != d['gzip_sha256']:
            raise RuntimeError('Compressed FASTA checksum mismatch for ' + d['label'])
        if not is_gzip and rawhash != d['fasta_sha256']:
            raise RuntimeError('FASTA checksum mismatch for ' + d['label'])
        dest = out/'cache'/('input_'+d['label']+'.fna')
        h = hashlib.sha256()
        with (gzip.open(src,'rb') if is_gzip else src.open('rb')) as reader, dest.open('wb') as writer:
            for chunk in iter(lambda: reader.read(1024*1024), b''):
                h.update(chunk);writer.write(chunk)
        if h.hexdigest() != d['fasta_sha256']:
            raise RuntimeError('Decompressed FASTA checksum mismatch for ' + d['label'])
        provenance['inputs'][d['label']] = {'path':str(src),'input_sha256':rawhash,'fasta_sha256':h.hexdigest()}
    shutil.copyfile(SOURCE/'configs/fixed_parameters.txt',out/'configs/fixed_parameters.txt')
    shutil.copyfile(SOURCE/'configs/kssd_k21_seed42.bin',out/'configs/kssd_k21_seed42.bin')
    cc, cxx = os.environ.get('CC','gcc'), os.environ.get('CXX','g++')
    common = ['-O3','-std=c11','-Wall','-Wextra','-I'+str(SOURCE/'production/include'),'-I'+str(SOURCE/'production/src')]
    objects=[]
    for name in ('kssd_array','permutation'):
        obj=out/'build'/(name+'.o');objects.append(obj)
        checked_run([cc,*common,'-c',SOURCE/'production/src'/(name+'.c'),'-o',obj],out/'logs'/('build_'+name+'.log'),out)
    lib=out/'build/libkssd_array.a'
    checked_run(['ar','rcs',lib,*objects],out/'logs/build_ar.log',out)
    for name in ('prepare','analyze','freeze'):
        checked_run([cxx,'-O3','-std=c++17','-Wall','-Wextra','-I'+str(SOURCE/'production/include'),SOURCE/'scripts'/(name+'.cpp'),lib,'-o',out/'build'/name],out/'logs'/('build_'+name+'.log'),out)
    checked_run([out/'build/freeze','21',out/'configs/generated_k21.bin'],out/'logs/freeze.log',out)
    if sha(out/'configs/generated_k21.bin') != sha(SOURCE/'configs/kssd_k21_seed42.bin'):
        raise RuntimeError('Recreated k21 table differs from historical frozen table')
    for d in datasets:
        label=d['label']; dest=out/'cache'/(label+'_k21')
        checked_run([out/'build/prepare',out/'cache'/('input_'+label+'.fna'),'21',dest],out/'logs'/('prepare_'+label+'.log'),out)
        for rec in d['records']:
            accession=rec['accession']; target=out/'results'/('primary_'+label+'_'+accession+'_w20.csv')
            cmd=[out/'build/analyze','--cache',dest/(accession+'.bin'),'--configs',out/'configs','--label',label,'--record',accession,'--out',target,'--seeds','42','--ws','20','--eval-w','20','--tie','left','--methods',','.join(METHODS),'--distinct','1']
            checked_run(cmd,out/'logs'/('analyze_'+label+'_'+accession+'.log'),out)
    rows=[]
    for d in datasets:
        for rec in d['records']:
            path=out/'results'/('primary_'+d['label']+'_'+rec['accession']+'_w20.csv')
            with path.open(newline='') as f:
                for r in csv.DictReader(f):
                    r['phase']='primary';r['stratum']=rec['group'];rows.append(r)
    if len(rows)!=len(METHODS)*4*sum(len(d['records']) for d in datasets):
        raise RuntimeError('Unexpected output row count')
    with (out/'results/primary_per_record.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    key=['phase','dataset','record','method','hash_seed','k','w','tau']
    def kval(r):return tuple(r[k] for k in key)
    with HISTORICAL.open(newline='') as f:
        historical={kval(r):r for r in csv.DictReader(f) if r['phase']=='primary' and r['method'] in METHODS}
    if len(historical)!=len(rows):raise RuntimeError('Historical per-record row count mismatch')
    for row in rows:
        old=historical.get(kval(row))
        if old is None or any(row[c]!=old[c] for c in row):
            raise RuntimeError('Per-record mismatch: '+repr(kval(row)))
    with EXPECT.open(newline='') as f:
        old_summary={(r['dataset'],r['method']):r for r in csv.DictReader(f) if r['phase']=='primary' and r['stratum']=='nuclear' and r['tau']=='50' and r['w']=='20' and r['method'] in METHODS}
    if len(old_summary)!=8:raise RuntimeError('Expected eight historical summary rows')
    summary=[]
    for label in ('yeast','arabidopsis'):
        for method in METHODS:
            chosen=[r for r in rows if r['dataset']==label and r['stratum']=='nuclear' and r['method']==method and r['tau']=='50']
            num=sum(int(r['n_avoidable_highfreq']) for r in chosen);den=sum(int(r['n_mixed_windows']) for r in chosen)
            prior=old_summary[label,method];pct=Decimal(100)*num/den
            # Historical summary is written as a floating-point decimal; compare its full stored precision.
            if num!=int(prior['n_avoidable_highfreq']) or den!=int(prior['n_mixed_windows']) or abs(pct-Decimal(prior['avoidable_highcopy_pct']))>Decimal('0.000000000001'):
                raise RuntimeError('Historical summary mismatch: '+label+' '+method)
            summary.append({'dataset':label,'method':method,'n_avoidable_highfreq':num,'n_mixed_windows':den,'percentage':str(pct),'historical_percentage':prior['avoidable_highcopy_pct'],'match':'PASS'})
    with (out/'results/table_s8_comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    provenance['status']='PASS';provenance['per_record_rows_verified']=len(rows);provenance['summary_rows_verified']=len(summary)
    (out/'run_manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('PASS: 384 per-record rows and eight Table S8 rows match; output',out,flush=True)

if __name__=='__main__':
    try: main()
    except Exception as e:
        print('ERROR:',e,file=sys.stderr);sys.exit(1)
