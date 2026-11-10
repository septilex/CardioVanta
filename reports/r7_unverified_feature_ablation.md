# R7 Report: Unverified Feature Ablation — `slope`, `thal`, `ca`

| Field | Value |
|---|---|
| Status | Research only. Production model, artifacts, registry, contract, API and frontend unchanged |
| Date | 2026-10-31 |
| Pre-registration | `openspec/changes/r7-unverified-feature-ablation/design.md`, SHA-256 `1805b17f…`, fixed before any R7 code was written or run |
| Experiment | `experiments/r7_unverified_feature_ablation.py` |
| Results | `experiments/results/r7_unverified_feature_ablation.json` (content hash excluding runtime `7931f88c…`) |
| Tests | `tests/test_r7_unverified_feature_ablation.py` (21 synthetic tests); `tests/test_r7_slope_reporting_correction.py` (8 tests) |
| Correction | **R7-C1 (2026-11-01):** calibration-slope comparisons restated by \|slope − 1\| (see §7). No rerun; original results and labels unchanged |
| **Outcome** | **The recipe depends materially on `ca` and on `thal`, and strongly on the three together. It barely depends on `slope`. H7.1 and H7.4 are supported. The `thal` result is not robust to the multiplicity correction** |

> CardioVanta is a research application and is not clinically validated. These results describe statistical dependence on the Kaggle training encoding. They assign no clinical meaning to any code.

## 1. Question and design

How much do the discrimination and calibration of the production training recipe depend on the features whose codes are unresolved (R6)? Five arms were compared on identical splits:

| Arm | Removed | Inputs |
|---|---|---|
| A_baseline | none | 13 |
| B_no_slope | `slope` | 12 |
| C_no_thal | `thal` | 12 |
| D_no_ca | `ca` | 12 |
| E_no_slope_thal_ca | all three | 10 |

**Protocol (as pre-registered):**
- **Data:** the 242 development rows only, via the R4 loader. Locked lines are never parsed. Orientation is disease-positive.
- **Splits:** duplicate-aware groups (241 groups), with StratifiedGroupKFold everywhere.
- **Cross-validation:** 10 repeats × 5 outer folds. In each outer-training partition, C ∈ {0.01…3} is tuned by inner 5-fold OOF log loss, followed by sigmoid calibration (`ensemble=True`, the production recipe).
- **Uncertainty:** paired group bootstrap (2,000 resamples, metrics per repeat and then averaged). Bonferroni intervals at 98.75% (4 comparisons) are a sensitivity analysis.
- **Secondary analysis:** C fixed at 0.1 (descriptive).
- **Classification rule:** see `design.md`.
  - *Dependence* means ΔAUC CI high < 0 or Δlog-loss CI low > 0.
  - *Non-inferior* means ΔAUC CI low ≥ −0.01 and Δlog-loss CI high ≤ +0.01.

## 2. Results (primary analysis: nested, tuned C)

### 2.1 Per-arm performance (mean of per-repeat metrics)

| Arm | ROC-AUC | PR-AUC | Log loss | Brier | Calibration slope |
|---|---:|---:|---:|---:|---:|
| A_baseline | 0.9128 | 0.9041 | 0.3780 | 0.1169 | 1.287 |
| B_no_slope | 0.9116 | 0.9030 | 0.3801 | 0.1181 | 1.283 |
| C_no_thal | 0.9009 | 0.8899 | 0.4039 | 0.1269 | 1.284 |
| D_no_ca | 0.9002 | 0.8888 | 0.4022 | 0.1267 | 1.249 |
| E_no_slope_thal_ca | 0.8769 | 0.8630 | 0.4419 | 0.1429 | 1.229 |

The baseline reproduces the production-recipe results of R4 and H2 exactly (AUC 0.9128, log loss 0.3780, slope 1.287), which is an internal consistency check. Bootstrap 95% intervals for each arm's absolute metrics are in the JSON (`paired_group_bootstrap.absolute`).

