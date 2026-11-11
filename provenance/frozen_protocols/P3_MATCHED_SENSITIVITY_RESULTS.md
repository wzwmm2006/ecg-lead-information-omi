# P3 MATCHED-SENSITIVITY RESULTS

Topic890 / Scientific Reports R2
Task: `TOPIC890_P3_MATCHED_SENSITIVITY`
Date: 2026-11-10
Mode: READ_ONLY_ANALYSIS_ONLY

---

# FINAL VERDICT

# `MATCHED_SENSITIVITY_PARTIALLY_SUPPORTED`

After interpolating each fold's empirical ROC to TPR = 0.9500, all nine
fold-weighted ΔSpecificity contrasts are negative. However, only 2 of 9
patient-cluster bootstrap intervals exclude zero, and several folds reverse
direction. Therefore, the matched-sensitivity analysis supports a direction but
does not support a uniformly precise or cross-condition effect.

---

## 1. Estimand and method

This is a post hoc operating-point analysis. The frozen plan is in
`P3_MATCHED_SENSITIVITY_ANALYSIS_PLAN.md` (SHA-256
`698f058926fd2730dd190a13e92d4e32bd67e96f5e12ae0ca00f9173f83000ec`).

For each outer fold and configuration:
- the empirical ROC is built from the stored outer-evaluation probability and
  OMI label;
- the first ROC vertex pair bracketing TPR = 0.9500 is linearly interpolated;
- `Specificity_at_TPR95 = 1 − interpolated FPR`;
- folds are weighted by the number of non-OMI ECGs;
- no cross-fold pooled scores are used.

The result is an estimated ROC operating point. It is not a deterministic
classifier threshold and is not a replacement for the frozen locked thresholds.

## 2. All fold-weighted results

Non-OMI weighted specificity at TPR95:

| Analysis | C0 | C1 | C2 | C3 |
|---|---:|---:|---:|---:|
| A1 Seed A | **0.4387** | 0.4044 | 0.3334 | 0.3603 |
| A1 Seed B | **0.4139** | 0.3638 | 0.3854 | 0.3612 |
| A2a Seed A | **0.4135** | 0.3488 | 0.3955 | 0.3314 |

Contrasts:

| Analysis | Contrast | Weighted ΔSpec | 95% patient-bootstrap CI | Excess FP/1,000 | Negative folds |
|---|---|---:|---|---:|---:|
| A1 Seed A | C1−C0 | **−0.0343** | −0.1118 to +0.0525 | 34.3 | 3/5 |
| A1 Seed A | C2−C0 | **−0.1053** | −0.1803 to −0.0175 | 105.3 | 4/5 |
| A1 Seed A | C3−C0 | **−0.0784** | −0.1530 to +0.0266 | 78.4 | 4/5 |
| A1 Seed B | C1−C0 | **−0.0502** | −0.1191 to +0.0315 | 50.2 | 3/5 |
| A1 Seed B | C2−C0 | **−0.0285** | −0.1026 to +0.0415 | 28.5 | 3/5 |
| A1 Seed B | C3−C0 | **−0.0528** | −0.1300 to +0.0224 | 52.8 | 3/5 |
| A2a Seed A | C1−C0 | **−0.0646** | −0.1492 to +0.0031 | 64.6 | 4/5 |
| A2a Seed A | C2−C0 | **−0.0180** | −0.0957 to +0.0528 | 18.0 | 3/5 |
| A2a Seed A | C3−C0 | **−0.0820** | −0.1599 to −0.0122 | 82.0 | 5/5 |

Only **A1 Seed A C2−C0** and **A2a C3−C0** have intervals excluding zero. All
nine bootstrap analyses completed 2,000/2,000 valid replicates.

## 3. Fold-level direction

All fold-specific deltas are retained in the CSV; none are removed. The positive
folds are:

| Analysis | Contrast | Positive folds |
|---|---|---|
| A1 Seed A | C1−C0 | folds 1, 3 |
| A1 Seed A | C2−C0 | fold 0 |
| A1 Seed A | C3−C0 | fold 1 |
| A1 Seed B | C1−C0 | folds 1, 2 |
| A1 Seed B | C2−C0 | folds 0, 1 |
| A1 Seed B | C3−C0 | folds 0, 1 |
| A2a | C1−C0 | fold 1 |
| A2a | C2−C0 | folds 0, 1 |
| A2a | C3−C0 | none |

