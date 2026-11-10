# Design: H2.1 — Calibration Confirmation (pre-registered before execution)

## Data
- **Rows:** the 242 Cleveland development rows only, through the R4 loader (`experiments/r4_ca_count_encoding.py`).
  - It parses only header and development-row lines; locked lines are never parsed.
  - It verifies the SHA-256 of `heart.csv` and `dev_indices.json` against production provenance.
- **Target:** `disease = 1 − target`.
- **Groups:** duplicate-aware (identical feature rows).

## Arms
Both arms use the production preprocessing (StandardScaler / passthrough / OneHotEncoder(ignore)), L2 LogisticRegression with lbfgs, and `class_weight="balanced"`.

| Arm | Calibration |
|---|---|
| **A**: production | `CalibratedClassifierCV(sigmoid, ensemble=True)` |
| **C**: pooled OOF | `CalibratedClassifierCV(sigmoid, ensemble=False)` |

H2 showed that removing class weighting has no effect (arms B and D), so those arms are not repeated.

## Protocol
New seeds, all disjoint from H2's 1000/2000/3000 offsets:
- **Outer loop:** `StratifiedGroupKFold(5, shuffle=True, random_state=5000+r)`, r = 0…19 (**20 repeats**). The splits are identical for both arms.
- **Inner tuning (per arm):** C ∈ {0.01, 0.03, 0.1, 0.3, 1, 3}.
  - Scored by the OOF log loss of the arm's calibrated model, on inner `StratifiedGroupKFold(5, shuffle=True, random_state=6000+r)` with 3 inner calibration folds.
  - Ties go to the smaller C.
- **Final model per outer fold:** fitted with 5 calibration folds (`random_state=7000+r`).
- **No outer-test labels in calibration.** Calibration is fitted only inside `CalibratedClassifierCV` on the outer-training partition, using OOF decision values from that partition's calibration splits.

## Endpoints
- **Primary:** **Δslope = slope(C) − slope(A)** (signed).
  - The slope is the coefficient of an unpenalised logistic regression of y on logit(p) (`C=np.inf`), computed on outer-fold OOF predictions per repeat.
  - **Expected direction: Δslope < 0** (C less under-confident).
- **Secondary:** Δlog loss, ΔBrier, ΔECE (10 bins). Expected direction for each: < 0.
- **Guardrail:** ΔROC-AUC.
- **Descriptive:** calibration intercept, calibration-in-the-large, PR-AUC and prediction stability.

## Inference
- **Paired group bootstrap.** 2,000 resamples of duplicate groups, `seed=4242`. In each resample, every metric is computed per repeat on the resampled patients and averaged over the 20 repeats; probabilities are not averaged.
- **Repeat level.** Per-repeat paired differences, with the count of repeats in the expected direction.
- **Multiplicity.**
  - The single primary endpoint is tested at two-sided α = 0.05, using the 95% percentile CI.
  - The three secondary endpoints use Bonferroni-adjusted two-sided 98.33% CIs. They are supportive only and are not part of the acceptance criteria.
  - The guardrail uses the 95% CI.

## Pre-registered acceptance criteria
The H2 finding is **confirmed** only if **all** of the following hold:
1. The upper bound of the primary Δslope 95% CI is < 0.
2. The lower bound of the ΔROC-AUC 95% CI is ≥ −0.01 (guardrail).
3. Arm C's mean calibration slope across repeats lies within [0.90, 1.10] (corrected, not over-corrected).
4. Direction consistency: Δslope < 0 in at least 16 of the 20 repeats (80%).

If any criterion fails, the finding is **not confirmed**. Secondary endpoints are reported, with their adjusted intervals, as supportive or non-supportive evidence and do not change the verdict.

## External cohorts
Excluded, as pre-registered in `proposal.md`, because their existing feature mappings are incompatible (unverified `slope`/`thal` code mappings and extensive missingness). No external data is parsed by this experiment.

## Reproducibility
- All seeds are fixed.
- Two independent full runs must produce identical result content, excluding runtime.
- The only output is `experiments/results/h2_1_calibration_confirmation.json`.
