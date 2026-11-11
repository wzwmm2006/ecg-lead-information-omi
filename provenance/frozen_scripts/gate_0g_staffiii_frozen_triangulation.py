from __future__ import annotations
import csv, hashlib, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import resample_poly
import scipy
import torch
import wfdb
from gate_0e_spatial_pilot import TinyECGCNN, CONFIGS, LEADS, ROOT, N_POINTS, BATCH

DATA=ROOT/'02_data'/'external'/'STAFF_III'; RES=ROOT/'03_results'; FIG=ROOT/'04_figures'/'gate_0g'; INTERIM=ROOT/'02_data'/'interim'
SEED=20260813; EPS=1e-6
PRIMARY=['C0','C1','C2','C3']; MODEL_PATH={c:INTERIM/f'gate_0f_model_{c}.pt' for c in PRIMARY}

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rid(v):
 if pd.isna(v): return None
 z=str(v).strip()
 import re
 m=re.fullmatch(r'(\d+)([a-z])',z)
 return (m.group(1).zfill(3)+m.group(2)) if m else z
def parsed(v):
 if pd.isna(v): return None
 try:
  p=[float(x) for x in str(v).split(';')]
  return {'start':p[0],'duration':p[1],'tail':p[2]} if len(p)==3 else None
 except ValueError:return None
def territory(s):
 s=str(s).lower()
 if 'lad' in s:return 'LAD'
 if 'rca' in s:return 'RCA'
 if 'circ' in s or 'lcx' in s:return 'LCx'
 if 'lm' in s or 'left main' in s:return 'LM'
 return 'OTHER'
def contrast_contaminated(v):
 if pd.isna(v):return False
 try:return any(55 <= float(x) <= 75 for x in str(v).split(';'))
 except ValueError:return True
def read_window(record, start_s):
 rec=wfdb.rdrecord(str(DATA/'data'/record), sampfrom=int(round(start_s*1000)), sampto=int(round((start_s+10)*1000)))
 if rec.fs != 1000 or rec.p_signal.shape[0] != 10000:raise ValueError('unexpected STAFF III fs/window')
 names=[str(x) for x in rec.sig_name]; canon={x.lower().replace(' ',''):i for i,x in enumerate(names)}
 required=['i','ii','iii','v1','v2','v3','v4','v5','v6']
 if not all(x in canon for x in required):raise ValueError('missing STAFF III measured lead')
 raw=np.asarray(rec.p_signal,dtype=np.float32)
 I=raw[:,canon['i']]; II=raw[:,canon['ii']]
 derived={'III':raw[:,canon['iii']],'aVR':-(I+II)/2,'aVL':I-II/2,'aVF':II-I/2}
 x=np.vstack([I,II,derived['III'],derived['aVR'],derived['aVL'],derived['aVF'],raw[:,canon['v1']],raw[:,canon['v2']],raw[:,canon['v3']],raw[:,canon['v4']],raw[:,canon['v5']],raw[:,canon['v6']]])
 # Frozen deterministic 1000 -> 500 anti-aliasing polyphase resampling, then Gate 0F 500 -> 50 Hz mean downsample.
 x=resample_poly(x, up=1, down=2, axis=1).reshape(12,N_POINTS,10).mean(axis=2)
 med=np.nanmedian(x,axis=1,keepdims=True); sd=np.nanstd(x,axis=1,keepdims=True)
 return np.nan_to_num((x-med)/np.maximum(sd,1e-3),nan=0.,posinf=0.,neginf=0.), names
def predict(models,x):
 out={}; device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
 for c,m in models.items():
  m.eval().to(device)
  with torch.no_grad(): out[c]=float(torch.sigmoid(m(torch.from_numpy(x[None,:, :][:,CONFIGS[c]]).float().to(device))).cpu().item())
 return out
def logit(p):
 p=np.clip(p,EPS,1-EPS);return float(np.log(p/(1-p)))
def boot(vals, n=1000):
 rng=np.random.default_rng(SEED); vals=np.asarray(vals,float); med=[]; con=[]
 for _ in range(n):
  x=vals[rng.integers(0,len(vals),len(vals))];med.append(np.median(x));con.append(np.mean(x>0))
 return (np.quantile(med,[.025,.975]),np.quantile(con,[.025,.975]))
