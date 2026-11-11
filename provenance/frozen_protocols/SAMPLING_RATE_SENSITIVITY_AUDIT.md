# Sampling-rate sensitivity audit

- Primary 50-Hz artifacts were read without retraining or modification.
- Cohort, labels, folds, architecture, training policy, and operating rule matched the frozen specification.
- 100-Hz and 250-Hz C1-C3 contrasts were all negative: True.
- All six 95% bootstrap CIs remained below zero: True.
- No rate-specific optimization, hidden TEST access, STAFF III analysis, or primary artifact modification occurred.

## NO-NEW-PROBLEM GATE

`NO_NEW_PROBLEM_GATE = PASS`

`ROBUST_DIRECTIONAL_PASS = PASS`
