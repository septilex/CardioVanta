# Design: R7 — Unverified Feature Ablation (pre-registered before execution)

## Data
- The development-only loader is reused from `experiments/r4_ca_count_encoding.py` (`load_development_data`).
  - It parses only the header and the 242 development-row lines; locked-row lines are discarded unparsed.
  - It verifies the SHA-256 of `heart.csv` and `dev_indices.json` against production provenance metadata.
- **Target:** disease-positive orientation, `disease = 1 − target`.
- **Groups:** duplicate-aware (identical 13-feature rows share a group). Groups are always defined on all 13 features, so every arm uses the same groups and splits.

## Arms
| Arm | Features removed | Inputs |
|---|---|---|
| **A_baseline** | none | 13 |
| **B_no_slope** | `slope` | 12 |
| **C_no_thal** | `thal` | 12 |
| **D_no_ca** | `ca` | 12 |
| **E_no_slope_thal_ca** | `slope`, `thal`, `ca` | 10 |

Every arm uses the production recipe, restricted to its own inputs:
- StandardScaler on the continuous inputs;
- passthrough for the binary inputs;
- `OneHotEncoder(handle_unknown="ignore")` for the remaining categorical inputs;
- `LogisticRegression(class_weight="balanced", solver="lbfgs", max_iter=2000, random_state=42)`;
- `CalibratedClassifierCV(method="sigmoid", ensemble=True)` with 5 duplicate-aware `StratifiedGroupKFold` calibration folds of the outer-training partition.

A removed feature is dropped before the preprocessor, so the arm never sees it. No code is recoded, merged or given a meaning.

## Protocol
- **Outer loop:** `StratifiedGroupKFold(5, shuffle=True, random_state=1000+r)`, r = 0…9. The splits are identical for all arms.
- **Inner tuning (per arm, inside the outer-training partition only):** C ∈ {0.01, 0.03, 0.1, 0.3, 1, 3}.
  - Each C is scored by inner `StratifiedGroupKFold(5, shuffle=True, random_state=2000+r)` OOF log loss of the arm's calibrated model (3 inner calibration folds).
  - Ties go to the smaller C.
- **Final model per outer fold:** the arm's calibrated model with the selected C and 5 calibration folds (seed `3000+r`).
- **Secondary analysis (descriptive):** C fixed at 0.1 (the production value), on the same splits.
- **Execution:** independent (repeat, arm) tasks can run in parallel processes. Every task is a deterministic function of its seeds, and results are assembled by index.

## Metrics (outer-fold OOF predictions, per repeat)
- **Primary:** ROC-AUC and log loss.
- **Secondary:**
  - PR-AUC;
  - Brier score;
  - calibration slope (unpenalized LR of y on logit p, `C=np.inf`) and |slope − 1|;
  - calibration intercept (slope fixed at 1);
  - calibration-in-the-large;
  - ECE (10 bins).

## Uncertainty
- **Repeat level:** paired per-repeat differences (arm − A), giving the mean, the 2.5/97.5 percentiles, and the count of repeats favouring each side.
- **Paired group bootstrap:** 2,000 resamples of duplicate groups (seed 42).
  - In each resample, metrics are computed per repeat on the resampled patients and then averaged over repeats.
  - The output is 95% percentile CIs for each arm's metrics and for Δ = arm − A.
  - Bonferroni intervals at 98.75% (4 comparisons) are a sensitivity analysis.

## Pre-registered hypotheses
- **H7.1 (`thal`):** removing `thal` shows dependence, as defined below. The expectation comes from R5's prediction sensitivity to `thal`; it is statistical, not clinical.
- **H7.2 (`slope`) and H7.3 (`ca`):** no directional expectation (two-sided, exploratory).
- **H7.4 (all three):** the point estimate of Δlog loss for E is at least as large as the largest single-feature Δlog loss.

## Pre-registered classification (primary analysis, each of B, C, D and E against A, 95% bootstrap CIs)
- **Dependence detected:** ΔROC-AUC CI upper bound < 0, **or** Δlog loss CI lower bound > 0.
- **Non-inferior without the feature(s):** ΔROC-AUC CI lower bound ≥ −0.01 **and** Δlog loss CI upper bound ≤ +0.01.
- **Label:**
  - `material_dependence` if dependence is detected and non-inferiority is not met;
  - `dependence_within_margin` if both hold;
  - `non_inferior` if only non-inferiority holds;
  - `inconclusive` if neither holds.
- **Robustness:** a label is `robust_to_multiplicity` if the Bonferroni intervals give the same label.
- **Scope:** the secondary metrics and the fixed-C analysis are descriptive and do not change any label.

H7.1 is supported if C's label is `material_dependence` or `dependence_within_margin`. H7.4 is evaluated on point estimates.

## Interpretation guard
A label describes statistical dependence of this recipe on the Kaggle training encoding, on 242 patients. It does not establish what any code means. It does not justify removing a feature from production, which would need a separately registered model version, and it is not external validation.

## Acceptance criteria for the run
1. Exactly 242 rows are used, and 0 locked rows are parsed.
2. The outer test folds are identical across arms and across the primary and secondary analyses (fold hash recorded).
3. Two full runs give identical result content, excluding runtime.
4. The artifact integrity check passes, and the contract SHA-256 is unchanged.
5. The only output is `experiments/results/r7_unverified_feature_ablation.json`.
