#!/usr/bin/env python3
"""Plot only the existing frozen Phase1 five-method score-loop summary."""
import csv, argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
METHODS=['KSSD-Array','XXH3','XXH64','MurmurHash3','wyhash']
DATASETS=['Synthetic_300_Mb','GRCh38.p14_chr1'];KS=[16,19,21,24,31]
COLORS=['#1F77B4','#FF7F0E','#2CA02C','#D62728','#9467BD'];STYLES=['-','--','-.','--',':'];MARKERS=['o','s','^','D','v']
a=argparse.ArgumentParser();a.add_argument('--data',type=Path,required=True);a.add_argument('--output-dir',type=Path,required=True);args=a.parse_args()
with args.data.open()as f:r=list(csv.DictReader(f,delimiter='\t'))
index={(x['dataset'],int(x['k']),x['method']):x for x in r}
assert len(r)==len(index)==50 and set(index)=={(d,k,m)for d in DATASETS for k in KS for m in METHODS}
assert all(int(x['n'])==5 for x in r)
assert abs(float(index['GRCh38.p14_chr1',21,'KSSD-Array']['throughput_Mscores_s_mean'])-521.6862161262)<1e-9
assert abs(float(index['GRCh38.p14_chr1',31,'KSSD-Array']['throughput_Mscores_s_mean'])-329.5954770048)<1e-9
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})
fig,axes=plt.subplots(1,2,figsize=(11.8,4.25),sharey=True)
maxy=max(float(x['throughput_Mscores_s_mean'])+float(x['throughput_Mscores_s_sample_sd'])for x in r)
for ax,d in zip(axes,DATASETS):
 for i,m in enumerate(METHODS):
  z=[index[d,k,m]for k in KS]
  ax.errorbar(range(5),[float(x['throughput_Mscores_s_mean'])for x in z],yerr=[float(x['throughput_Mscores_s_sample_sd'])for x in z],label=m,color=COLORS[i],linestyle=STYLES[i],marker=MARKERS[i],linewidth=2 if i==0 else 1.25,markersize=5 if i==0 else 4,capsize=2.3,elinewidth=.75)
 ax.set_title(d);ax.set_xticks(range(5));ax.set_xticklabels(KS);ax.set_xlabel('k-mer length (k)');ax.set_ylim(0,maxy*1.12);ax.grid(axis='y',alpha=.25)
axes[0].set_ylabel('Throughput (M scores/s)')
h,l=axes[0].get_legend_handles_labels();fig.legend(h,l,loc='upper center',bbox_to_anchor=(.5,.98),ncol=5,frameon=False)
fig.subplots_adjust(top=.79,bottom=.16,left=.085,right=.985,wspace=.12)
args.output_dir.mkdir(parents=True,exist_ok=True)
for ext in ['png','pdf','svg']:
 p=args.output_dir/('Figure2_five_method_independent_scoring.'+ext)
 fig.savefig(p,dpi=600,facecolor='white')
 print(p)
plt.close(fig)
