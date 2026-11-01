# R5 Research Report: Explanation Stability under One-Feature Perturbations

| Field | Value |
|---|---|
| Status | Research only. The production model was loaded read-only through the SHA-256-verified registry. No retraining or recalibration; no production change |
| Date | 2026-10-31 |
| Design | `openspec/changes/r5-explanation-stability/design.md` (SHA-256 `79ef1183…`, written before execution) |
| Implementation | `experiments/r5_explanation_stability.py` |
| Results | `experiments/results/r5_explanation_stability.json` |
| Tests | `tests/test_r5_explanation_stability.py` (8 synthetic tests) |
| Model | `cardiovanta-lr13@1.0.0` (outcome mapping `interim_legacy`) |
| Data | **Synthetic profiles only.** No `heart.csv`, no locked rows, no external cohorts |

> CardioVanta is a research application and is not clinically validated. Explanations describe the behaviour of a statistical model, not clinical causes. Unverified codes carry no clinical meaning here.

## Contents
1. [What was measured](#1-what-was-measured)
2. [Pre-stated expectations, all confirmed](#2-pre-stated-expectations-all-confirmed)
3. [Results: continuous perturbations](#3-results-continuous-perturbations)
4. [Results: categorical perturbations](#4-results-categorical-perturbations)
5. [Per-feature results](#5-per-feature-results)
6. [Findings](#6-findings)
7. [Reproducibility and integrity](#7-reproducibility-and-integrity)
8. [Limitations](#8-limitations)

## 1. What was measured

- **Profiles.** 100 deterministic synthetic profiles (seed 20261031):
  - continuous values uniform within the contract's development range;
  - binary and categorical values uniform over the accepted codes.
- **Continuous perturbations.** Each continuous feature was shifted by ±5% and ±10% of its development-range width. Shifts leaving the range were skipped rather than clipped (138 of 2,000).
- **Categorical perturbations.** Each binary or categorical feature was set to every other accepted code.
- **Total.** 3,562 single-feature perturbations: 1,862 continuous and 1,700 categorical.
- **Methods compared.** Both production explanation methods:
  - **linear**: contributions of the uncalibrated explanation model, intercept + Σ;
  - **SHAP-equivalent**: contributions relative to the frozen background means.

| Metric | Definition |
|---|---|
| \|Δp\| | Change in calibrated P(disease present) |
| ρ | Spearman correlation of \|contributions\| across the 13 features, before vs after |
| Top-3 / top-5 overlap | Share of the top-k features (by \|contribution\|) retained |
| Own sign flip | The perturbed feature's contribution changes sign. A change between 0 and non-zero counts as a flip |
| Direction agreement | The sign of the perturbed feature's Δcontribution equals the sign of Δp |
| Additivity error | \|base + Σ contributions − log-odds\| |

## 2. Pre-stated expectations, all confirmed

| Expectation (design.md) | Observed |
|---|---|
| **Locality**: perturbing feature j changes only j's contribution | Maximum change in any other feature's contribution = **0.0**; other-feature sign flips = **0** |
| **Additivity** < 1e-9 | Maximum error **1.8e-15** |
| **Shared deltas**: both methods move by the same amount | Maximum \|Δ linear − Δ SHAP\| = **2.2e-16** |

**Locality is structural.** It follows from the explanation model being linear and additive per feature, so any instability can only come from the perturbed feature itself. This is a property of the method, not evidence of robustness in a clinical sense.

## 3. Results: continuous perturbations

Means, with the minimum ρ in parentheses.

| Shift | n | \|Δp\| mean / p95 / max | Linear ρ | Linear top-3 | Linear own flip | SHAP ρ | SHAP top-3 | SHAP own flip | Direction agreement |
|---|---|---|---|---|---|---|---|---|---|
| −10% | 452 | 0.021 / 0.058 / 0.066 | 0.987 (0.85) | 0.965 | 10.4% | 0.984 (0.85) | 0.968 | 10.4% | 100% |
| −5% | 480 | 0.010 / 0.029 / 0.034 | 0.995 (0.88) | 0.986 | 5.0% | 0.994 (0.92) | 0.982 | 3.5% | 100% |
| +5% | 477 | 0.010 / 0.029 / 0.034 | 0.995 (0.88) | 0.975 | 4.6% | 0.994 (0.88) | 0.983 | 6.1% | 100% |
| +10% | 453 | 0.021 / 0.059 / 0.068 | 0.988 (0.85) | 0.959 | 9.1% | 0.986 (0.85) | 0.954 | 9.7% | 100% |
| **All continuous** | **1,862** | **0.015 / 0.051 / 0.068** | **0.992** | **0.972** | **7.2%** | **0.989** | **0.972** | **7.4%** | **100%** |

- Responses scale roughly linearly with shift size: a 10% shift gives about twice the |Δp| and flip rate of a 5% shift.
- Sign flips occur only when a value crosses the feature's reference point: the scaler mean for the linear method, the background mean for SHAP-equivalent.

## 4. Results: categorical perturbations

Grouped by the contract verification level of the codes involved. Codes are identified by number only.

| Group | n | \|Δp\| mean / p95 / max | Linear ρ (min) | Linear top-3 | SHAP ρ (min) | SHAP top-3 | SHAP top-5 | Linear own flip | SHAP own flip | Direction agreement |
|---|---|---|---|---|---|---|---|---|---|---|
| Both codes verified (`verified_patient_matched` / `codebook_and_project_contract`) | 1,046 | 0.052 / 0.176 / 0.286 | 0.930 (0.57) | 0.904 | **0.991 (0.88)** | 0.941 | 0.978 | 66.7% | 66.7% | 100% |
| Involves an `unverified` code (slope; thal 1–3) | 500 | 0.066 / 0.159 / **0.301** | 0.916 (0.70) | 0.887 | 0.905 (0.64) | 0.899 | 0.910 | 64.8% | 53.6% | 100% |
| Involves an `undefined_in_codebook` code (ca = 4, thal = 0) | 306 | 0.048 / 0.135 / 0.154 | 0.927 (0.75) | 0.878 | 0.899 (0.64) | 0.857 | 0.847 | 70.3% | 29.7% | 100% |
| **All categorical** | **1,700** | **0.055 / 0.167 / 0.301** | **0.928** | **0.900** | **0.962** | **0.923** | **0.944** | **66.6%** | **59.4%** | **100%** |

The groups overlap: a `thal` 0 → 3 change counts in both the unverified and undefined groups.

## 5. Per-feature results

Means over all perturbations of that feature.

| Feature | Kind | n | \|Δp\| mean / max | Linear ρ | SHAP ρ | Linear top-3 | SHAP top-3 | SHAP own flip |
|---|---|---|---|---|---|---|---|---|
| age | continuous | 383 | 0.001 / 0.004 | 0.999 | 0.998 | 1.000 | 1.000 | 6.5% |
| trestbps | continuous | 366 | 0.007 / 0.018 | 0.995 | 0.993 | 0.997 | 0.995 | 6.6% |
| chol | continuous | 379 | 0.025 / 0.068 | 0.985 | 0.984 | 0.953 | 0.951 | 8.2% |
| thalach | continuous | 367 | 0.020 / 0.054 | 0.989 | 0.987 | 0.946 | 0.950 | 7.9% |
| oldpeak | continuous | 367 | 0.023 / 0.062 | 0.990 | 0.985 | 0.961 | 0.963 | 7.6% |
| sex | binary | 100 | 0.059 / 0.114 | **0.760** | 0.970 | 0.857 | 0.990 | 100% |
| fbs | binary | 100 | 0.003 / 0.006 | 0.988 | 0.997 | 1.000 | 1.000 | 100% |
| exang | binary | 100 | 0.064 / 0.123 | **0.787** | 0.990 | 0.903 | 1.000 | 100% |
| cp | categorical (verified) | 300 | 0.069 / 0.286 | 0.953 | 0.990 | 0.852 | 0.858 | 45.3% |
| restecg | categorical (codebook) | 200 | 0.024 / 0.075 | 0.986 | 0.995 | 1.000 | 1.000 | 65.0% |
| slope | categorical (**unverified**) | 200 | 0.049 / 0.140 | 0.933 | 0.959 | 0.990 | 1.000 | 62.0% |
| ca | categorical (0–3 codebook; **4 undefined**) | 400 | 0.058 / 0.220 | 0.958 | 0.976 | 0.889 | 0.908 | 43.8% |
| thal | categorical (**unverified / 0 undefined**) | 300 | **0.078 / 0.301** | 0.904 | **0.870** | **0.818** | 0.832 | 48.0% |

## 6. Findings

1. **Explanation direction always matches the reported probability.** In all 3,562 perturbations, the perturbed feature's contribution moved in the same direction as the calibrated P(disease). This holds even though the explanation model is not the calibrated ensemble. Within this synthetic, in-range setting, users are never shown a factor "pushing toward CAD present" while the displayed probability falls.
2. **Continuous explanations are stable.** For shifts of 5–10% of the development range:
   - ranking correlation is about 0.99 and top-3 overlap about 0.97;
   - |Δp| averages 0.015 (maximum 0.068);
   - sign flips (7%) happen only around a feature's reference point, where its contribution is near zero.
3. **Categorical changes move the explanation more, as expected for discrete jumps.** On average |Δp| is 3.6× the continuous figure and the maximum is 0.30. Rankings are less stable (ρ about 0.93–0.96).
4. **SHAP-equivalent rankings are more stable than linear ones for binary and categorical changes.**
   - For `sex` and `exang`, linear ρ is about 0.76–0.79, versus about 0.97–0.99 for SHAP-equivalent.
   - The reason is structural. The linear method assigns exactly 0 to a binary feature at code 0 and the full coefficient at code 1, so toggling it jumps the feature from bottom to near-top rank. SHAP-equivalent centres on the background mean, so both states contribute non-zero values of opposite sign.
   - The 100% "flip" rate for binary features therefore means a 0 ↔ non-zero transition for the linear method, but a genuine sign reversal for SHAP-equivalent.
5. **Explanation and prediction instability concentrates on codes without established meaning.**
   - Perturbations of `thal`, whose codes 1–3 are `unverified` and code 0 is `undefined_in_codebook`, produce the largest probability changes (maximum 0.30) and the least stable SHAP-equivalent rankings (ρ 0.870, minimum 0.64; top-3 overlap 0.83).
   - Changes involving `ca = 4` (undefined) move probability by up to 0.15.
   - The model therefore relies materially on inputs whose code semantics the project cannot currently verify. That is a robustness and transparency concern, not a clinical finding, and it reinforces the R1 recommendation to resolve the `slope`/`thal` mappings before any model v2.

## 7. Reproducibility and integrity

| Check | Result |
|---|---|
| Two independent runs | Exit 0 both. Identical result content excluding runtime (canonical-JSON SHA-256 `94c30837…`) |
| Warnings | 0 in both runs (run with `-W error::FutureWarning`) |
| Profiles | Deterministic: `profiles_sha256` is recorded in the results |
| Model loading | Through `cardiovanta_ml.load_model`; all SHA-256 checks pass before deserialisation |
| Artifact integrity | `scripts/verify_artifact_integrity.py` passes. Registry checksum manifest and contract unchanged. No changes under `artifacts/`, `cardiovanta_ml/`, `backend/`, `src/`, `api/` or `vercel.json` |
| Tests | 8/8 synthetic tests pass, including locality, additivity, determinism, constraint adherence and the no-dataset check |

To reproduce:

```bash
python experiments/r5_explanation_stability.py
python -m pytest tests/test_r5_explanation_stability.py
```

## 8. Limitations

- **Synthetic, independent sampling.** Features were drawn independently and uniformly, so the profiles ignore real correlations and include combinations that are implausible or rare in practice. The results describe model behaviour over the input space, not over a patient population.
- **Not a robustness guarantee.** Perturbation sizes (±5/10% of the range) and "every other code" are design choices. Locality and shared deltas are guaranteed by the linear explanation structure, so they say nothing about non-linear models.
- **Explanations are of the explanation model.** They describe the uncalibrated explanation model, not the calibrated ensemble. Direction agreement was 100% here, but the attributions still do not decompose the displayed probability (R0.3).
- **Coarse flip definition.** Counting 0 ↔ non-zero as a flip makes the linear method's binary flip rate 100% by construction.
- **No clinical meaning.** No clinical meaning is attached to any code, especially the `unverified` (slope, thal 1–3) and `undefined_in_codebook` (ca = 4, thal = 0) codes. Their effects are reported only as model behaviour.
- **Interim legacy orientation.** The model's outcome mapping is `interim_legacy` (label 0 = disease); all reported probabilities are disease-positive, as served by the API.
