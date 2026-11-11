from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import wfdb

ROOT = Path(r"<ROOT>")
META = ROOT / "02_data" / "metadata_raw" / "CSV"
WAVE = ROOT / "02_data" / "interim" / "waveforms_raw" / "row_data"
INTERIM = ROOT / "02_data" / "interim"
RES = ROOT / "03_results"
SEED = 20260813
N_SPLITS = 5
EPOCHS = 10
BATCH = 256
FS = 500
N_POINTS = 500
CONFIGS = {
    "C0": list(range(12)),
    "C1": list(range(6)),
    "C2": list(range(6, 12)),
    "C3": [0, 1, 2],
    "E1": [0],
    "E2": [1],
}
LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]


class TinyECGCNN(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(channels, 32, 11, padding=5), nn.BatchNorm1d(32), nn.ReLU(), nn.MaxPool1d(4),
            nn.Conv1d(32, 64, 9, padding=4), nn.BatchNorm1d(64), nn.ReLU(), nn.MaxPool1d(4),
            nn.Conv1d(64, 96, 7, padding=3), nn.BatchNorm1d(96), nn.ReLU(), nn.AdaptiveAvgPool1d(1),
        )
        self.fc = nn.Linear(96, 1)

    def forward(self, x):
        return self.fc(self.net(x).squeeze(-1)).squeeze(-1)


def seed_all(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)


def record_id(v) -> str:
    return Path(str(v)).stem.zfill(5)


