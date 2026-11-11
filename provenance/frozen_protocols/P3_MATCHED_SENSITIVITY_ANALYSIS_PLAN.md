# P3 MATCHED-SENSITIVITY ANALYSIS PLAN

Topic890 / Scientific Reports R2
Task: `TOPIC890_P3_MATCHED_SENSITIVITY`
Status: **FROZEN BEFORE READING RESULTS**
Date: 2026-11-10
Permission: READ_ONLY_ANALYSIS_ONLY

---

## 1. Question

In the existing patient-isolated outer predictions, after setting the empirical
ROC sensitivity to 0.9500, do reduced ECG lead configurations still show lower
specificity than C0?

This is a post hoc operating-point sensitivity analysis. It does not replace the
principal locked-threshold analysis and it does not create a deployable
threshold.

## 2. Two separate estimands

### A. Locked-threshold analysis (existing, primary independent-calibration evidence)

For A1 and A2a, a threshold was selected on patient-disjoint inner-calibration
patients by the frozen first-crossing >=0.95 rule, locked, and applied once to
the outer-evaluation patients. The outer achieved sensitivity and specificity
are reported as observed. These results remain the primary independent-calibration
evidence.

The original pooled OOF is **not** in this category: its threshold was selected
on the same evaluated OOF records. P3 does not alter or re-label that analysis.

### B. ROC TPR95 matched-sensitivity analysis (new, post hoc)

For each training setting, outer fold and configuration, build the empirical ROC
from the stored outer-evaluation `probability` and `omi_label` columns. Identify
the first adjacent ROC vertex pair bracketing TPR = 0.9500 and linearly
interpolate FPR at that TPR. Report:

```
Specificity_at_TPR95 = 1 - interpolated FPR
Delta_Spec_at_TPR95 = Specificity_at_TPR95(reduced) - Specificity_at_TPR95(C0)
Excess_FP_per_1000_at_TPR95 = -1000 * Delta_Spec_at_TPR95
```

The interpolation is an estimated ROC operating-point specificity. It need not
correspond to an attainable deterministic threshold or a real confusion matrix.

## 3. Unique ROC rules (fixed before results)

1. **One fold at a time.** No pooled cross-fold ROC and no single threshold
   fitted across folds. Fold-specific score scales are not mixed.
2. **Same patients and labels.** C0-C3 rows are joined by ECG ID, patient ID and
   label. A configuration missing any required row aborts the fold.
3. **Score direction.** Higher stored `probability` means more likely OMI.
4. **ROC construction.** Sort unique predicted probabilities in descending
   order. For each unique threshold, FPR and TPR are computed from strict
   `probability >= threshold` decisions. Append the (0,0) ROC point.
5. **TPR target.** TPR = 0.9500 exactly.
6. **Interpolation.** Find the first adjacent ROC vertex pair with
   `TPR_i < 0.9500 <= TPR_j` and `FPR_i != FPR_j`. Interpolate:
   ```
   w = (0.95 - TPR_i) / (TPR_j - TPR_i)
   FPR95 = FPR_i + w * (FPR_j - FPR_i)
   ```
   Save i, j, both TPR/FPR endpoints and `w`.
7. **Ties/platforms.** A vertical ROC segment has `FPR_i == FPR_j`; it is
   traversed without interpolation and cannot define FPR95. A horizontal
   plateau at a lower TPR is not used.
8. **Endpoint rule.** If TPR cannot reach 0.95 because the fold has fewer OMI
   positives than needed for the required rank increment, the fold is invalid
   and reported. No extrapolation beyond the empirical ROC endpoint.
9. **No threshold export.** The interpolated TPR95 is not written as a model
   threshold, not saved as a replacement for the frozen threshold, and not
   described as an independently calibrated decision rule.

## 4. Deterministic-threshold companion (C)

For each fold and configuration, select the first descending-score threshold
reaching `sensitivity >= 0.95` (the same deterministic rule, but here applied to
outer-evaluation rows only for diagnostic purposes). Report its achieved
sensitivity, specificity, and the difference from the interpolated TPR95
specificity. Label all such results **exploratory outer-fold re-selection**; they
are not independent validation.

## 5. Aggregation

Report all five fold-specific values first. Compute the cross-fold specificity as
the non-OMI-ECG-count-weighted average of fold-specific specificities, and the
cross-fold difference as the non-OMI-count-weighted average of fold-specific
paired differences. Do not substitute a simple unweighted mean or a pooled-score
ROC.

## 6. Patient-cluster bootstrap

- Replicates: **2,000**
- RNG seed: **20261110**
- Unit: patient, sampled with replacement separately within each outer fold.
- All ECGs of a sampled patient enter together.
- The same sampled patient set is used simultaneously for C0, C1, C2 and C3 to
  preserve pairing.
- Each replicate recomputes all empirical ROCs, TPR95 specificity values and
  cross-fold weighted differences.
- 95% percentile interval: 2.5th and 97.5th percentiles.
- Any replicate without a valid ROC for any configuration is counted and its
  reason logged. It is not silently dropped. If invalid replicates materially
  prevent 2,000 valid computations, analysis stops and reports a blocker.
- The interval covers patient sampling and empirical ROC operating-point
  uncertainty **conditional on the existing trained models**. It does not cover
  retraining, fold reassignment, device variation or external hospitals.

## 7. Analyses and outputs

Analyses are fixed:
- A1 Seed A: C0-C3, five folds
- A1 Seed B: C0-C3, five folds
- A2a Seed A: C0-C3, five folds

All three contrasts C1-C0, C2-C0, C3-C0 are mandatory and reported together.

Outputs:
- per-fold TPR95 endpoints, weight and specificity;
- per-configuration fold-weighted specificity;
- per-contrast weighted ΔSpecificity and excess FP per 1,000 non-OMI ECGs;
- fold signs and counts;
- locked-threshold versus TPR95 comparison;
- deterministic first-crossing comparison;
- 2,000-replicate patient-cluster bootstrap;
- consistency checks (prediction completeness, row pairing, score direction,
  range, denominator arithmetic).

## 8. Decision rules

- `MATCHED_SENSITIVITY_SUPPORTED`: all three reductions have negative weighted
  ΔSpecificity in all three analyses and their paired intervals support the
  direction, with fold/effect/ad-hoc caveats explicitly retained.
- `MATCHED_SENSITIVITY_PARTIALLY_SUPPORTED`: direction has some support but
  configuration, seed, interval or fold reversal limits remain.
- `MATCHED_SENSITIVITY_INCONCLUSIVE`: insufficient reliable direction evidence.
- `MATCHED_SENSITIVITY_NOT_SUPPORTED`: matched-sensitivity analysis clearly does
  not show the original direction.

This plan is frozen before executing the analysis. No post-result change to
target TPR, interpolation, fold weighting or bootstrap rules is permitted.
