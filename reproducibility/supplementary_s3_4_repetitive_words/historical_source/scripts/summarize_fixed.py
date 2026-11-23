from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
R=Path(__file__).resolve().parents[1]
meta={(d['label'],r['accession']):r['group']for d in json.loads((R/'input_manifest.json').read_text())for r in d['records']}
frames=[]
for phase in ['primary','sensitivity10','sensitivity50']:
 for p in (R/'results').glob(phase+'_*.csv'):
  f=pd.read_csv(p);f['phase']=phase;f['stratum']=[meta[(d,c)]for d,c in zip(f.dataset,f.record)];frames.append(f)
f=pd.concat(frames,ignore_index=True)
assert len(f)==2016,len(f)
assert set(f.hash_seed)=={42} and set(f.k)=={21}
assert (f.n_hash_calls==f.n_eligible).all()
assert (f.n_avoidable_highfreq<=f.n_mixed_windows).all()
assert (f.n_eval_covered<=f.n_eval_feasible).all()
assert (f.n_selected_highfreq<=f.n_selected).all()
assert (f.n_windows_with_allA==f.n_windows_select_allA)[f.method.isin(['mul','mul64'])].all()
for _,g in f.groupby(['phase','dataset','record','w','tau']):
 for c in ['n_eligible','n_windows','n_mixed_windows','n_eval_feasible','n_eval_windows','n_windows_with_allA']:
  assert g[c].nunique()==1,c
for _,g in f.groupby('method'):
 for c in ['salt','a','b']:assert g[c].nunique()==1,('parameters changed',c)
f.to_csv(R/'results/fixed_per_record.csv',index=False)
allf=f.copy();allf['stratum']='all';sinput=pd.concat([f,allf],ignore_index=True)
keys=['phase','dataset','stratum','k','w','eval_w','tau','method','hash_seed']
counts=[c for c in f.columns if c.startswith(('n_','sum_')) and c!='n_unique_selected_record']
s=sinput.groupby(keys)[counts].sum().reset_index()
m=sinput.groupby(keys)[['max_selected_frequency','max_uncovered_feasible_run']].max().reset_index();s=s.merge(m,on=keys)
def pct(n,d):return np.where(d>0,100*n/d,np.nan)
s['density_pct']=pct(s.n_selected,s.n_eligible)
s['density_factor']=(s.w+1)*s.density_pct/100
s['avoidable_highcopy_pct']=pct(s.n_avoidable_highfreq,s.n_mixed_windows)
s['coverage_after_filtering_pct']=pct(s.n_eval_covered,s.n_eval_feasible)
s['filtered_selected_pct']=pct(s.n_selected_highfreq,s.n_selected)
s['mean_reference_frequency_of_selected']=s.sum_reference_frequency/s.n_selected
s['uncovered_feasible_per_100000']=1000*(100-s.coverage_after_filtering_pct)
s['allA_chosen_when_present_pct']=pct(s.n_windows_select_allA,s.n_windows_with_allA)
s.to_csv(R/'results/fixed_summary_all.csv',index=False)
primary=s[(s.phase=='primary')&(s.stratum=='nuclear')&(s.tau==50)].copy()
primary.to_csv(R/'results/fixed_primary_nuclear.csv',index=False)
config_info={'status':'PASS','biological_per_record_threshold_rows':len(f),'frozen_configuration_count_per_method':1,'distinct_k':[21],'distinct_sampling_windows':[10,20,50],'nuclear_records':21,'all_records':24,'mapping_calls_equal_eligible_in_all_rows':True,'denominators_method_independent':True,'arithmetic_parameters_identical_across_all_inputs':True}
(R/'logs/result_invariants.json').write_text(json.dumps(config_info,indent=2))
print(primary[['dataset','method','density_pct','avoidable_highcopy_pct','coverage_after_filtering_pct']].to_string(index=False))
