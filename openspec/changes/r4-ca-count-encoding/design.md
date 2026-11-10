# Design: R4 — Count Encoding of `ca` (pre-registered before execution)

## Data
- **Source:** `data/raw/heart.csv`. The SHA-256 must equal the value in the production provenance metadata.
- **Rows used:** only the 242 rows listed in `data/processed/dev_indices.json` (SHA-256 also checked).
- **Reading:** the file is read line by line, and only header and development-row lines are parsed. Locked-row lines are discarded unparsed, so the 61 locked observations are never parsed, inspected or used.
- **Target:** harmonised to clinical orientation, `disease = 1 − target` (Phase 17 finding; R0.3 orientation). ROC-AUC, Brier score and log loss are invariant in magnitude under this relabelling when probabilities are flipped consistently; it is applied for interpretability.
- **Groups:** duplicate-aware. Identical feature rows share a group, as in production (`phase5.py`).

## Arms (identical except for `ca` encoding)

| Arm | Continuous (5) | Binary (3) | Categorical | `ca` | Model |
|---|---|---|---|---|---|
| **Baseline**, the production recipe | StandardScaler | passthrough | OneHotEncoder(ignore) for cp, restecg, slope, ca, thal | 5 one-hot columns | LR, `class_weight="balanced"`, lbfgs |
| **Candidate** | StandardScaler | passthrough | OneHotEncoder(ignore) for cp, restecg, slope, thal | `ca_count` (codes 0–3; 0 for code 4), standardized fold-locally, plus `ca_code4` indicator | same |

## Primary analysis: repeated nested cross-validation
- **Outer loop:** `StratifiedGroupKFold(5, shuffle=True, random_state=1000+r)`, repeated r = 0…9.
- **Inner tuning:** C ∈ {0.01, 0.03, 0.1, 0.3, 1, 3}.
  - Each candidate C is scored by inner `StratifiedGroupKFold(5, shuffle=True, random_state=2000+r)` OOF log loss of a sigmoid-calibrated model.
  - The calibration CV is `StratifiedGroupKFold(3)` on the inner-training groups.
  - Ties go to the smaller C.
- **Final model per outer fold:** `CalibratedClassifierCV(method="sigmoid")` on the outer-training data, with `StratifiedGroupKFold(5)` duplicate-aware calibration splits (the production calibration design).
- **Secondary analysis:** the same outer splits with C fixed at 0.1 (the production value), which isolates the encoding effect from tuning.

## Metrics (on outer-fold out-of-fold predictions)
- **Discrimination:** ROC-AUC, PR-AUC.
- **Calibration:** Brier score, log loss, ECE (10 equal-width bins), calibration slope (logistic recalibration of logit p), calibration-in-the-large (mean y − mean p).
- **Robustness:** per-patient standard deviation of OOF probability across the 10 repeats (prediction stability), and the distribution of selected C.
- **Uncertainty:** distribution across repeats (mean and 2.5/97.5 percentiles), plus a paired, group-level bootstrap (2,000 resamples, seed 42) of repeat-averaged OOF probabilities for ΔAUC, ΔBrier, Δlog loss and ΔECE.

## Pre-registered decision rule
Candidate − baseline, primary analysis, paired bootstrap 95% CI. H1 is **supported** only if both conditions hold:
1. **Non-inferior discrimination:** the lower CI bound of ΔAUC ≥ −0.01.
2. **Improved calibration:** the upper CI bound of Δlog loss < 0, **or** the upper CI bound of ΔBrier < 0.

Otherwise H1 is **not supported**. Prediction stability is reported descriptively and does not change the verdict.

## Reproducibility
- All seeds are fixed.
- The experiment is run twice, and the result content (excluding timestamps and runtime) must be identical.
- Outputs are written only to `experiments/results/r4_ca_count_encoding.json`.