def paired_boot(a,b,n=1000):
 rng=np.random.default_rng(SEED+91); d=[]
 for _ in range(n):
  ix=rng.integers(0,len(a),len(a));d.append(np.mean(b[ix])-np.mean(a[ix]))
 return np.quantile(d,[.025,.975])
def main():
 RES.mkdir(exist_ok=True,parents=True); FIG.mkdir(exist_ok=True,parents=True)
 # Full official SHA256 audit.
 expected={}
 for line in (DATA/'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
  p=line.split(maxsplit=1)
  if len(p)==2:expected[p[1]]=p[0]
 rows=[]; passed=failed=missing=0
 for rel,h in expected.items():
  path=DATA/rel; state='PASS' if path.exists() and sha(path)==h else ('MISSING' if not path.exists() else 'FAIL')
  passed+=state=='PASS'; failed+=state=='FAIL'; missing+=state=='MISSING'; rows.append({'relative_path':rel,'extension':path.suffix,'expected_sha256':h,'status':state,'size_bytes':path.stat().st_size if path.exists() else None,'possible_role':'waveform' if path.suffix=='.dat' else ('header' if path.suffix=='.hea' else 'annotation')})
 pd.DataFrame(rows).to_csv(RES/'gate_0g_staffiii_asset_inventory.csv',index=False)
 critical=[r for r in rows if r['relative_path']=='RECORDS' or r['relative_path'].startswith('data/') or r['relative_path']=='STAFF-III-Database-Annotations.xlsx']
 critical_fail=sum(r['status']!='PASS' for r in critical)
 if critical_fail:raise RuntimeError(f'critical integrity failed {critical_fail=}')
 records=[x.strip() for x in (DATA/'RECORDS').read_text().splitlines() if x.strip()]; expected_records={Path(x).name for x in records}
 actual_records={str(x.relative_to(DATA/'data').with_suffix('')) for x in (DATA/'data').rglob('*.hea')};
 if expected_records != actual_records:raise RuntimeError('RECORDS/header mismatch')
 # Spreadsheet mapping; first patient row begins after ten explanatory/header rows.
 raw=pd.read_excel(DATA/'STAFF-III-Database-Annotations.xlsx',header=None); data=raw.iloc[10:].copy(); ann=[]; select=[]
 for _,r in data.iterrows():
  patient_raw=r.iloc[0]
  if pd.isna(patient_raw): continue
  try: patient=str(int(float(patient_raw)))
  except (TypeError, ValueError): continue
  baseline=rid(r.iloc[3]);
  for j,(rec_col,art_col,time_col,inj_col) in enumerate([(6,7,8,9),(10,11,12,13),(14,15,16,17),(18,19,20,None),(21,22,23,None)],1):
   recid=rid(r.iloc[rec_col]); timing=parsed(r.iloc[time_col])
   quality='EXCLUDE_PRIMARY'; reason=''
   if recid and timing and timing['duration']>=90 and baseline:
    quality='CLEAR';reason='first-line spreadsheet timing'
    if contrast_contaminated(r.iloc[inj_col]) if inj_col is not None else False:quality='EXCLUDE_PRIMARY';reason='contrast within 55-75s after inflation'
   if recid and (DATA/'data'/f'{recid}.hea').exists()==False:quality='EXCLUDE_PRIMARY';reason='missing record'
   ann.append({'patient_id':patient,'record_id':recid,'measurement_type':f'BI{j}','artery_raw':rid(r.iloc[art_col]),'artery':territory(r.iloc[art_col]),'inflation_number':j,'inflation_start':timing['start'] if timing else None,'inflation_end':(timing['start']+timing['duration']) if timing else None,'inflation_duration':timing['duration'] if timing else None,'contrast_injection':rid(r.iloc[inj_col]) if inj_col is not None else None,'baseline_record':baseline,'annotation_source':'official XLSX','annotation_quality':quality,'reason':reason})
  candidates=[x for x in ann if x['patient_id']==patient and x['annotation_quality']=='CLEAR']
  if candidates:
   e=sorted(candidates,key=lambda x:x['inflation_number'])[0]; e=e.copy();e.update({'selected':True,'baseline_window_start':60,'occlusion_window_start':e['inflation_start']+60,'selection_rule':'first CLEAR BI1-BI5; duration >=90s; baseline BR; no primary contrast 55-75s'}) ;select.append(e)
 pd.DataFrame(ann).to_csv(RES/'gate_0g_staffiii_annotation_audit.csv',index=False); pd.DataFrame(select).to_csv(RES/'gate_0g_primary_event_selection.csv',index=False)
 # Frozen Gate 0F checkpoints only.
 models={}
 for c,p in MODEL_PATH.items():
  state=torch.load(p,map_location='cpu',weights_only=False);m=TinyECGCNN(len(CONFIGS[c]));m.load_state_dict(state['state_dict']);models[c]=m
 scores=[]; excluded=[]
 for e in select:
  try:
   xb,n1=read_window(e['baseline_record'],60); xo,n2=read_window(e['record_id'],e['inflation_start']+60)
   if n1!=n2:raise ValueError('lead-order mismatch')
   pb=predict(models,xb);po=predict(models,xo)
   for c in PRIMARY:scores.append({'patient_id':e['patient_id'],'record_id':e['record_id'],'artery':e['artery'],'configuration':c,'p_baseline':pb[c],'p_occlusion':po[c],'baseline_window_start':60,'occlusion_window_start':e['inflation_start']+60,'lead_names_raw':';'.join(n1),'lead_mapping':'measured I,II,III,V1-V6; derived aVR=-(I+II)/2,aVL=I-II/2,aVF=II-I/2'})
  except Exception as ex:excluded.append({'patient_id':e['patient_id'],'record_id':e['record_id'],'reason':str(ex)})
 pd.DataFrame(scores).to_csv(RES/'gate_0g_frozen_scores.csv',index=False)
 s=pd.DataFrame(scores); s['delta_probability']=s.p_occlusion-s.p_baseline;s['delta_logit']=s.apply(lambda r:logit(r.p_occlusion)-logit(r.p_baseline),axis=1);s.to_csv(RES/'gate_0g_within_patient_deltas.csv',index=False)
 out=[]; base=None
 for c in PRIMARY:
  d=s[s.configuration==c]; vals=d.delta_logit.to_numpy();ci,cci=boot(vals); concord=float(np.mean(vals>0));
  if c=='C0':base=(vals>0).astype(float)
  dci=[None,None] if c=='C0' else paired_boot(base,(vals>0).astype(float))
  out.append({'configuration':c,'n_patients':d.patient_id.nunique(),'median_delta_logit':float(np.median(vals)),'mean_delta_logit':float(np.mean(vals)),'delta_logit_ci_low':ci[0],'delta_logit_ci_high':ci[1],'positive_shift_concordance':concord,'concordance_ci_low':cci[0],'concordance_ci_high':cci[1],'delta_concordance_vs_C0':None if c=='C0' else concord-float(np.mean(base)),'delta_concordance_ci_low':dci[0],'delta_concordance_ci_high':dci[1]})
 pd.DataFrame(out).to_csv(RES/'gate_0g_configuration_concordance.csv',index=False)
 terr=[]
 for art in ['LAD','RCA','LCx','LM']:
  for c in PRIMARY:
   d=s[(s.artery==art)&(s.configuration==c)]
   if len(d):terr.append({'territory':art,'configuration':c,'n_patients':d.patient_id.nunique(),'median_delta_logit':float(d.delta_logit.median()),'positive_shift_concordance':float((d.delta_logit>0).mean())})
 pd.DataFrame(terr).to_csv(RES/'gate_0g_territory_analysis.csv',index=False)
 print(json.dumps({'hash_pass':int(passed),'records':len(records),'selected':len(select),'scored_patients':s.patient_id.nunique(),'excluded':excluded,'summary':out},indent=2))
if __name__=='__main__':main()