### 2.2 Paired differences, ablation − baseline (bootstrap mean, 95% CI; repeats in which the ablation is worse)

| Arm | ΔROC-AUC | ΔPR-AUC | ΔLog loss | ΔBrier | ΔCalibration slope |
|---|---|---|---|---|---|
| B_no_slope | −0.0012 [−0.0075, +0.0052] · 8/10 | −0.0012 [−0.0101, +0.0071] | +0.0021 [−0.0077, +0.0118] · 8/10 | +0.0012 [−0.0029, +0.0053] | −0.004 [−0.078, +0.065] |
| C_no_thal | −0.0119 [−0.0290, +0.0049] · 10/10 | −0.0143 [−0.0347, +0.0041] | **+0.0260 [+0.0023, +0.0494]** · 10/10 | **+0.0100 [+0.0003, +0.0198]** | −0.004 [−0.172, +0.174] |
| D_no_ca | −0.0127 [−0.0262, +0.0004] · 10/10 | **−0.0156 [−0.0312, −0.0023]** | **+0.0245 [+0.0064, +0.0425]** · 10/10 | **+0.0099 [+0.0029, +0.0172]** | −0.043 [−0.172, +0.074] |
| E_no_slope_thal_ca | **−0.0360 [−0.0621, −0.0107]** · 10/10 | **−0.0414 [−0.0747, −0.0120]** | **+0.0642 [+0.0297, +0.0974]** · 10/10 | **+0.0261 [+0.0123, +0.0397]** | −0.066 [−0.296, +0.158] |

Bold marks a 95% interval that excludes zero.

### 2.3 Pre-registered classification

| Arm | Label (95%) | Label (Bonferroni 98.75%) | Robust to multiplicity |
|---|---|---|---|
| B_no_slope | `inconclusive` | `inconclusive` | yes |
| C_no_thal | **`material_dependence`** | `inconclusive` | **no** |
| D_no_ca | **`material_dependence`** | `material_dependence` | yes |
| E_no_slope_thal_ca | **`material_dependence`** | `material_dependence` | yes |

**Notes on each label:**
- **`slope`** is labelled `inconclusive` because its log-loss interval (upper bound +0.0118) slightly exceeds the +0.01 non-inferiority margin. The estimated effect is close to zero on every metric. With 242 patients, the data cannot certify non-inferiority at that margin.
- **`thal`:** the Δlog-loss interval excludes zero at 95% (+0.0023 lower bound) but not at the Bonferroni level (−0.0049).
- **`ca`:** the Δlog-loss interval excludes zero at both levels.

### 2.4 Hypotheses

| Hypothesis | Result |
|---|---|
| H7.1: removing `thal` shows dependence | **Supported** (`material_dependence`), but not robust to multiplicity |
| H7.2: `slope` (exploratory, two-sided) | No detectable dependence; non-inferiority not certified |
| H7.3: `ca` (exploratory, two-sided) | Material dependence, robust |
| H7.4: Δlog loss of E ≥ the largest single-feature Δlog loss | **Supported**: +0.0639 vs +0.0259 (per-repeat means) |

The combined effect (+0.064) is larger than the sum of the single effects (+0.052). So these features are not interchangeable: each carries signal the others do not fully replace.

## 3. Secondary analysis (C fixed at 0.1, descriptive)

| Arm | ΔROC-AUC (per-repeat mean, 2.5–97.5%) | ΔLog loss | Repeats worse (log loss) |
|---|---|---|---|
| B_no_slope | −0.0005 [−0.0009, +0.0004] | +0.0025 | 9/10 |
| C_no_thal | −0.0154 [−0.0180, −0.0119] | +0.0331 | 10/10 |
| D_no_ca | −0.0112 [−0.0131, −0.0091] | +0.0234 | 10/10 |
| E_no_slope_thal_ca | −0.0368 [−0.0407, −0.0317] | +0.0679 | 10/10 |

