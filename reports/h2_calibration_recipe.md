# H2 Research Report: Calibration of the Production Training Recipe

| Field | Value |
|---|---|
| Status | Research only. Production model, artifacts, registry, contract, API and frontend unchanged |
| Date | 2026-10-31 |
| Pre-registered design | `openspec/changes/h2-calibration-recipe/design.md` (SHA-256 `ad120765…a96a3d7`, fixed at 12:40:00Z before any code or results; recorded in the results) |
| Implementation | `experiments/h2_calibration_recipe.py` |
| Results | `experiments/results/h2_calibration_recipe.json` |
| Tests | `tests/test_h2_calibration_recipe.py` (17 synthetic tests) |
| **Pre-registered verdict** | **No arm met the decision rule. H2 is not supported as stated.** |
| **Key descriptive finding** | **Pooled OOF calibration corrected the under-confidence (slope 1.29 → 1.02) in 10/10 repeats; class weighting had no effect** |

> CardioVanta is a research application and is not clinically validated. Nothing here is clinical evidence.

## Contents
1. [Question and arms](#1-question-and-arms)
2. [Data and leakage controls](#2-data-and-leakage-controls)
3. [Method](#3-method)
4. [Results](#4-results)
5. [Verdict under the pre-registered rule](#5-verdict-under-the-pre-registered-rule)
6. [Interpretation](#6-interpretation)
7. [Reproducibility and isolation](#7-reproducibility-and-isolation)
8. [Limitations](#8-limitations)
9. [Recommended next step](#9-recommended-next-step)

## 1. Question and arms

R4 found that the production recipe produces **under-confident** probabilities: the OOF calibration slope was about 1.28, and every repeat fell above 1. H2 tests whether either of two recipe components causes this:
- class-balanced weighting;
- per-fold ("ensemble") sigmoid calibration.

| Arm | `class_weight` | Calibration (`CalibratedClassifierCV`, sigmoid) |
|---|---|---|
| **A**: production (baseline) | `"balanced"` | `ensemble=True`: 5 calibrated members averaged; each sigmoid fitted on one calibration fold (about 38 rows) |
| **B**: no weighting | `None` | `ensemble=True` |
| **C**: pooled OOF | `"balanced"` | `ensemble=False`: one sigmoid fitted on the pooled OOF decision values of the whole outer-training partition, applied to one model refitted on that partition |
| **D**: both | `None` | `ensemble=False` |

Preprocessing is identical to production: StandardScaler for continuous inputs, passthrough for binary, one-hot encoding for categoricals. The model is L2 logistic regression.

## 2. Data and leakage controls

| Control | Implementation |
|---|---|
| Development rows only | The R4 loader is reused. It parses only the header and the 242 development-row lines, so locked lines are never parsed. It verifies the SHA-256 of `heart.csv` and `dev_indices.json` against production provenance |
| Target | `disease = 1 − target`. Prevalence 0.455 |
| Duplicates | Identical feature rows share a group (241 groups). All splits are `StratifiedGroupKFold` |
| Identical splits | One set of outer splits per repeat, shared by all four arms and both analyses. Their SHA-256 is recorded in the results |
| Fold-local fitting | Preprocessing, C tuning and calibration are fitted only on outer-training data. Calibration uses OOF decision values from calibration splits *within* the outer-training partition |
| Outer-test labels | Never used. A synthetic test flips outer-test labels and confirms that predictions and the selected C are unchanged for every arm |

## 3. Method

- **Repeated nested CV.** 10 repeats × 5 outer folds (`random_state=1000+r`).
- **Inner tuning per arm.** C is selected from {0.01, 0.03, 0.1, 0.3, 1, 3}, scored by 5-fold OOF log loss of that arm's own calibrated model (3 inner calibration folds). Ties go to the smaller C.
- **Final model per outer fold.** The arm's calibrated model is refitted with 5 calibration folds.
- **Secondary analysis.** C is fixed at 0.1 (the production value) on the same splits.
- **Primary endpoints.**
  - Calibration slope, the coefficient of an unpenalised logistic regression of y on logit(p). It is fitted with `C=np.inf`, which **resolves the scikit-learn 1.9 `penalty=None` deprecation** noted in R4; pinned dependencies are unchanged. It is evaluated as |slope − 1|.
  - Log loss.
- **Guardrail.** ROC-AUC.
- **Also reported.**
  - Brier score.
  - Calibration intercept: `a` in `sigmoid(a + logit p)` with the slope fixed at 1, estimated by Newton–Raphson.
  - Calibration-in-the-large.
  - ECE with 10 bins.
  - PR-AUC.
  - Prediction stability.
- **Uncertainty.** Two levels are reported:
  - per-repeat paired differences;
  - a paired bootstrap over duplicate groups (2,000 resamples). Each metric is computed per repeat on the resampled patients and then averaged over repeats; probabilities are not averaged. 95% and Bonferroni 98.33% intervals are given.

## 4. Results

### 4.1 Primary analysis (nested, tuned C): mean over repeats [2.5th–97.5th percentile]

| Metric | A: production | B: no weighting | C: pooled OOF | D: both |
|---|---|---|---|---|
| **Calibration slope** (ideal 1) | 1.287 [1.190, 1.356] | 1.287 [1.190, 1.356] | **1.024** [0.965, 1.083] | **1.025** [0.966, 1.083] |
| \|slope − 1\| ↓ | 0.287 | 0.287 | **0.038** | **0.038** |
| **Log loss** ↓ | 0.3780 [0.374, 0.391] | 0.3779 | **0.3706** [0.365, 0.384] | **0.3703** [0.365, 0.384] |
| **ROC-AUC** (guardrail) ↑ | 0.9128 [0.905, 0.916] | 0.9126 | 0.9122 [0.906, 0.916] | 0.9123 |
| Brier ↓ | 0.1169 | 0.1168 | 0.1153 | **0.1151** |
| ECE (10 bins) ↓ | 0.0631 | 0.0638 | 0.0425 | 0.0430 |
| Calibration intercept (ideal 0) | +0.010 | +0.010 | +0.002 | +0.006 |
| Calibration-in-the-large | +0.0014 | +0.0013 | +0.0003 | +0.0007 |
| PR-AUC ↑ | 0.9041 | 0.9040 | 0.9023 | 0.9026 |
| Prediction stability (mean SD) ↓ | 0.0301 | 0.0304 | 0.0296 | 0.0296 |
| Selected C (count of 50 folds) | 0.1: 17, 0.3: 33 | 0.1: 16, 0.3: 33, 1: 1 | 0.1: 38, 0.3: 12 | 0.1: 37, 0.3: 13 |

### 4.2 Repeat-level paired differences versus A (primary)

| Arm | ΔROC-AUC | Δlog loss | Δ\|slope − 1\| | ΔBrier | ΔECE |
|---|---|---|---|---|---|
| B | −0.0001 (4/10) | −0.0001 (9/10) | +0.0000 (3/10) | −0.0001 (9/10) | +0.0008 (4/10) |
| C | −0.0006 (3/10) | **−0.0074 (10/10)** | **−0.249 (10/10)** | −0.0017 (10/10) | −0.0205 (9/10) |
| D | −0.0005 (5/10) | **−0.0076 (10/10)** | **−0.249 (10/10)** | −0.0019 (10/10) | −0.0200 (9/10) |

Figures in parentheses are the number of repeats (of 10) in which the arm was better than A.

### 4.3 Paired group bootstrap, primary analysis (Δ = arm − A): mean [95% CI] / [Bonferroni 98.33% CI]

| Metric | B: no weighting | C: pooled OOF | D: both |
|---|---|---|---|
| ΔROC-AUC | −0.0001 [−0.0008, +0.0005] | −0.0006 [−0.0022, +0.0009] | −0.0005 [−0.0022, +0.0012] |
| Δlog loss | −0.0001 [−0.0008, +0.0007] | −0.0075 [−0.0206, **+0.0069**] | −0.0077 [−0.0210, **+0.0067**] |
| Δ\|slope − 1\| | +0.0001 [−0.0045, +0.0049] | −0.204 [−0.335, **+0.117**] | −0.204 [−0.332, **+0.117**] |
| Δslope (signed, descriptive) | +0.0001 [−0.0045, +0.0049] | **−0.268 [−0.335, −0.217]** / [−0.354, −0.208] | **−0.267 [−0.332, −0.216]** / [−0.349, −0.208] |
| ΔBrier | −0.0001 [−0.0004, +0.0002] | −0.0017 [−0.0048, +0.0015] | −0.0019 [−0.0050, +0.0014] |
| ΔECE | +0.0002 [−0.0044, +0.0047] | −0.0129 [−0.0294, +0.0066] | −0.0128 [−0.0286, +0.0070] |
| Δcalibration intercept | −0.0003 [−0.0029, +0.0022] | −0.0075 [−0.074, +0.057] | −0.0043 [−0.071, +0.061] |

### 4.4 Secondary analysis (fixed C = 0.1), descriptive

| Metric | A | B | C | D |
|---|---|---|---|---|
| Calibration slope | 1.284 | 1.285 | **1.019** | **1.020** |
| Log loss | 0.3775 | 0.3773 | 0.3698 | **0.3696** |
| ROC-AUC | 0.9124 | 0.9125 | 0.9127 | 0.9128 |
| Brier | 0.1169 | 0.1168 | 0.1150 | **0.1149** |
| Δ\|slope − 1\| vs A, per repeat | n/a | +0.0004 (2/10) | −0.249 (10/10) | −0.249 (10/10) |
| Δlog loss vs A, per repeat | n/a | −0.0002 (9/10) | −0.0077 (10/10) | −0.0079 (10/10) |

The pattern is the same with C held fixed, so the effect does not come from different C selection.

## 5. Verdict under the pre-registered rule

The rule: ΔAUC 95% CI lower bound ≥ −0.01, **and** an upper 95% CI bound below 0 for Δ|slope − 1| or Δlog loss, **and** point estimates of both ≤ 0.

| Arm | AUC guardrail | A primary endpoint improved (CI upper < 0) | No primary endpoint worse (point estimates) | **Improves calibration** |
|---|---|---|---|---|
| B: no weighting | ✓ | ✗ | ✗ (Δ\|slope − 1\| = +0.0001) | **No** |
| C: pooled OOF | ✓ | ✗ (upper bounds +0.117 / +0.0069) | ✓ | **No** |
| D: both | ✓ | ✗ (upper bounds +0.117 / +0.0067) | ✓ | **No** |

**No arm qualifies. H2, as pre-registered, is not supported.**

## 6. Interpretation

The pre-registered verdict stands, and the following points do not change it. They do characterise a strong, specific signal that the rule did not capture.

1. **Ensemble calibration, not class weighting, drives the under-confidence.**
   - Arm B is practically indistinguishable from A on every metric (|Δ| ≤ 0.0008). After sigmoid calibration, `class_weight="balanced"` has no material effect at this prevalence (0.455).
   - Both pooled-calibration arms (C and D) move the slope to about 1.02 in **every one of the 10 repeats**. The signed slope difference has a 95% CI of [−0.335, −0.217], which excludes zero and also holds under the Bonferroni correction.
   - The likely mechanism: averaging five sigmoids, each fitted on about 38 rows and each applied to a model trained on only 80% of the partition, compresses predictions toward the centre.

2. **Why the pre-registered endpoint missed it.** The endpoint was |slope − 1|, a folded statistic. In bootstrap resamples where the baseline's slope happens to land near 1, the pooled arm's small deviation can exceed it. That pushes the upper CI bound above 0 (+0.117) even though the signed shift is consistent.

   Log loss improved in 10/10 repeats, by about 0.0075, but its patient-level bootstrap interval [−0.021, +0.007] still includes 0 at n = 242. The improvement is consistent but small relative to sampling uncertainty.

3. **Discrimination is unaffected.** All arms are within 0.0006 AUC of production, and every guardrail interval lies well inside −0.01. Recalibration changes the probability scale, not the ranking.

4. **Practical reading.**
   - The evidence favours pooled OOF calibration as a calibration fix for a future model version. It is directionally consistent, has a large effect on slope and no discrimination cost.
   - It is **not** confirmed under the pre-registered decision rule, and it must not be adopted on the basis of this study.
   - Removing class weighting is not supported.

## 7. Reproducibility and isolation

| Check | Result |
|---|---|
| Two full independent runs | Exit 0 both. Result content identical, excluding runtime (canonical-JSON SHA-256 `0c8b7588…`). Runtimes 1,032 s and 977 s |
| Warnings | 0 in both run logs. The slope estimator raises no deprecation warning (enforced by a synthetic test) |
| Seeds | Outer `1000+r`, inner `2000+r`, calibration `3000+r`, bootstrap 42, LR `random_state=42` |
| Rows used | 242 development rows. Locked lines parsed: 0 (by construction; loader behaviour verified by synthetic test) |
| Production | `scripts/verify_artifact_integrity.py` passes. Registry manifest, contract, datasets and Phase 17 outputs unchanged (SHA-256) |
| Tests | 17/17 synthetic H2 tests pass |
| Environment | Python 3.12.16, scikit-learn 1.9.1 (pinned) |

To reproduce:

```bash
python experiments/h2_calibration_recipe.py
python -m pytest tests/test_h2_calibration_recipe.py
```

## 8. Limitations

- **Small sample, single centre.** 242 rows from one historical cohort. Patient-level intervals are wide, which is why the consistent repeat-level log-loss gain is not statistically confirmed.
- **Folded endpoint.** |slope − 1| was a conservative and noisy choice under resampling. Its weakness is documented here rather than replaced after the fact.
- **Two levels of uncertainty.** Repeat-level consistency (10/10) and patient-level intervals answer different questions:
  - repeat-level consistency shows that the result is stable across data partitions;
  - patient-level intervals show how much the estimate could vary with a different sample of patients.
- **Calibration slope as an endpoint.** At this n the calibration slope is itself uncertain, and an OOF slope near 1 does not guarantee calibration in other populations or under dataset shift.
- **Scope.**
  - Only sigmoid calibration was studied. Isotonic and temperature scaling were compared in Phase 3, under a different protocol.
  - `ensemble=False` refits the base model on the full partition, so arms C and D differ from A both in how calibration is fitted and in which base model is calibrated. The two effects are not separated.
- **Multiplicity.** Three comparisons were made. Bonferroni intervals are reported, but no arm qualified even at 95%.
- **No independent confirmation.** The 61 locked rows were neither used nor usable for this purpose, because earlier phases have evaluated them repeatedly.

## 9. Recommended next step

A confirmatory study, pre-registered from the start, comparing **pooled OOF sigmoid calibration (arm C) with the production recipe**:
- **Primary endpoint:** the signed calibration slope (H0: Δslope = 0), with log loss as key secondary.
- **Inference:** a repeat-aware resampling scheme, plus additional repeats.
- **External check:** calibration on the Phase 17 external cohorts as a *pre-declared*, non-selection, transportability check, without tuning on them.

Only if confirmed would a new model version be trained and registered (for example `cardiovanta-lr13@1.1.0`, with a harmonised target, explicit `outcome_semantics` and a model card) through the R2 registry. The 13-feature contract, outcome orientation and API would stay unchanged.
