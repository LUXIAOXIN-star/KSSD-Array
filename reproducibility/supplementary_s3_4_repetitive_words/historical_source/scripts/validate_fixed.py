from pathlib import Path
from collections import Counter
import ctypes,random,subprocess,csv,struct,math,json,re,hashlib,os
R=Path(__file__).resolve().parents[1];D=R/'cache'/'validation';D.mkdir(exist_ok=True)
E=int(os.environ.get("ASSESSMENT_W","20"))
MASK=(1<<64)-1
def mix(x):
 x=((x^(x>>30))*0xbf58476d1ce4e5b9)&MASK;x=((x^(x>>27))*0x94d049bb133111eb)&MASK;return x^(x>>31)
def params(seed,k):
 seq=[mix((seed+(i+1)*0x9e3779b97f4a7c15)&MASK) for i in range(3)];mask=(1<<(2*k))-1
 return seq[0]&mask,(seq[1]|1)&mask,seq[2]&mask
def mm(x,mask):
 x=(~x+(x<<21))&mask;x^=x>>24;x=(x+(x<<3)+(x<<8))&mask;x^=x>>14;x=(x+(x<<2)+(x<<4))&mask;x^=x>>28;return (x+(x<<31))&mask
def enc(s):
 a=0
 for c in s:a=(a<<2)|'ACGT'.index(c)
 return a