The pattern holds with regularisation held constant, and the `thal` effect is somewhat larger there. These intervals reflect variation across repeats only, not across patients, so they are much narrower than the bootstrap intervals and are not inferential.

## 4. Other observations
- **Selected C.** Ablated arms chose weaker regularisation more often. The baseline chose C = 0.1 or 0.3; E chose C = 0.3 or 1.0 in 47 of 50 folds. This is expected when fewer columns remain.
- **Prediction change.** The mean absolute change in an individual predicted probability relative to the baseline was 0.029 (B), 0.069 (C), 0.054 (D) and 0.098 (E).
- **Calibration slope.** Every arm stays under-confident (slope about 1.23–1.29). Ablation does not fix this, and slope differences are not significant. Pooled OOF calibration (H2, under confirmation in H2.1) remains the lead for calibration.
- **Bootstrap-scale slope.** On bootstrap resamples, absolute slope estimates average higher (for example 1.319 for the baseline) than on the full data, because of resampling duplicates. Point estimates in §2.1 use the full data.
- **Direction convention (corrected, see §7).** The original JSON field `calibration_slope.repeats_ablation_worse` treated a lower signed slope as worse. For slope, closer to 1 is better. §7 restates the comparison by |slope − 1|. No label was affected.

## 5. Interpretation and implications

1. **Removing the unresolved features has a measurable cost.** Removing all three loses about 0.036 AUC and adds about 0.064 to log loss, with intervals excluding zero after correction. A model v2 that simply drops them would be clearly weaker on this cohort.
2. **The cost is concentrated in `ca` and `thal`.** `slope` contributes little: under 0.002 AUC in either analysis.
3. **This raises the value of resolving the codebook (R6).** The model relies on `thal`, whose codes 1–3 are unverified and whose code 0 is undefined. It also relies on `ca`, whose codes 0–3 are codebook-supported but whose code 4 is undefined. R6's recommended path (a pre-registered, development-only patient match, which needs your authorisation) would now settle a question with a demonstrated performance stake.
4. **Product implication (not acted on).** A user cannot meaningfully choose a `thal` code, yet the prediction depends on it. Options include displaying the range of predictions across the allowed codes, or a model tier that excludes these inputs (arm E: AUC 0.877). Either would need a separate, approved change.

## 6. Limitations
- **Single cohort.** 242 Cleveland patients; no external validation. Effects may differ in Hungary and Long Beach, where `ca` and `thal` are often missing.
- **Margins.** The non-inferiority margins (−0.01 AUC, +0.01 log loss) are project conventions, not clinically derived.
- **Dependence is not meaning.** These results show the recipe uses these columns. They show nothing about what the codes mean, whether `ca = 4` or `thal = 0` are missing-value codes, or whether any code is clinically valid.
- **Ablation removes a whole feature.** Recoding or merging individual codes was not tested, because it would require assigning meanings.
- **Fixed recipe.** Other model families might depend on these features differently.

## 7. Reporting correction R7-C1: calibration slope by |slope − 1| (2026-11-01)

**Issue.** In the saved JSON, `per_repeat_differences_vs_baseline.<arm>.calibration_slope.repeats_ablation_worse` counted a lower *signed* slope as worse. For calibration slope, closer to 1 is better. Every R7 slope is above 1 at the repeat level, so a lower slope means a slope closer to 1. The original field therefore counted the repeats in which the ablation was **better** calibrated, despite its name.

**Correction.** `experiments/r7_slope_reporting_correction.py` recomputes the comparison from the saved per-repeat slopes as Δ|slope − 1| (arm − baseline; negative = closer to 1 = better). It reuses the saved paired-bootstrap Δ|slope − 1|. No experiment was rerun, and no data or model was touched.
- The step adds a `reporting_corrections` block (`R7-C1`) to the results JSON. Every original field is left unchanged; the block records the superseded values and their convention.
- It refuses to run unless the original content matches the verified reproducible hash (`7931f88c…`).
- Recomputed per-repeat values match the saved `abs_slope_minus_1` differences exactly.

