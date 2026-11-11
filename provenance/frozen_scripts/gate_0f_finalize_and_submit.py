from __future__ import annotations
import hashlib, json, platform, random, subprocess, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
import wfdb
from gate_0e_spatial_pilot import TinyECGCNN, CONFIGS, LEADS, META, WAVE, ROOT, FS, N_POINTS, SEED, BATCH, EPOCHS, seed_all, record_id

RES=ROOT/'03_results'; INTERIM=ROOT/'02_data'/'interim'; MAN=ROOT/'02_data'/'manifests'; ADMIN=ROOT/'00_admin'
UNREADABLE={'03228','14262'}
SUBS=[('C0','gate_0f_submission_C0_12lead.csv'),('C1','gate_0f_submission_C1_limb6.csv'),('C2','gate_0f_submission_C2_precordial6.csv'),('C3','gate_0f_submission_C3_I_II_III.csv')]

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load(df, cache):
    if cache.exists(): return np.asarray(np.load(cache,mmap_mode='r'),dtype=np.float32)
    out=np.empty((len(df),12,N_POINTS),dtype=np.float32)
    for i,rid in enumerate(df.ecg_id):
        x=np.asarray(wfdb.rdrecord(str(WAVE/rid)).p_signal,dtype=np.float32).T
        x=x.reshape(12,N_POINTS,FS*10//N_POINTS).mean(axis=2)
        med=np.nanmedian(x,axis=1,keepdims=True); sd=np.nanstd(x,axis=1,keepdims=True)
        out[i]=np.nan_to_num((x-med)/np.maximum(sd,1e-3),nan=0.,posinf=0.,neginf=0.)
    np.save(cache,out); return out

def train_model(x,y,w,chs,seed,path):
    seed_all(seed); device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); m=TinyECGCNN(len(chs)).to(device)
    opt=torch.optim.AdamW(m.parameters(),lr=1e-3,weight_decay=1e-4)
    ds=torch.utils.data.TensorDataset(torch.from_numpy(x[:,chs]).float(),torch.from_numpy(y).float(),torch.from_numpy(w).float())
    dl=torch.utils.data.DataLoader(ds,batch_size=BATCH,shuffle=True,generator=torch.Generator().manual_seed(seed),num_workers=0)
    m.train()
    for _ in range(EPOCHS):
        for xb,yb,wb in dl:
            xb,yb,wb=xb.to(device),yb.to(device),wb.to(device); loss=(torch.nn.functional.binary_cross_entropy_with_logits(m(xb),yb,reduction='none')*wb).sum()/wb.sum(); opt.zero_grad(); loss.backward(); opt.step()
    torch.save({'state_dict':m.state_dict(),'configuration':chs,'seed':seed},path); return m

def predict(m,x,chs):
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); m.eval().to(device); out=[]
    with torch.no_grad():
        for st in range(0,len(x),BATCH): out.append(torch.sigmoid(m(torch.from_numpy(x[st:st+BATCH][:,chs]).float().to(device))).cpu().numpy())
    return np.concatenate(out)

def tau95(y,p):
    order=np.argsort(-p); yy=y[order]; pp=p[order]; k=np.flatnonzero(np.cumsum(yy)/max(yy.sum(),1)>=.95)[0]; return float(pp[k])

def qcm(y,p,t):
    z=(p>=t).astype(int); tn,fp,fn,tp=confusion_matrix(y,z,labels=[0,1]).ravel(); return {'n':len(y),'omi':int(y.sum()),'sensitivity':tp/(tp+fn) if tp+fn else None,'specificity':tn/(tn+fp) if tn+fp else None,'ppv':tp/(tp+fp) if tp+fp else None,'npv':tn/(tn+fn) if tn+fn else None}

