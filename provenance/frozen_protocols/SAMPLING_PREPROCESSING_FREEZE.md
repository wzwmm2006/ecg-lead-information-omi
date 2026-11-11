# Sampling preprocessing freeze

Status: FROZEN BEFORE TRAINING

Authority: `D:\老婆资料\论文\Topic890\02_data`

The native clinical ECG is 500 Hz, 5,000 samples per 10-second record and 12 leads. For target rate `r`, the integer block size is `b = 500/r`, and the deterministic reduction is:

`y[k] = mean(x[b*k : b*k+b])`

The blocks are non-overlapping. No learned preprocessing or rate-specific tuning is used. Per-record, per-lead median centering and standard-deviation scaling occur after reduction, with a minimum scale of `1e-3` and non-finite values converted to zero.

| Rate | Block size | Output samples/lead | Explicit anti-alias filter |
|---:|---:|---:|---|
| 50 Hz primary | 10 | 500 | None; block mean is boxcar smoothing before decimation |
| 100 Hz sensitivity | 5 | 1,000 | None; block mean is boxcar smoothing before decimation |
| 250 Hz sensitivity | 2 | 2,500 | None; block mean is boxcar smoothing before decimation |

The same model architecture, channel configurations, patient folds, labels, training policy, seed policy, operating-point rule, and patient-level bootstrap framework are used at 100 and 250 Hz. The only input change is temporal length caused by the target sampling rate. Primary 50-Hz artifacts are not overwritten.

Code path: `05_code/r2_sampling_run.py`.

## Source hashes

- `02_data/metadata_raw/CSV/train.csv`: `15FDB9B576DA88ACC31D07612E457848A3D3502EA4955FFD3FED845968310907`
- `02_data/interim/gate_0e_patient_fold_assignment.csv`: `DE06A73B48552F6572AC4923D22C70B5443FC1E58B416F0201E3A760F9905C52`
- `05_code/gate_0e_spatial_pilot.py`: `B8BCEA13450DAA29904FB6D78646D9CA9305BAB2F772AD62DBC9A8A16FBB6922`