**Corrected comparison (primary analysis, nested tuned C)**

| Arm | Signed slope, mean [min, max] over repeats | \|slope − 1\| mean | Δ\|slope − 1\| per repeat | Repeats closer to 1 / further | Δ\|slope − 1\| bootstrap 95% CI | Original field (superseded) |
|---|---|---:|---:|---|---|---:|
| A_baseline | 1.287 [1.177, 1.362] | 0.287 | — | — | — | — |
| B_no_slope | 1.283 [1.191, 1.349] | 0.283 | −0.004 | 6 / 4 | [−0.078, +0.063] | 6 |
| C_no_thal | 1.284 [1.144, 1.357] | 0.284 | −0.003 | 7 / 3 | [−0.171, +0.174] | 7 |
| D_no_ca | 1.249 [1.167, 1.311] | 0.249 | −0.037 | 10 / 0 | [−0.172, +0.070] | 10 |
| E_no_slope_thal_ca | 1.229 [1.085, 1.317] | 0.229 | −0.058 | 9 / 1 | [−0.295, +0.158] | 9 |

**Secondary analysis (C = 0.1, per repeat):**

| Arm | Δ\|slope − 1\| | Closer to 1 / further |
|---|---:|---|
| B | −0.003 | 6 / 4 |
| C | −0.026 | 9 / 1 |
| D | −0.033 | 10 / 0 |
| E | −0.064 | 10 / 0 |

**Crossings below 1 (flagged).**
- No arm has a slope below 1 in any repeat, in either analysis.
- The only crossing is in the bootstrap: arm E's 95% interval for its absolute slope is [0.989, 1.598], with the lower bound just below 1.

So no arm is shown to be over-confident. For arms B–D the signed and absolute comparisons agree, because no slope crosses 1.

**Corrected interpretation.**
- Removing features moves the slope slightly **closer** to 1, most clearly without `ca` (10/10 repeats in both analyses) and without all three.
- The effect is small: at most −0.06 in |slope − 1|. Every bootstrap interval includes 0.
- It is about a fifth of the effect of pooled OOF calibration (H2.1: −0.27). It comes alongside the losses in discrimination and log loss reported in §2.

The conclusion in §4 stands: ablation does not fix the under-confidence. The pre-registered labels, hypotheses and every original number in §§2–3 are unchanged.

## 8. Verification

| Check | Result |
|---|---|
| Pre-registration before execution | `design.md` hash `1805b17f…` recorded at 17:28:51 UTC. The first run started at 17:34:06 UTC. The results embed the same hash |
| Data | 242 development rows; 0 locked rows parsed; 241 duplicate groups; prevalence 0.455 |
| Identical splits | One outer-fold hash (`f191e82d…`) shared by all arms and both analyses |
| Reproducibility | Two full runs (1,152 s and 1,168 s, 9 worker processes) have identical content excluding runtime (`7931f88c…`) |
| Warnings | No warnings in either run (run with FutureWarning treated as an error) |
| Tests | 21/21 synthetic tests pass, including: invariance to removed features, unchanged test-fold predictions under label flips, parallel = sequential, a bootstrap independent of job count, and classification-rule cases |
| Correction R7-C1 | No rerun. All original JSON fields and their order are unchanged (original content hash `7931f88c…` re-verified). The step is idempotent (a second application gives a byte-identical file). 8/8 correction tests pass |
| Production isolation | The artifact integrity check passes. All 18 files under `artifacts/`, `cardiovanta_ml/contracts/` and `data/` have the same checksums before and after. There are no changes under `artifacts/`, `cardiovanta_ml/`, `backend/`, `src/`, `api/`, `data/`, `contracts/` or `vercel.json` |