def main():
    seed_all(SEED); RES.mkdir(exist_ok=True,parents=True); INTERIM.mkdir(exist_ok=True,parents=True); MAN.mkdir(exist_ok=True,parents=True)
    train=pd.read_csv(META/'train.csv'); test=pd.read_csv(META/'test.csv'); train['ecg_id']=train.ecg_row_record.map(record_id); test['ecg_id']=test.ecg_row_record.map(record_id); train=train[~train.ecg_id.isin(UNREADABLE)].reset_index(drop=True)
    train['patient_id']=train.Patient_id.astype(str); train['omi']=train.OMI.astype(int); test['patient_id']=test.Patient_id.astype(str)
    pats=train[['patient_id','omi']].groupby('patient_id',as_index=False).agg(omi=('omi','max')); fit_p,cal_p=train_test_split(pats,test_size=.2,random_state=SEED,stratify=pats.omi)
    fitset=set(fit_p.patient_id); train['finalization_split']=np.where(train.patient_id.isin(fitset),'MODEL_FIT','THRESHOLD_CALIBRATION'); train[['patient_id','finalization_split']].drop_duplicates().sort_values('patient_id').to_csv(INTERIM/'gate_0f_finalization_split.csv',index=False)
    x=load(train,INTERIM/'gate_0e_train_downsampled.npy'); xt=load(test,INTERIM/'gate_0f_test_downsampled.npy')
    counts=train[train.finalization_split=='MODEL_FIT'].patient_id.value_counts(); fit=train.finalization_split.to_numpy()=='MODEL_FIT'; cal=~fit; y=train.omi.to_numpy(); w=np.where(y==1,1/train.loc[fit,'omi'].mean(),1/(1-train.loc[fit,'omi'].mean())) if False else None
    fit_y=y[fit]; fit_pw=train.loc[fit,'patient_id'].map(1/counts).to_numpy(); cw=np.where(fit_y==1,1/fit_y.mean(),1/(1-fit_y.mean())); weights=fit_pw*cw
    thresholds={}; rows=[]; ck=[]
    for ci,(cfg,_) in enumerate(SUBS):
        chs=CONFIGS[cfg]; m=train_model(x[fit],fit_y,weights,chs,SEED+ci,INTERIM/f'gate_0f_model_{cfg}.pt'); pcal=predict(m,x[cal],chs); t=tau95(y[cal],pcal); thresholds[cfg]=t; rows.append({'configuration':cfg,'n':int(cal.sum()),'omi':int(y[cal].sum()),'tau95':t,**qcm(y[cal],pcal,t)}); ck.append({'configuration':cfg,'checkpoint':str(INTERIM/f'gate_0f_model_{cfg}.pt'),'sha256':sha256(INTERIM/f'gate_0f_model_{cfg}.pt'),'seed':SEED+ci,'model_fit_patients':int(fit_p.shape[0]),'model_fit_omi':int(fit_y.sum())})
    pd.DataFrame(rows).to_csv(RES/'gate_0f_finalization_performance.csv',index=False); pd.DataFrame(ck).to_csv(MAN/'gate_0f_model_manifest.csv',index=False)
    freeze={'analysis_time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'platform':platform.platform(),'python':sys.version,'torch':torch.__version__,'seed':SEED,'finalization':'patient-level 80% MODEL_FIT / 20% THRESHOLD_CALIBRATION, stratified OMI, random_state 20260813','architecture':'Gate 0E TinyECGCNN unchanged','optimizer':'AdamW lr=0.001 weight_decay=0.0001','epochs':EPOCHS,'batch_size':BATCH,'normalization':'per-record per-lead z-score after fixed 10x downsample to 500 points','lead_order':LEADS,'configurations':{k:v for k,v in CONFIGS.items() if k in ['C0','C1','C2','C3']},'thresholds':thresholds,'submission_order':[x[0] for x in SUBS],'test_rule':'single deterministic inference over official TEST; binary prediction >= frozen tau95','adaptive_changes_after_submission':'prohibited','hidden_evaluator':'http://39.105.59.221:8080/; no submission yet at manifest creation'}
    (ADMIN/'GATE_0F_FREEZE_MANIFEST.md').write_text('# Topic890 Gate 0F Freeze Manifest\n\n```json\n'+json.dumps(freeze,indent=2)+'\n```\n\nThis manifest was written before TEST inference and before any evaluator response. No adaptive changes are permitted.\n',encoding='utf-8')
    # Hash manifest after writing, then append hash to a separate audit line (manifest content itself remains frozen).
    mh=sha256(ADMIN/'GATE_0F_FREEZE_MANIFEST.md'); (ADMIN/'GATE_0F_FREEZE_MANIFEST.sha256').write_text(mh+'  GATE_0F_FREEZE_MANIFEST.md\n',encoding='ascii')
    probs=[]; subrows=[]
    for cfg,fn in SUBS:
        m=torch.load(INTERIM/f'gate_0f_model_{cfg}.pt',map_location='cpu',weights_only=False); mm=TinyECGCNN(len(CONFIGS[cfg])); mm.load_state_dict(m['state_dict']); p=predict(mm,xt,CONFIGS[cfg]); b=(p>=thresholds[cfg]).astype(int)
        for i,(rid,prob,bi) in enumerate(zip(test.ecg_row_record,p,b)): probs.append({'test_id':rid,'configuration':cfg,'probability':float(prob),'threshold':thresholds[cfg],'binary_prediction':int(bi)})
        out=pd.DataFrame({'ecg_row_record':test.ecg_row_record,'ecg_med_record':test.ecg_med_record,'OMI':b}); out.to_csv(RES/fn,index=False)
        assert len(out)==len(test) and out.ecg_row_record.equals(test.ecg_row_record) and out.OMI.isin([0,1]).all() and not out.duplicated('ecg_row_record').any()
        subrows.append({'configuration':cfg,'filename':fn,'sha256':sha256(RES/fn),'n_rows':len(out),'n_positive_predictions':int(b.sum()),'submission_timestamp':'NOT_SUBMITTED','technical_resubmission':'NO'})
    pd.DataFrame(probs).to_csv(RES/'gate_0f_test_probabilities_internal.csv',index=False); pd.DataFrame(subrows).to_csv(RES/'gate_0f_submission_manifest.csv',index=False)
    print('FREEZE_READY',mh); print(pd.DataFrame(rows).to_string(index=False)); print(pd.DataFrame(subrows).to_string(index=False))

if __name__=='__main__': main()
