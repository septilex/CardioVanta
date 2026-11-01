# R4 Research Report: Count Encoding of `ca` versus the Production One-Hot Recipe

| Field | Value |
|---|---|
| Status | Research only. Production model, artifacts, registry, contract, API and frontend unchanged |
| Date | 2026-10-31 |
| Pre-registered design | `openspec/changes/r4-ca-count-encoding/design.md` (SHA-256 `c2700c19…4489d`, fixed before execution, recorded in the results) |
| Implementation | `experiments/r4_ca_count_encoding.py` |
| Results | `experiments/results/r4_ca_count_encoding.json` |
| Tests | `tests/test_r4_ca_count_encoding.py` (18 synthetic tests) |
| **Verdict** | **H1 not supported.** The candidate is not an improvement; production encoding retained |

> CardioVanta is a research application and is not clinically validated. Nothing in this report is clinical evidence.

## Contents
1. [Research question](#1-research-question)
2. [Why this experiment](#2-why-this-experiment-and-not-another)
3. [Data and leakage controls](#3-data-and-leakage-controls)
4. [Method](#4-method)
5. [Results](#5-results)
6. [Interpretation](#6-interpretation)
7. [Reproducibility and isolation](#7-reproducibility-and-isolation)
8. [Limitations](#8-limitations)
9. [Recommended next hypothesis](#9-recommended-next-hypothesis)

## 1. Research question

**H1:** In the production recipe (sigmoid-calibrated, class-balanced L2 logistic regression), replace the five one-hot columns of `ca` (codes 0–4) with:
- a fold-locally standardized vessel **count** (codes 0–3);
- an indicator for the codebook-undefined code 4.

Does this improve calibration and prediction stability without a meaningful loss of discrimination?

### Rationale
- The UCI codebook defines `ca` as a count, 0–3. The R1 contract records that meaning at verification level `codebook_and_project_contract`. Code 4 is `undefined_in_codebook`; it gets its own indicator, so no meaning is assumed for it.
- On 242 rows, five dummies are thinly supported. Development counts by code are 0: 138, 1: 55, 2: 27, 3: 17, 4: 5.
- The encoding change is internal to the pipeline. The 13 inputs, accepted codes and outcome are unchanged, so a positive result could have been adopted by a future registered model without a contract or API change.

## 2. Why this experiment and not another

Coverage of earlier phases, from source and results inspection:

| Already tested | Where |
|---|---|
| Algorithm families: LR, KNN, SVM, RF, gradient boosting, XGBoost, LightGBM, CatBoost, TabICL | Phase 2B, Phase 13 |
| Calibration method: none / sigmoid / isotonic / temperature | Phase 3 |
| Thresholds, perturbation and resampling robustness, subgroups | Phase 4A/4B, nested threshold optimisation |
| Interaction (age × thalach) and quadratic oldpeak | Phase 16 |
| Clinical domain features, B-splines, elastic-net, soft-voting ensemble | "90%" study (`experiments/next_research_phase_90pct.py`) |
| Shrinkage LDA | `experiments/nested_lda_evaluation.py` |
| Reduced 9/10-feature sets across cohorts (excluding `ca`) | Phase 17 |

No phase tested an ordinal or count encoding of any input; a source search finds no ordinal encoders. The earlier work also targeted accuracy, whereas the R4 objective is calibration and robustness.

## 3. Data and leakage controls

| Control | Implementation |
|---|---|
| Development rows only | The loader parses only the header and the 242 lines listed in `dev_indices.json`. Lines for other indices are skipped before tokenisation, so the 61 locked rows are never parsed. Verified by a synthetic test in which "locked" lines are deliberately unparseable |
| Provenance | SHA-256 of `heart.csv` and `dev_indices.json` must equal the values in production provenance metadata, or the run aborts |
| Target orientation | `disease = 1 − target` (Phase 17 finding, R0.3 orientation). Prevalence 0.455 |
| Duplicates | Identical feature rows share a group (241 groups for 242 rows). Every split is `StratifiedGroupKFold` |
| Fold-local fitting | Scalers, encoders, C selection and sigmoid calibration are all fitted on training folds only |
| External cohorts | Not used |

## 4. Method

### Arms (identical except for `ca`)

| | Baseline (production recipe) | Candidate |
|---|---|---|
| Continuous (5) | StandardScaler | StandardScaler |
| Binary (3) | passthrough | passthrough |
| cp, restecg, slope, thal | one-hot | one-hot |
| `ca` | one-hot, 5 columns | `ca_count` (standardized) + `ca_code4`, 2 columns |
| Model | LR, `class_weight="balanced"`, lbfgs | same |
| Calibration | `CalibratedClassifierCV(sigmoid)`, 5 duplicate-aware folds | same |

### Analyses
- **Primary, repeated nested CV:** 10 repeats × 5 outer folds.
  - Inner 5-fold selection of C ∈ {0.01, 0.03, 0.1, 0.3, 1, 3} by out-of-fold (OOF) log loss of a sigmoid-calibrated model, with 3-fold inner calibration.
  - The final model per outer fold is calibrated with 5 duplicate-aware folds.
  - Both arms use identical outer, inner and calibration splits.
- **Secondary:** the same outer splits with C fixed at 0.1 (the production value), which isolates the encoding effect.
- **Metrics:** ROC-AUC, PR-AUC, Brier score, log loss, ECE (10 bins), calibration slope, calibration-in-the-large, and per-patient prediction SD across repeats (stability).
- **Uncertainty:** the spread across repeats, plus a paired bootstrap over duplicate groups (2,000 resamples) of repeat-averaged OOF probabilities.
- **Pre-registered rule:** H1 is supported only if the lower bound of the ΔAUC 95% CI is ≥ −0.01 **and** the upper bound of the Δlog-loss or ΔBrier CI is < 0.

## 5. Results

### 5.1 Primary analysis (nested, tuned C): mean over 10 repeats [2.5th–97.5th percentile]

| Metric | Baseline (one-hot `ca`) | Candidate (count `ca`) |
|---|---|---|
| ROC-AUC ↑ | **0.9128** [0.9050–0.9164] | 0.9101 [0.9048–0.9136] |
| PR-AUC ↑ | **0.9041** [0.8946–0.9093] | 0.9018 [0.8958–0.9056] |
| Brier ↓ | **0.1169** [0.1145–0.1227] | 0.1179 [0.1165–0.1216] |
| Log loss ↓ | **0.3780** [0.3738–0.3908] | 0.3813 [0.3781–0.3891] |
| ECE (10 bins) ↓ | 0.0631 [0.0449–0.0888] | **0.0613** [0.0461–0.0760] |
| Calibration slope (ideal 1) | 1.287 [1.190–1.356] | 1.278 [1.210–1.332] |
| Calibration-in-the-large (ideal 0) | +0.0014 | +0.0005 |
| Prediction stability (mean SD across repeats) ↓ | 0.0301 | **0.0269** |
| Selected C (count of 50 folds) | 0.1: 17, 0.3: 33 | 0.1: 35, 0.3: 15 |

### 5.2 Paired differences (candidate − baseline), primary analysis

| Metric | Per-repeat mean [2.5–97.5%] | Repeats favouring candidate | Paired group bootstrap 95% CI |
|---|---|---|---|
| ΔROC-AUC | −0.0027 [−0.0054, −0.0001] | 1 / 10 | −0.0030 [**−0.0137**, +0.0060] |
| ΔPR-AUC | −0.0023 [−0.0081, +0.0020] | 3 / 10 | n/a |
| ΔBrier | +0.0009 [−0.0011, +0.0022] | 1 / 10 | +0.0012 [−0.0042, +0.0075] |
| Δlog loss | +0.0033 [−0.0018, +0.0064] | 1 / 10 | +0.0038 [−0.0107, +0.0204] |
| ΔECE | −0.0018 [−0.0194, +0.0121] | 5 / 10 | −0.0099 [−0.0450, +0.0240] |

The mean absolute per-patient probability difference between arms is 0.031.

### 5.3 Secondary analysis (fixed C = 0.1)

| Metric | Baseline | Candidate | Paired bootstrap Δ 95% CI |
|---|---|---|---|
| ROC-AUC | 0.9124 | 0.9109 | −0.0018 [−0.0120, +0.0067] |
| Brier | 0.1169 | 0.1174 | +0.0005 [−0.0049, +0.0065] |
| Log loss | 0.3775 | 0.3800 | +0.0025 [−0.0115, +0.0185] |
| Prediction stability (mean SD) | 0.0241 | 0.0233 | n/a |

### 5.4 Verdict under the pre-registered rule

| Criterion | Primary | Secondary |
|---|---|---|
| ΔAUC CI lower bound ≥ −0.01 | ✗ (−0.0137) | ✗ (−0.0120) |
| Δlog loss or ΔBrier CI upper bound < 0 | ✗ | ✗ |
| **H1 supported** | **No** | **No** |

## 6. Interpretation

- **No improvement.** Every point estimate for discrimination, log loss and Brier score favours the production one-hot encoding, and in 9 of 10 repeats the candidate had lower AUC and higher log loss. The differences are small (|ΔAUC| ≈ 0.003) and their intervals span zero, so the honest reading is "no evidence of benefit, slight evidence of harm". It is not "proven harmful".
- **Linearity is not supported.** The count encoding imposes a linear log-odds trend across vessel counts. The one-hot model's freedom to estimate a non-linear pattern appears to carry real signal even at n = 242. The data do not support replacing it.
- **Stability gain is confounded.** The candidate's lower prediction SD in the primary analysis (0.027 vs 0.030) coincides with it selecting the stronger regularisation (C = 0.1) more often. At fixed C, stability is essentially identical (0.0233 vs 0.0241). So the gain is attributable to tuning differences, not to the encoding.
- **ECE does not change the verdict.** It is noisy at this sample size: per-repeat ranges are about ±0.02, and the candidate is better in only 5 of 10 repeats.
- **Production encoding retained.** No change to the production recipe is warranted.

### Incidental, consistent finding: under-confident probabilities
- In **both** arms, and in both analyses, the OOF calibration slope is about 1.28, and the per-repeat range (≈1.19–1.36) excludes 1.
- A slope above 1 means the calibrated probabilities are too compressed toward the middle: more extreme predictions would be better calibrated.
- This is a property of the production recipe (class-balanced weighting, L2 at C ≈ 0.1–0.3, then sigmoid calibration on small folds), not of the `ca` encoding.
- It was not part of H1. It is reported here as a hypothesis-generating observation, not a confirmed finding.

## 7. Reproducibility and isolation

| Check | Result |
|---|---|
| Two independent full runs | Result content identical, excluding runtime (canonical-JSON SHA-256 `495c4496…`) |
| Seeds | Outer `1000+r`, inner `2000+r`, calibration `3000+r`, bootstrap 42, LR `random_state=42` |
| Rows used | 242 development rows. Locked lines parsed: 0 (by construction; loader behaviour verified by synthetic test) |
| Production artifacts | `scripts/verify_artifact_integrity.py` passes after both runs; registry manifest, contract, datasets and Phase 17 outputs unchanged (SHA-256) |
| Synthetic tests | 18 / 18 pass (`tests/test_r4_ca_count_encoding.py`) |
| Runtime | About 6 minutes per run (Python 3.12.16, scikit-learn 1.9.1) |

To reproduce:

```bash
python experiments/r4_ca_count_encoding.py
python -m pytest tests/test_r4_ca_count_encoding.py
```

## 8. Limitations

- **Small sample.** 242 rows, with rare `ca` codes (code 3: 17, code 4: 5). The study is powered only to detect large effects; the non-inferiority interval width is about ±0.01 AUC.
- **Single centre.** One historical development cohort (Cleveland). Results may not transfer, and external cohorts were deliberately excluded from selection.
- **Bootstrap scope.** Intervals are computed on repeat-averaged OOF probabilities. They capture patient-sampling variability but not the full model-refitting variability; per-repeat spreads are reported alongside for that reason.
- **Constraints on the candidate.** The count encoding assumes a linear trend over codes 0–3. Other ordinal forms, such as monotone splines or thresholded "≥ 1 vessel" indicators, were not tested and would need their own pre-registration.
- **Code 4 handling.** Code 4 was modelled only through an indicator with 5 occurrences, so its coefficient is unstable in both arms.
- **Deprecation warning.** The calibration-slope helper uses `penalty=None`. That is a deprecation warning in scikit-learn 1.9, and the equivalent `C=np.inf` should be used before any upgrade past 1.9. It does not affect results under the pinned 1.9.1.
- **Not independent confirmation.** The 61 locked rows were not used, and they could not give independent confirmation anyway, because earlier phases have repeatedly evaluated them.

## 9. Recommended next hypothesis

**H2 (calibration of the production recipe):** the systematic under-confidence (slope ≈ 1.28) arises from combining `class_weight="balanced"` with strong L2 regularisation before sigmoid calibration fitted on small folds.

Pre-register a comparison of the production recipe against:
- (a) `class_weight=None`;
- (b) calibration fitted once on pooled OOF decision values (`ensemble=False`);
- (c) both together.

Use the same repeated nested CV. The primary endpoint is the calibration slope's distance from 1 and log loss, with AUC non-inferiority as a guardrail. None of these variants appears in Phases 2–17; class weighting was tuned only for AUC in Phase 2B. Any of them could be adopted without changing the 13-feature contract, the outcome orientation or the API.
