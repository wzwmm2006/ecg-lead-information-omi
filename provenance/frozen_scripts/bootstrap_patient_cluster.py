"""Efficient paired patient-cluster bootstrap at locked thresholds.

Method: one row per ECG, implicit patient multinomial weights per replicate.
This reproduces the standard cluster bootstrap where each sampled patient's
observed ECGs enter once per draw. No file writes until all 3 contrasts finish.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

RUN=Path(r'10_gate2_a2a_integration/runs/RUN_20261110_A2a_ONLY')
allp=pd.read_csv(RUN/'A2A_ALL_EVAL_PREDICTIONS.csv',dtype={'ecg_id':str,'patient_id':str})
pooled=pd.read_csv(RUN/'A2A_POOLED_LOCKED_METRICS.csv').set_index('configuration')
patients=np.array(sorted(allp.patient_id.unique()))
pid2i={p:i for i,p in enumerate(patients)}
B=1000
rows=[]
for ci,cfg in enumerate(['C1','C2','C3']):
    rng=np.random.default_rng(20260912+ci)
    sub=allp[allp.configuration.isin(['C0',cfg])].copy()
    sub['pidx']=sub.patient_id.map(pid2i)
    correct=((sub.omi_label==0)&(sub.probability<sub.threshold)).to_numpy(dtype=np.float64)
    non=(sub.omi_label==0).to_numpy(dtype=np.float64)
    isC0=(sub.configuration=='C0').to_numpy()
    isCFG=(sub.configuration==cfg).to_numpy()
    diffs=np.empty(B)
    for b in range(B):
        w=np.bincount(rng.choice(len(patients),size=len(patients),replace=True),minlength=len(patients)).astype(np.float64)
        rw=w[sub.pidx.to_numpy()]
        num0=float((rw[isC0]*correct[isC0]).sum()); den0=float((rw[isC0]*non[isC0]).sum())
        numc=float((rw[isCFG]*correct[isCFG]).sum()); denc=float((rw[isCFG]*non[isCFG]).sum())
        diffs[b]=(numc/denc if denc else np.nan)-(num0/den0 if den0 else np.nan)
    diffs=diffs[np.isfinite(diffs)]
    rows.append({'contrast':f'{cfg}-C0','delta_specificity':float(pooled.loc[cfg,'specificity']-pooled.loc['C0','specificity']),
                 'ci_low':float(np.quantile(diffs,0.025)),'ci_high':float(np.quantile(diffs,0.975)),
                 'bootstrap_unit':'patient cluster (all observed ECGs per sampled patient once)',
                 'patients':len(patients),'replicates':int(diffs.size),'thresholds':'locked per fold'})
out=pd.DataFrame(rows)
out.to_csv(RUN/'A2A_PAIRED_PATIENT_BOOTSTRAP.csv',index=False)
summary={'method':'patient multinomial cluster bootstrap','patients':int(len(patients)),'replicates':B,'rows':rows}
(RUN/'A2A_BOOTSTRAP_METHOD.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(out.to_string(index=False))
