"""TOPIC890 P3 matched-sensitivity READ-ONLY analysis.

Implements the frozen plan. Reads only existing outer per-ECG predictions.
No training, no re-inference, no checkpoint or original-result modification.
"""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd

ROOT=Path('.').resolve();OUT=ROOT/'12_p3_matched_sensitivity'
A1=ROOT/'10_gate2_r2/runs/RUN_20261110_A1A2a'
A2=ROOT/'10_gate2_a2a_integration/runs/RUN_20261110_A2a_ONLY'
CFGS=['C0','C1','C2','C3'];TARGET=.95;B=2000;SEED=20261110

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def roc_vertices(y,p):
 d=pd.DataFrame({'y':np.asarray(y,dtype=int),'p':np.asarray(p,dtype=float)})
 npos=int(d.y.sum());nneg=len(d)-npos
 if npos==0 or nneg==0:return None
 g=d.groupby('p',sort=False).y.agg(['sum','size']).sort_index(ascending=False)
 tp=np.cumsum(g['sum'].to_numpy());fp=np.cumsum(g['size'].to_numpy()-g['sum'].to_numpy())
 return np.vstack([np.zeros(2),np.column_stack([fp/nneg,tp/npos])])

def interp_tpr95(y,p):
 r=roc_vertices(y,p);fpr,tpr=r[:,0],r[:,1]
 cand=np.flatnonzero(tpr>=TARGET)
 if not len(cand):return None
 j=int(cand[0]);i=j-1
 if i<0:return {'fpr_i':0.,'tpr_i':0.,'fpr_j':0.,'tpr_j':0.,'weight':0.,'fpr95':0.,'specificity':1.,'n':int(len(y))}
 if tpr[i]>=TARGET or tpr[i]==tpr[j]:return None
 w=(TARGET-tpr[i])/(tpr[j]-tpr[i]);f95=fpr[i]+w*(fpr[j]-fpr[i])
 return {'fpr_i':float(fpr[i]),'tpr_i':float(tpr[i]),'fpr_j':float(fpr[j]),'tpr_j':float(tpr[j]),'weight':float(w),'fpr95':float(f95),'specificity':float(1-f95),'n':int(len(y))}

def deterministic(y,p):
 y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float);o=np.argsort(-p);yy=y[o];pp=p[o]
 cum=np.cumsum(yy)/max(yy.sum(),1);idx=np.flatnonzero(cum>=TARGET)
 if not len(idx):return None
 t=float(pp[int(idx[0])]);pred=p>=t;np_=int(y.sum());nn=len(y)-np_
 return {'threshold':t,'sensitivity':float(((y==1)&pred).sum()/np_),'specificity':float(((y==0)&~pred).sum()/nn)}

