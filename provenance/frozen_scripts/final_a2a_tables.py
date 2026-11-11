"""Final A2a Gate 2 analysis tables and consistency checks."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('.').resolve(); GATE=ROOT/'10_gate2_a2a_integration'; RUN=GATE/'runs/RUN_20261110_A2a_ONLY'
pooled=pd.read_csv(RUN/'A2A_POOLED_LOCKED_METRICS.csv').set_index('configuration')
a1=pd.read_csv(ROOT/'10_gate2_r2/runs/RUN_20261110_A1A2a/A1_POOLED_LOCKED_THRESHOLD.csv')
a1a=a1[a1.analysis=='A1_seedA'].set_index('cfg')
original=pd.read_csv(ROOT/'03_results/FINAL_TABLE_2_OOF_PERFORMANCE.csv').set_index('configuration')
comp=[]
for cfg in ['C1','C2','C3']:
    comp.append({'configuration':cfg,
      'A2a_delta_vs_C0':float(pooled.loc[cfg,'specificity']-pooled.loc['C0','specificity']),
      'A2a_sensitivity':float(pooled.loc[cfg,'sensitivity']),
      'A1_seedA_delta_vs_C0':float(a1a.loc[cfg,'spec']-a1a.loc['C0','spec']),
      'A1_seedA_sensitivity':float(a1a.loc[cfg,'sens']),
      'original_OOF_delta_spec95':float(original.loc[cfg,'delta_spec95_vs_c0']),
      'same_direction_A2a_vs_original':bool((pooled.loc[cfg,'specificity']-pooled.loc['C0','specificity'])<0),
      'same_direction_A2a_vs_A1':bool((pooled.loc[cfg,'specificity']-pooled.loc['C0','specificity'])<(a1a.loc[cfg,'spec']-a1a.loc['C0','spec'])+1e-15)})
# Correct same_direction_A2a_vs_A1: compare signs, not magnitude
for x in comp:
    x['same_direction_A2a_vs_A1']=bool(x['A2a_delta_vs_C0']*x['A1_seedA_delta_vs_C0']>0)
pd.DataFrame(comp).to_csv(RUN/'A2A_CROSS_ANALYSIS_CONSISTENCY.csv',index=False)
print(pd.DataFrame(comp).to_string(index=False))
# Fold-level sign counts
per=pd.read_csv(RUN/'A2A_PERFOLD_LOCKED_METRICS.csv')
sign=[]
for cfg in ['C1','C2','C3']:
    x=per.pivot(index='outer_fold',columns='configuration',values='specificity')
    d=x[cfg]-x['C0']
    sign.append({'contrast':f'{cfg}-C0','negative_folds':int((d<0).sum()),'positive_folds':int((d>0).sum()),'zero_folds':int((d==0).sum())})
pd.DataFrame(sign).to_csv(RUN/'A2A_FOLD_SIGN_COUNTS.csv',index=False)
print(pd.DataFrame(sign).to_string(index=False))
# Full result JSON
res={'tasks_completed':20,'configurations':['C0','C1','C2','C3'],'seed':'A policy only',
     'pooled':pooled.reset_index().to_dict('records'),
     'bootstrap':pd.read_csv(RUN/'A2A_PAIRED_PATIENT_BOOTSTRAP.csv').to_dict('records'),
     'fold_signs':sign,'analysis_scope':'A2a only; A1 not retrained; no hidden TEST or STAFF III.'}
(RUN/'A2A_GATE2_RESULT_SUMMARY.json').write_text(json.dumps(res,indent=2),encoding='utf-8')
print('summary written')
