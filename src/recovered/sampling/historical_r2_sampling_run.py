from pathlib import Path
import random
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, roc_auc_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import wfdb

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'revision_r2_sampling'; CACHE=OUT/'cache'; MODEL=OUT/'models'
META=ROOT/'02_data/metadata_raw/CSV/train.csv'; WAVE=ROOT/'02_data/interim/waveforms_raw/row_data'; FOLDS=ROOT/'02_data/interim/gate_0e_patient_fold_assignment.csv'
BASE=20260813; BOOT_SEED=20260912; EPOCHS=10; BATCH=256; FS=500; TARGET=.95; NBOOT=1000
CONFIGS={'C0':list(range(12)),'C1':list(range(6)),'C2':list(range(6,12)),'C3':[0,1,2]}
class TinyECGCNN(nn.Module):
 def __init__(self,n):
  super().__init__(); self.net=nn.Sequential(nn.Conv1d(n,32,11,padding=5),nn.BatchNorm1d(32),nn.ReLU(),nn.MaxPool1d(4),nn.Conv1d(32,64,9,padding=4),nn.BatchNorm1d(64),nn.ReLU(),nn.MaxPool1d(4),nn.Conv1d(64,96,7,padding=3),nn.BatchNorm1d(96),nn.ReLU(),nn.AdaptiveAvgPool1d(1)); self.fc=nn.Linear(96,1)
 def forward(self,x): return self.fc(self.net(x).squeeze(-1)).squeeze(-1)
def seed(s):
 random.seed(s); np.random.seed(s); torch.manual_seed(s)
 if torch.cuda.is_available(): torch.cuda.manual_seed_all(s)
def rid(v): return Path(str(v)).stem.zfill(5)
def prep(df,rate):
 b=FS//rate; n=FS*10//b; path=CACHE/f'train_{rate}hz.npy'
 if path.exists(): return np.load(path,mmap_mode='r')
 out=np.empty((len(df),12,n),np.float32)
 for i,r in enumerate(df.ecg_id):
  rec=wfdb.rdrecord(str(WAVE/r)); x=np.asarray(rec.p_signal,dtype=np.float32).T
  if x.shape!=(12,5000) or float(rec.fs)!=500: raise RuntimeError(f'waveform mismatch {r}')
  x=x.reshape(12,n,b).mean(axis=2); med=np.nanmedian(x,axis=1,keepdims=True); sd=np.nanstd(x,axis=1,keepdims=True)
  out[i]=np.nan_to_num((x-med)/np.maximum(sd,1e-3),nan=0.,posinf=0.,neginf=0.)
 CACHE.mkdir(parents=True,exist_ok=True); np.save(path,out); return out
def train(x,y,w,tr,va,ch,s):
 seed(s); dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); m=TinyECGCNN(len(ch)).to(dev); opt=torch.optim.AdamW(m.parameters(),lr=1e-3,weight_decay=1e-4)
 dl=DataLoader(TensorDataset(torch.from_numpy(np.asarray(x[tr][:,ch])).float(),torch.from_numpy(y[tr]).float(),torch.from_numpy(w[tr]).float()),batch_size=BATCH,shuffle=True,generator=torch.Generator().manual_seed(s),num_workers=0)
 m.train()
 for _ in range(EPOCHS):
  for xb,yb,wb in dl:
   xb,yb,wb=xb.to(dev),yb.to(dev),wb.to(dev); loss=(nn.functional.binary_cross_entropy_with_logits(m(xb),yb,reduction='none')*wb).sum()/wb.sum(); opt.zero_grad(); loss.backward(); opt.step()
 m.eval(); z=[]
 with torch.no_grad():
  for st in range(0,len(va),BATCH): z.append(torch.sigmoid(m(torch.from_numpy(np.asarray(x[va[st:st+BATCH]][:,ch])).float().to(dev))).cpu().numpy())
 return np.concatenate(z)