The A1 Seed A C1 fold-1 positive delta is +0.0765, and the A1 Seed B C2 fold-0
positive delta is +0.1437. These are not negligible reversals.

## 4. Did matching remove the association?

Comparing the locked-threshold analysis with TPR95:

| Analysis | Contrast | Locked ΔSpec | TPR95 ΔSpec | Change |
|---|---|---:|---:|---:|
| A1 Seed A | C1−C0 | −0.0972 | −0.0343 | **+0.0629** (weaker) |
| A1 Seed A | C2−C0 | −0.1668 | −0.1053 | **+0.0615** |
| A1 Seed A | C3−C0 | −0.1377 | −0.0784 | **+0.0593** |
| A1 Seed B | C1−C0 | −0.0375 | −0.0502 | −0.0126 (slightly stronger) |
| A1 Seed B | C2−C0 | −0.0387 | −0.0285 | +0.0102 |
| A1 Seed B | C3−C0 | −0.0516 | −0.0528 | −0.0012 (nearly unchanged) |
| A2a | C1−C0 | −0.1073 | −0.0646 | **+0.0427** |
| A2a | C2−C0 | −0.0504 | −0.0180 | **+0.0324** |
| A2a | C3−C0 | −0.1678 | −0.0820 | **+0.0858** |

The original A1 Seed A and A2a contrasts shrink materially after matching. In
Seed B, they are small and mostly unaffected. Two conclusions follow:

1. Some of the locked-threshold specificity cost is associated with unequal
   achieved sensitivity.
2. Matching to TPR95 does not erase the direction, but it also does not produce
   a uniform or statistically precise effect.

The two analyses are nevertheless different estimands. The change cannot be
ascribed solely to sensitivity: the locked result is an independent
calibration/threshold-transport procedure; TPR95 is a post hoc empirical-ROC
interpolation. Both statements must be retained.

## 5. Deterministic TPR ≥95% companion

At the outer-fold first-crossing rule, achieved TPR is 0.9522-0.9524 across all
60 fold/config tasks. The deterministic threshold specificity is numerically
equal to interpolated TPR95 specificity (maximum absolute difference
1.11e-16), because the interpolation lies on the same flat ROC segment.
This confirms numerical consistency but does not make the outer threshold
independent calibration. It remains exploratory.

## 6. Training randomness

A1 Seed A and Seed B differ materially at matched sensitivity:

- C1: −0.0343 vs −0.0502;
- C2: −0.1053 vs −0.0285;
- C3: −0.0784 vs −0.0528.

A2a has one seed only. The matched-sensitivity result therefore preserves the
training-randomness limitation and cannot be used to claim a stable effect
magnitude.

## 7. Scientific limits retained

- The analysis is post hoc; threshold matching was not the original primary
  design.
- TPR95 specificity is an interpolated ROC quantity, not a deployable
  classifier threshold or an independent-validation confusion matrix.
- The patient-cluster intervals condition on existing trained models and
  empirical ROC curves. They do not include retraining, fold reassignment,
  device variation or external hospitals.
- No external validation is represented.
- The three training settings are not independent external cohorts.
- No adjustment for multiple contrasts is applied; no significance claim is made
  beyond the reported intervals.
- No hidden TEST or STAFF III data were accessed.

## 8. What the result means clinically

Under this post hoc matched empirical-ROC sensitivity condition, reduced-lead
configurations consistently have lower *point-estimate* ECG-level specificity
than C0. The absolute excess false-positive classification estimates range
from about **18 to 105 per 1,000 non-OMI ECGs** across the negative contrasts.
These are estimated ROC operating-point differences, not observed counts of
unnecessary CAG, PCI or procedures.

The uncertainty and fold reversals mean the appropriate clinical statement is
directional, not a fixed deployment cost.

## 9. Decision

`MATCHED_SENSITIVITY_PARTIALLY_SUPPORTED`

Reason:
- direction: **9/9 point estimates negative**, so direction-level support;
- precision: **2/9 intervals exclude zero**, so not fully supported;
- fold consistency: several reversals in every analysis;
- seed dependence: material;
- A2a: one seed only.

The original locked-threshold analysis remains the independent-calibration
evidence. P3 does **not** replace it and does not justify changing the original
primary endpoint.