def canon(s):return min(enc(s),enc(s.translate(str.maketrans('ACGT','TGCA'))[::-1]))
rg=random.Random(9191)
raw=[''.join(rg.choices('ACGT',k=110))+'A'*110+'N'+'AT'*75+'nCGTnAC', 'aCgT'*32+'R'+'C'*80+''.join(rg.choices('ACGT',k=90)), 'AT'*90+'N'+'T'*100+'GATC'*24]
fixture=D/'fixture.fa';fixture.write_text(''.join(f'>r{i}\n{s}\n'for i,s in enumerate(raw)))
methods=['kssd_repo','xor','mul','mul64','affine','affine64','salted_mul','salted_mul64','mix64','minimap_hash','identity'];checks=0;rowcount=0;cachechecks=0
for k in [2,3,9,21,32]:
 cache=D/f'k{k}';subprocess.run([str(R/'build/prepare'),str(fixture),str(k),str(cache)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
 all_blocks=[[b for b in re.split('[^ACGT]',s.upper())if len(b)>=k]for s in raw]
 ids=[[[canon(b[j:j+k])for j in range(len(b)-k+1)]for b in bs]for bs in all_blocks];freq=Counter(x for rec in ids for bs in rec for x in bs)
 for rec in range(len(raw)):
  b=(cache/f'r{rec}.bin').read_bytes();magic,kk,n,nb=struct.unpack_from('<QQQQ',b);off=32+16*nb;observed=list(struct.unpack_from('<'+'Q'*n,b,off));off+=8*n;observedf=list(struct.unpack_from('<'+'I'*n,b,off));off+=4*n;flags=b[off:off+n];flat=[x for bs in ids[rec]for x in bs]
  assert observed==flat;assert observedf==[freq[x]for x in flat];cachechecks+=2*n
  for v,flag in zip(flat,flags):
   counts=Counter((v>>(2*t))&3 for t in range(k));ent=-sum((c/k)*math.log2(c/k)for c in counts.values());expected=(ent<1.2)|((len(counts)==1)<<1)|((v==0)<<2);assert flag==expected;cachechecks+=1
  for tie in ['left','right','robust']:
   out=D/f'v_{k}_{rec}_{tie}.csv';subprocess.run([str(R/'build/analyze'),'--cache',str(cache/f'r{rec}.bin'),'--label','fixture','--record',f'r{rec}','--out',str(out),'--seeds','42','--configs',str(R/'configs'),'--eval-w',str(E),'--ws','1,4,20,50','--tie',tie,'--distinct','1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
   contexts={}
   for row in csv.DictReader(out.open()):
    method,seed,w,tau=row['method'],int(row['hash_seed']),int(row['w']),int(row['tau']);key=(method,seed)
    salt,a,c=params(seed,k);mask=(1<<(2*k))-1
    rawparams=json.loads((R/'configs/fixed_parameters.json').read_text())
    s64,a64,b64=map(int,[rawparams['salt'],rawparams['multiplier_odd'],rawparams['offset']])
    if method=='kssd_repo':
     blob=(R/'configs'/f'kssd_k{k}_seed42.bin').read_bytes();assert blob[:8]==b'KSDFIX01'
     bk,L,C,rng,bs=struct.unpack_from('<IIIIQ',blob,8);assert (bk,C,rng,bs)==(k,8,0,42)
     off=32;tables={}
     for q in range(1,L+1):
      ss,nn=struct.unpack_from('<IQ',blob,off);off+=12;assert ss==q and nn==4**q
      tables[q]=struct.unpack_from('<'+'H'*nn,blob,off);off+=2*nn
     m=(k+7)//8;q,rr=divmod(k,m);lengths=[q+(i<rr)for i in range(m)]
     def score(x):
      consumed=0;h=0
      for ell in lengths:
       consumed+=ell;j=(x>>(2*(k-consumed)))&((1<<(2*ell))-1)
       h=(h<<(2*ell))|tables[ell][j]
      return h
    else:
     score={'xor':lambda x:x^salt,'mul':lambda x:x*a&mask,'affine':lambda x:(x*a+c)&mask,'salted_mul':lambda x:(x^salt)*a&mask,'mix64':lambda x:mix(x^salt),'minimap_hash':lambda x:mm(x,mask),'identity':lambda x:x,
      'mul64':lambda x:x*a64&MASK,'affine64':lambda x:(x*a64+b64)&MASK,'salted_mul64':lambda x:((x^s64)*a64)&MASK}[method]
    st=dict(n_eligible=sum(map(len,ids[rec])),n_windows=0,n_selected=0,n_unique_selected_record=0,n_selected_highfreq=0,n_selected_lowentropy=0,n_selected_homopolymer=0,sum_reference_frequency=0,max_selected_frequency=0,n_mixed_windows=0,n_avoidable_highfreq=0,n_feasible_sampling_windows=0,n_windows_select_highfreq=0,n_windows_with_allA=0,n_windows_select_allA=0,n_eval_windows=0,n_eval_feasible=0,n_eval_covered=0,max_uncovered_feasible_run=0,sum_retained_reference_frequency=0,n_hash_calls=sum(map(len,ids[rec])))
    selectedcodes=[]
    for bs in ids[rec]:
     sc=[score(x)for x in bs];sel=set();prev=None
     for start in range(max(0,len(bs)-w+1)):
      p=min(range(start,start+w),key=lambda p:(sc[p],p if tie=='left'else-p))
      if tie=='robust'and prev is not None and prev>=start and sc[prev]==sc[p]:p=prev
      prev=p;sel.add(p);fs=[freq[x]for x in bs[start:start+w]];mixed=min(fs)<=tau<max(fs);hi=freq[bs[p]]>tau
      st['n_windows']+=1;st['n_mixed_windows']+=mixed;st['n_avoidable_highfreq']+=mixed and hi;st['n_feasible_sampling_windows']+=min(fs)<=tau;st['n_windows_select_highfreq']+=hi
      aa=0 in bs[start:start+w];st['n_windows_with_allA']+=aa;st['n_windows_select_allA']+=aa and bs[p]==0
     for p in sel:
      x=bs[p];f=freq[x];st['n_selected']+=1;st['n_selected_highfreq']+=f>tau;st['sum_reference_frequency']+=f;st['max_selected_frequency']=max(st['max_selected_frequency'],f);st['sum_retained_reference_frequency']+=f if f<=tau else 0;cnt=Counter((x>>(2*j))&3 for j in range(k));e=-sum((z/k)*math.log2(z/k)for z in cnt.values());st['n_selected_lowentropy']+=e<1.2;st['n_selected_homopolymer']+=len(cnt)==1;selectedcodes.append(x)
     run=0
     for start in range(max(0,len(bs)-E+1)):
      feasible=any(freq[bs[j]]<=tau for j in range(start,start+E));covered=any(j in sel and freq[bs[j]]<=tau for j in range(start,start+E));st['n_eval_windows']+=1;st['n_eval_feasible']+=feasible;st['n_eval_covered']+=covered;run=run+1 if feasible and not covered else 0;st['max_uncovered_feasible_run']=max(run,st['max_uncovered_feasible_run'])
    st['n_unique_selected_record']=len(set(selectedcodes))
    for key,val in st.items():assert int(row[key])==val,(k,rec,tie,method,seed,w,tau,key,row[key],val);checks+=1
    rowcount+=1
print(json.dumps(dict(status='PASS',fixture_rows=rowcount,integer_metric_comparisons=checks,cache_element_comparisons=cachechecks,ks=[2,3,9,21,32],sampling_windows=[1,4,20,50],assessment_window=E,tie_rules=['left','right','robust'],methods=methods,independent_frequency_counting=True,frequency_scope='all fixture records',lowercase_ambiguity_record_boundary_tests=True)))