def operating(y,p):
 o=np.argsort(-p); ys=y[o]; k=np.where(np.cumsum(ys)/max(ys.sum(),1)>=TARGET)[0][0]; tau=p[o[k]]; pred=p>=tau; return float((pred[y==0]==0).mean()),float((pred[y==1]).mean()),float(tau)
def boot(d,c):
 rng=np.random.default_rng(BOOT_SEED); pats=d.patient_id.unique(); by={p:g.index.to_numpy() for p,g in d.groupby('patient_id')}; vals=[]
 for _ in range(NBOOT):
  ix=np.concatenate([by[p] for p in rng.choice(pats,len(pats),replace=True)]); q=d.loc[ix]; vals.append(operating(q.omi.to_numpy(),q[c].to_numpy())[0]-operating(q.omi.to_numpy(),q.C0.to_numpy())[0])
 return np.quantile(vals,[.025,.5,.975])
def main():
 OUT.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True); MODEL.mkdir(exist_ok=True)
 df=pd.read_csv(META); df['ecg_id']=df.ecg_row_record.map(rid); df=df[~df.ecg_id.isin({'03228','14262'})].reset_index(drop=True); df['patient_id']=df.Patient_id.astype(str); df['omi']=df.OMI.astype(int); fmap=pd.read_csv(FOLDS).set_index('patient_id').fold; df['fold']=df.patient_id.map(fmap).astype(int)
 counts=df.patient_id.value_counts(); prevalence=df.omi.mean(); df['weight']=df.patient_id.map(1/counts).to_numpy()*np.where(df.omi.to_numpy()==1,1/prevalence,1/(1-prevalence))
 allrows=[]; bootrows=[]
 for rate in (100,250):
  x=prep(df,rate); wide=df[['ecg_id','patient_id','omi','fold']].copy()
  for pos,(c,ch) in enumerate(CONFIGS.items()):
   p=np.full(len(df),np.nan)
   for f in range(5):
    tr=np.where(df.fold.to_numpy()!=f)[0]; va=np.where(df.fold.to_numpy()==f)[0]; p[va]=train(x,df.omi.to_numpy(),df.weight.to_numpy(),tr,va,ch,BASE+f+100*pos)
   wide[c]=p
  y=wide.omi.to_numpy()
  for c in CONFIGS:
   s,sen,t=operating(y,wide[c].to_numpy()); allrows.append({'sampling_rate_hz':rate,'configuration':c,'n_ecg':len(y),'n_patients':wide.patient_id.nunique(),'n_omi_patients':wide.loc[wide.omi==1,'patient_id'].nunique(),'auroc':roc_auc_score(y,wide[c]),'auprc':average_precision_score(y,wide[c]),'sensitivity':sen,'spec95':s,'threshold':t,'delta_spec95_vs_same_rate_C0':np.nan})
  base=[r['spec95'] for r in allrows if r['sampling_rate_hz']==rate and r['configuration']=='C0'][0]
  for r in allrows:
   if r['sampling_rate_hz']==rate: r['delta_spec95_vs_same_rate_C0']=r['spec95']-base
  for c in ('C1','C2','C3'):
   lo,med,hi=boot(wide,c); bootrows.append({'sampling_rate_hz':rate,'contrast':c+'-C0','delta_spec95':float([r for r in allrows if r['sampling_rate_hz']==rate and r['configuration']==c][0]['delta_spec95_vs_same_rate_C0']),'ci_low':lo,'bootstrap_median':med,'ci_high':hi,'replicates':NBOOT,'seed':BOOT_SEED})
  wide.to_csv(OUT/f'OOF_{rate}HZ.csv',index=False)
 pd.DataFrame(allrows).to_csv(OUT/'SAMPLING_RATE_SENSITIVITY_RESULTS.csv',index=False); pd.DataFrame(bootrows).to_csv(OUT/'SAMPLING_BOOTSTRAP_RESULTS.csv',index=False)
if __name__=='__main__': main()