def load_all():
 data={};hashes={}
 for a in ['A1_seedA','A1_seedB','A2a']:
  for f in range(5):
   frm={}
   for c in CFGS:
    p=(A1/f'fold{f}'/a/f'{c}_eval_predictions.csv') if a.startswith('A1') else (A2/f'fold{f}'/'A2a'/f'{c}_eval_predictions.csv')
    if not p.exists():raise FileNotFoundError(p)
    d=pd.read_csv(p,dtype={'ecg_id':str,'patient_id':str});d['ecg_id']=d.ecg_id.str.zfill(5)
    if d.ecg_id.duplicated().any():raise ValueError(f'duplicate ECG {p}')
    if not np.isfinite(d.probability).all():raise ValueError(f'nonfinite {p}')
    d=d.sort_values('ecg_id').reset_index(drop=True);frm[c]=d;hashes[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
   b=frm['C0'][['ecg_id','patient_id','omi_label']]
   for c in CFGS:
    x=frm[c]
    if x.ecg_id.tolist()!=b.ecg_id.tolist():raise ValueError(f'ECG mismatch {a} {f} {c}')
    if not (x.patient_id.to_numpy()==b.patient_id.to_numpy()).all():raise ValueError(f'patient mismatch {a} {f} {c}')
    if not (x.omi_label.to_numpy()==b.omi_label.to_numpy()).all():raise ValueError(f'label mismatch {a} {f} {c}')
   data[(a,f)]=frm
 return data,hashes

def rows_to_fold(rows):
 out=[]
 for (a,f),fr in rows['data'].items():
  for c in CFGS:
   d=fr[c];r=interp_tpr95(d.omi_label,d.probability)
   if r is None:raise RuntimeError(f'no TPR95 interpolation {a} {f} {c}')
   dt=deterministic(d.omi_label,d.probability)
   rec={'analysis':a,'outer_fold':f,'configuration':c,'n_ecg':len(d),'n_omi':int((d.omi_label==1).sum()),'n_non_omi':int((d.omi_label==0).sum()),
        'specificity_at_TPR95':r['specificity'],'fpr_at_TPR95':r['fpr95'],'roc_endpoint_i':f"{r['fpr_i']:.12g},{r['tpr_i']:.12g}",'roc_endpoint_j':f"{r['fpr_j']:.12g},{r['tpr_j']:.12g}",'interp_weight':r['weight'],
        'det_threshold':dt['threshold'],'det_sensitivity':dt['sensitivity'],'det_specificity':dt['specificity']}
   out.append(rec)
 return pd.DataFrame(out)

def main():
 data,hashes=load_all();fold=rows_to_fold({'data':data})
 # cross-fold weighted aggregates
 agg=[]
 for a in fold.analysis.unique():
  f=fold[fold.analysis==a]
  for c in CFGS:
   x=f[f.configuration==c];w=x.n_non_omi
   agg.append({'analysis':a,'configuration':c,'weighted_specificity_at_TPR95':float((x.specificity_at_TPR95*w).sum()/w.sum()),
               'weighted_det_specificity':float((x.det_specificity*w).sum()/w.sum()),'total_non_omi':int(w.sum())})
 agg=pd.DataFrame(agg)
 comp=[]
 for a in fold.analysis.unique():
  w=agg[(agg.analysis==a)&(agg.configuration=='C0')].iloc[0]
  for c in ['C1','C2','C3']:
   x=agg[(agg.analysis==a)&(agg.configuration==c)].iloc[0]
   f=fold[fold.analysis==a];piv=f.pivot(index='outer_fold',columns='configuration',values='specificity_at_TPR95')
   delta=piv[c]-piv['C0']
   comp.append({'analysis':a,'contrast':f'{c}-C0','weighted_delta_spec_at_TPR95':float(x.weighted_specificity_at_TPR95-w.weighted_specificity_at_TPR95),
                'excess_FP_per_1000':float(-1000*(x.weighted_specificity_at_TPR95-w.weighted_specificity_at_TPR95)),
                'negative_folds':int((delta<0).sum()),'positive_folds':int((delta>0).sum()),'zero_folds':int((delta==0).sum()),
                'fold_deltas':','.join(f'{v:.8f}' for v in delta),
                'weighted_delta_det_spec':float(agg[(agg.analysis==a)&(agg.configuration==c)].iloc[0].weighted_det_specificity-agg[(agg.analysis==a)&(agg.configuration=='C0')].iloc[0].weighted_det_specificity)})
 comp=pd.DataFrame(comp)
 fold.to_csv(OUT/'P3_MATCHED_SENSITIVITY_RESULTS.csv',index=False)
 agg.to_csv(OUT/'P3_FOLD_WEIGHTED_CONFIGURATION_RESULTS.csv',index=False)
 comp.to_csv(OUT/'P3_FOLD_WEIGHTED_CONTRASTS.csv',index=False)
 # locked-vs-TPR95 comparison
 lock_rows=[]
 for a in ['A1_seedA','A1_seedB','A2a']:
  src=(A1/'A1_POOLED_LOCKED_THRESHOLD.csv') if a.startswith('A1') else (A2/'A2A_POOLED_LOCKED_METRICS.csv')
  d=pd.read_csv(src)
  if a.startswith('A1'):d=d[d.analysis==a];smap={'C0':'spec','C1':'spec','C2':'spec','C3':'spec'};cmap={'C0':'C0','C1':'C1','C2':'C2','C3':'C3'}
  else:smap={c:'specificity' for c in CFGS}
  base=float(d[d[('cfg' if a.startswith('A1') else 'configuration')]=='C0'][smap['C0']].iloc[0])
  for c in ['C1','C2','C3']:
   v=float(d[d[('cfg' if a.startswith('A1') else 'configuration')]==c][smap[c]].iloc[0])
   q=comp[(comp.analysis==a)&(comp.contrast==f'{c}-C0')].iloc[0]
   lock_rows.append({'analysis':a,'contrast':f'{c}-C0','locked_delta_spec':v-base,'TPR95_weighted_delta_spec':q.weighted_delta_spec_at_TPR95,'difference_TPR95_minus_locked':q.weighted_delta_spec_at_TPR95-(v-base)})
 pd.DataFrame(lock_rows).to_csv(OUT/'P3_LOCKED_VS_TPR95.csv',index=False)
 (OUT/'P3_INPUT_HASHES.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
 # bootstrap
 boot=[];invalid=0
 rng=np.random.default_rng(SEED)
 for a in ['A1_seedA','A1_seedB','A2a']:
  for b in range(B):
   vals=[];ok=True;reasons=[]
   for f in range(5):
    fr=data[(a,f)];base=fr['C0'];pats=np.array(sorted(base.patient_id.unique()));idx={p:i for i,p in enumerate(pats)}
    chosen=rng.integers(0,len(pats),len(pats));counts=np.bincount(chosen,minlength=len(pats)).astype(float)
    # patient weight; each observed ECG of a sampled patient once
    pw=counts[base.patient_id.map(idx).to_numpy()]
    sp={}
    for c in CFGS:
     d=fr[c];y=d.omi_label.to_numpy();
     # weighted ROC by expanding records according to patient multiplicity
     reps=np.rint(pw).astype(int)
     y2=np.repeat(y,reps);p2=np.repeat(d.probability.to_numpy(),reps)
     r=interp_tpr95(y2,p2)
     if r is None:ok=False;reasons.append(f'fold {f} {c} no ROC crossing');break
     sp[c]=r['specificity']
    if not ok:break
    vals.append((len(base)-int((base.omi_label==1).sum()),sp))
   if not ok:
    invalid+=1;boot.append({'analysis':a,'replicate':b,'valid':False,'reason':';'.join(reasons)});continue
   # weighted by non-OMI ECG count of original folds
   tot=sum(v[0] for v in vals)
   for c in ['C1','C2','C3']:
    delta=sum(v[0]*(v[1][c]-v[1]['C0']) for v in vals)/tot
    boot.append({'analysis':a,'replicate':b,'valid':True,'contrast':f'{c}-C0','delta_specificity':delta,'reason':''})
  # For report: aggregate only complete replicates
 bd=pd.DataFrame(boot);bd.to_csv(OUT/'P3_MATCHED_SENSITIVITY_BOOTSTRAP_RAW.csv',index=False)
 ci=[]
 for a in ['A1_seedA','A1_seedB','A2a']:
  for c in ['C1','C2','C3']:
   x=bd[(bd.analysis==a)&(bd.valid==True)&(bd.contrast==f'{c}-C0')].delta_specificity.to_numpy()
   ci.append({'analysis':a,'contrast':f'{c}-C0','point_estimate':float(comp[(comp.analysis==a)&(comp.contrast==f'{c}-C0')].weighted_delta_spec_at_TPR95.iloc[0]),'ci_low':float(np.quantile(x,.025)) if len(x) else None,'ci_high':float(np.quantile(x,.975)) if len(x) else None,'valid_replicates':int(len(x)),'invalid_replicates':int(B-len(x)),'bootstrap_seed':SEED,'bootstrap_unit':'patient within fold; same patient sample across configurations'})
 pd.DataFrame(ci).to_csv(OUT/'P3_MATCHED_SENSITIVITY_BOOTSTRAP.csv',index=False)
 print('fold rows',len(fold),'contrasts',len(comp),'bootstrap valid rows',len(bd[bd.valid]),'invalid',int((~bd.valid).sum()))
 print(comp.to_string(index=False));print(pd.DataFrame(ci).to_string(index=False))
if __name__=='__main__':main()
