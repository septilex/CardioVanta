# Design: H2 — Calibration of the Production Recipe (pre-registered before execution)

## Data
- The development-only loader is reused from `experiments/r4_ca_count_encoding.py` (`load_development_data`).
  - It parses only the header and the 242 development-row lines; locked-row lines are discarded unparsed.
  - It verifies the SHA-256 of `heart.csv` and `dev_indices.json` against production provenance metadata.
- **Target:** `disease = 1 − target`.
- **Groups:** duplicate-aware (identical feature rows share a group).

## Arms
All arms use the production preprocessing:
- StandardScaler on the 5 continuous inputs;
- passthrough for the 3 binary inputs;
- `OneHotEncoder(handle_unknown="ignore")` for cp, restecg, slope, ca and thal.

The model is LogisticRegression with lbfgs and `random_state=42`, wrapped in `CalibratedClassifierCV(method="sigmoid")`. Calibration splits are 5 duplicate-aware `StratifiedGroupKFold` folds of the outer-training partition.

| Arm | `class_weight` | Calibration |
|---|---|---|
| **A**: production (baseline) | `"balanced"` | `ensemble=True`: per-fold sigmoid; average of 5 calibrated members |
| **B**: no weighting | `None` | `ensemble=True` |
| **C**: pooled OOF | `"balanced"` | `ensemble=False`: one sigmoid fitted on pooled OOF decision values of the outer-training partition; base model refitted on the whole partition |
| **D**: both | `None` | `ensemble=False` |

**No outer-test labels in calibration.** Calibration is fitted only inside `CalibratedClassifierCV`, on the outer-training partition. Its OOF decision values come from the calibration splits of that partition, so outer-test labels are never used in tuning or calibration.

## Protocol
- **Outer loop:** `StratifiedGroupKFold(5, shuffle=True, random_state=1000+r)`, r = 0…9. The splits are identical for all arms.
- **Inner tuning (per arm):** C ∈ {0.01, 0.03, 0.1, 0.3, 1, 3}.
  - Each C is scored by inner `StratifiedGroupKFold(5, shuffle=True, random_state=2000+r)` OOF log loss of that arm's calibrated model.
  - The inner calibration CV is 3 duplicate-aware folds.
  - Ties go to the smaller C.
- **Final model per outer fold:** that arm's calibrated model with 5 calibration folds (seed `3000+r`).
- **Secondary analysis:** C fixed at 0.1 for all arms (the production value), on the same splits.

## Metrics (on outer-fold OOF predictions, per repeat)
- **Primary:**
  - calibration slope, the coefficient of an unpenalized logistic regression of y on logit(p), using `C=np.inf` (the replacement for the deprecated `penalty=None`), reported as |slope − 1|;
  - log loss.
- **Guardrail:** ROC-AUC.
- **Also reported:**
  - Brier score;
  - calibration intercept, the intercept `a` maximising the likelihood of `sigmoid(a + logit p)` (slope fixed at 1, estimated by Newton–Raphson);
  - calibration-in-the-large (mean y − mean p);
  - ECE (10 equal-width bins);
  - PR-AUC.

## Uncertainty
- **Repeat level:** per-repeat paired differences (arm − A), giving the mean, the 2.5/97.5 percentiles, and the count of repeats favouring each arm.
- **Paired group bootstrap:** 2,000 resamples of duplicate groups (seed 42).
  - In each resample, every metric is computed **per repeat** on the resampled patients and then averaged over the 10 repeats; it is not computed on averaged probabilities. This avoids the slope inflation that comes from averaging predictions across repeats.
  - The output is 95% percentile CIs for Δ = arm − A.
  - Bonferroni-adjusted intervals (98.33%, for three comparisons) are also reported as a sensitivity analysis.

## Pre-registered decision rule (primary analysis, each of arms B, C and D versus A)
An arm **improves calibration** only if all three conditions hold:
1. **Guardrail:** the 95% CI lower bound of ΔROC-AUC ≥ −0.01.
2. **At least one primary endpoint improves:** the 95% CI upper bound of Δ|slope − 1| < 0, **or** the 95% CI upper bound of Δlog loss < 0.
3. **Neither primary endpoint worsens:** the point estimates of both Δ|slope − 1| and Δlog loss are ≤ 0.

If more than one arm qualifies, the preferred arm is the one with the lowest mean log loss. Arm D (both changes) is preferred over a single-change arm only if it also qualifies. Results that hold at 95% but not under the Bonferroni intervals are labelled "not robust to multiplicity". The secondary fixed-C analysis is descriptive and does not change the verdict.

## Reproducibility
- All seeds are fixed.
- Two full runs must produce identical result content, excluding runtime.
- The only output is `experiments/results/h2_calibration_recipe.json`.