def load_waveforms(df: pd.DataFrame, cache: Path) -> np.ndarray:
    if cache.exists():
        arr = np.load(cache, mmap_mode="r")
        if arr.shape == (len(df), 12, N_POINTS): return np.asarray(arr, dtype=np.float32)
    out = np.empty((len(df), 12, N_POINTS), dtype=np.float32)
    for i, rid in enumerate(df.ecg_id):
        rec = wfdb.rdrecord(str(WAVE / rid))
        x = np.asarray(rec.p_signal, dtype=np.float32).T
        if x.shape != (12, 5000): raise ValueError(f"{rid}: unexpected {x.shape}")
        x = x.reshape(12, N_POINTS, FS*10//N_POINTS).mean(axis=2)
        # Per-record, per-lead normalization is fixed for every configuration.
        med = np.nanmedian(x, axis=1, keepdims=True)
        scale = np.nanstd(x, axis=1, keepdims=True)
        x = np.nan_to_num((x - med) / np.maximum(scale, 1e-3), nan=0.0, posinf=0.0, neginf=0.0)
        out[i] = x
        if (i + 1) % 1000 == 0: print(f"waveforms {i+1}/{len(df)}", flush=True)
    np.save(cache, out)
    return out


def train_one(x, y, weights, tr, va, channels, seed):
    seed_all(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TinyECGCNN(len(channels)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    xt = torch.from_numpy(x[tr][:, channels]).float(); yt = torch.from_numpy(y[tr]).float(); wt = torch.from_numpy(weights[tr]).float()
    loader = DataLoader(TensorDataset(xt, yt, wt), batch_size=BATCH, shuffle=True, generator=torch.Generator().manual_seed(seed), num_workers=0)
    model.train()
    for _ in range(EPOCHS):
        for xb, yb, wb in loader:
            xb, yb, wb = xb.to(device), yb.to(device), wb.to(device)
            loss = (nn.functional.binary_cross_entropy_with_logits(model(xb), yb, reduction="none") * wb).sum() / wb.sum()
            opt.zero_grad(); loss.backward(); opt.step()
    model.eval()
    with torch.no_grad():
        def pred(idx):
            vals=[]
            for start in range(0, len(idx), BATCH):
                xb=torch.from_numpy(x[idx[start:start+BATCH]][:,channels]).float().to(device)
                vals.append(torch.sigmoid(model(xb)).cpu().numpy())
            return np.concatenate(vals)
        return pred(va), model


def spec_at_sens(y, p, target):
    order = np.argsort(-p); ys = y[order]; ps = p[order]
    sens = np.cumsum(ys) / max(ys.sum(), 1)
    ok = np.where(sens >= target)[0]
    if len(ok) == 0: return np.nan, np.nan, np.nan
    k = ok[0]; tau = ps[k]
    pred = p >= tau
    return float((pred[y == 0] == 0).mean()), float(tau), float((pred[y == 1]).mean())


def bootstrap_pair(df, cfg0, cfg1, target=0.95, n=1000):
    rng=np.random.default_rng(SEED+99); pats=df.patient_id.unique(); by={p:g.index.to_numpy() for p,g in df.groupby("patient_id")}
    vals=[]
    for _ in range(n):
        chosen=rng.choice(pats, len(pats), replace=True); ix=np.concatenate([by[p] for p in chosen]); d=df.loc[ix]
        s0=spec_at_sens(d.omi.to_numpy(), d[cfg0].to_numpy(), target)[0]; s1=spec_at_sens(d.omi.to_numpy(), d[cfg1].to_numpy(), target)[0]
        if np.isfinite(s0) and np.isfinite(s1): vals.append(s1-s0)
    return float(np.quantile(vals,.025)), float(np.quantile(vals,.975)), float(np.median(vals))


def main():
    seed_all(SEED); RES.mkdir(parents=True, exist_ok=True); INTERIM.mkdir(parents=True, exist_ok=True)
    train=pd.read_csv(META/"train.csv"); train["ecg_id"]=train.ecg_row_record.map(record_id)
    bad={"03228","14262"}; train=train[~train.ecg_id.isin(bad)].reset_index(drop=True)
    train["patient_id"]=train.Patient_id.astype(str); train["omi"]=train.OMI.astype(int)
    x=load_waveforms(train, INTERIM/"gate_0e_train_downsampled.npy")
    counts=train.patient_id.value_counts(); train["patient_weight"]=train.patient_id.map(1/counts).astype(float)
    class_weight = np.where(train.omi.to_numpy() == 1, 1.0 / train.omi.mean(), 1.0 / (1.0 - train.omi.mean()))
    train["training_weight"] = train.patient_weight.to_numpy() * class_weight
    train["LAD"] = ((train.PLAD == 1) | (train.MLAD == 1) | (train.DLAD == 1)).astype(int)
    train["RCA"] = ((train.PRCA == 1) | (train.MRCA == 1) | (train.DRCA == 1)).astype(int)
    train["LCx"] = ((train.PLCX == 1) | (train.MLCX == 1) | (train.DLCX == 1) | (train.OM == 1)).astype(int)
    sg=StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    folds=np.full(len(train),-1,dtype=int)
    for f,(_,va) in enumerate(sg.split(train, train.omi, train.patient_id)): folds[va]=f
    fold_path=INTERIM/"gate_0e_patient_fold_assignment.csv"; pd.DataFrame({"patient_id":train.patient_id,"fold":folds}).drop_duplicates().sort_values("patient_id").to_csv(fold_path,index=False)
    preds=[]; channel_fail=[]; models={}
    for cfg,chs in CONFIGS.items():
        p=np.full(len(train),np.nan)
        for f in range(N_SPLITS):
            tr=np.where(folds!=f)[0]; va=np.where(folds==f)[0]
            pv,model=train_one(x,train.omi.to_numpy(),train.training_weight.to_numpy(),tr,va,chs,SEED+f+100*list(CONFIGS).index(cfg))
            p[va]=pv
            if cfg=="C0": models[f]=model
        train[cfg]=p
        for i,row in train[["ecg_id","patient_id","omi"]].iterrows(): preds.append({"ecg_id":row.ecg_id,"patient_id":row.patient_id,"omi_label":row.omi,"fold":int(folds[i]),"configuration":cfg,"oof_probability":float(p[i])})
    pd.DataFrame(preds).to_csv(RES/"gate_0e_oof_predictions.csv",index=False)
    # C0 single-input masking uses the already-fitted fold model, without retraining.
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    c0=train.C0.to_numpy();
    for lead,lead_name in enumerate(LEADS):
        pm=np.full(len(train),np.nan)
        for f in range(N_SPLITS):
            va=np.where(folds==f)[0]; model=models[f].to(device).eval()
            with torch.no_grad():
                xb=torch.from_numpy(x[va].copy()).float(); xb[:,lead,:]=0; vals=[]
                for st in range(0,len(va),BATCH): vals.append(torch.sigmoid(model(xb[st:st+BATCH].to(device))).cpu().numpy())
            pm[va]=np.concatenate(vals)
        s0,t0,_=spec_at_sens(train.omi.to_numpy(),c0,.95); sm,tm,_=spec_at_sens(train.omi.to_numpy(),pm,.95)
        channel_fail.append({"masked_lead":lead_name,"auroc":roc_auc_score(train.omi,pm),"delta_auroc":roc_auc_score(train.omi,pm)-roc_auc_score(train.omi,c0),"spec95":sm,"delta_spec95":sm-s0,"tau95":tm})
    pd.DataFrame(channel_fail).to_csv(RES/"gate_0e_channel_failure.csv",index=False)
    perf=[]; taus={}
    for cfg in CONFIGS:
        y=train.omi.to_numpy(); p=train[cfg].to_numpy(); s,t,sens=spec_at_sens(y,p,.95); s975,t975,_=spec_at_sens(y,p,.975); taus[cfg]=t
        perf.append({"configuration":cfg,"lead_set":";".join(LEADS[i] for i in CONFIGS[cfg]),"n_ecg":len(train),"n_patients":train.patient_id.nunique(),"n_omi_patients":train.loc[train.omi==1,"patient_id"].nunique(),"auroc":roc_auc_score(y,p),"auprc":average_precision_score(y,p),"brier":brier_score_loss(y,p),"tau95":t,"sensitivity_at_tau95":sens,"specificity_at_tau95":s,"ppv_at_tau95":float((p>=t)[y==1].sum()/max((p>=t).sum(),1)),"npv_at_tau95":float(((p<t)&(y==0)).sum()/max((p<t).sum(),1)),"spec97_5":s975,"tau97_5":t975})
    perfdf=pd.DataFrame(perf); perfdf["delta_auroc_vs_C0"]=perfdf.auroc-perfdf.loc[perfdf.configuration=="C0","auroc"].iloc[0]; perfdf["delta_spec95_vs_C0"]=perfdf.specificity_at_tau95-perfdf.loc[perfdf.configuration=="C0","specificity_at_tau95"].iloc[0]; perfdf.to_csv(RES/"gate_0e_configuration_performance.csv",index=False)
    primary=perfdf[perfdf.configuration.isin(["C0","C1","C2","C3"])].copy(); primary[["configuration","tau95","sensitivity_at_tau95","specificity_at_tau95","spec97_5","auroc","auprc","brier","delta_auroc_vs_C0","delta_spec95_vs_C0"]].to_csv(RES/"gate_0e_high_sensitivity_tradeoff.csv",index=False)
    contrasts=[]; base=perfdf.loc[perfdf.configuration=="C0"].iloc[0]
    for cfg in ["C1","C2","C3"]:
        lo,hi,med=bootstrap_pair(train,"C0",cfg,.95,1000); contrasts.append({"contrast":f"{cfg}-C0","delta_spec95":float(perfdf.loc[perfdf.configuration==cfg,"specificity_at_tau95"].iloc[0]-base.specificity_at_tau95),"ci_low":lo,"ci_high":hi,"bootstrap_median":med,"delta_auroc":float(perfdf.loc[perfdf.configuration==cfg,"auroc"].iloc[0]-base.auroc)})
    pd.DataFrame(contrasts).to_csv(RES/"gate_0e_paired_contrasts.csv",index=False)
    terr=[]
    for cfg in ["C0","C1","C2","C3"]:
        for terr_name,mask in [("LAD",train.LAD==1),("RCA",train.RCA==1),("LCx",train.LCx==1)]:
            d=train[mask];
            if d.omi.nunique()==2: terr.append({"configuration":cfg,"territory":terr_name,"n_ecg":len(d),"n_omi":int(d.omi.sum()),"auroc":roc_auc_score(d.omi,d[cfg])})
    pd.DataFrame(terr).to_csv(RES/"gate_0e_territory_sensitivity.csv",index=False)
    manifest = {"model":"TinyECGCNN","torch":torch.__version__,"seed":SEED,"epochs":EPOCHS,"batch":BATCH,"input_points":N_POINTS,"normalization":"per-record per-lead z-score after fixed 10x downsample","configs":";".join(CONFIGS)}
    pd.DataFrame([manifest]).to_csv(ROOT/"02_data"/"manifests"/"gate_0e_model_manifest.csv", index=False)


if __name__ == "__main__": main()
