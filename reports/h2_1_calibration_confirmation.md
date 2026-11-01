# H2.1 Report: Calibration Confirmation — Pooled Out-of-Fold Sigmoid Calibration

| Field | Value |
|---|---|
| Status | Research only. Production model, artifacts, registry, contract, API and frontend unchanged |
| Date | 2026-11-01 |
| Pre-registration | `openspec/changes/h2-1-calibration-confirmation/design.md` (SHA-256 `134535e1…`) and `proposal.md` (`3ac7cc98…`), both embedded in the results |
| Experiment | `experiments/h2_1_calibration_confirmation.py` |
| Results | `experiments/results/h2_1_calibration_confirmation.json` (content hash excluding runtime `70b6b136…`) |
| Tests | `tests/test_h2_1_calibration_confirmation.py` (7 synthetic tests) |
| **Verdict** | **Confirmed. All four pre-registered acceptance criteria pass** |

> CardioVanta is a research application and is not clinically validated. "Confirmed" means the H2 calibration signal replicated on new partitions of the **same 242 development patients**. It is not external validation, and it does not change production.

## 1. Question
H2 found, descriptively, that pooled out-of-fold sigmoid calibration (`CalibratedClassifierCV(ensemble=False)`) moved the out-of-fold calibration slope from about 1.29 to about 1.02, at no cost to discrimination. H2's own pre-registered rule was not met, because it used the noisy |slope − 1| endpoint. H2.1 tests the finding prospectively:
- a single signed primary endpoint;
- new seeds disjoint from H2's;
- twice as many repeats.

## 2. Design (as pre-registered)
- **Arms.** A is the production recipe (sigmoid, `ensemble=True`). C is pooled OOF (sigmoid, `ensemble=False`). Both use `class_weight="balanced"` and the production preprocessing. Class weighting was dropped as a factor because it had no effect in H2.
- **Data.** 242 development rows via the R4 loader; 0 locked rows parsed; 241 duplicate groups; disease-positive orientation.
- **Cross-validation.** 20 repeats × 5 outer duplicate-aware folds, with seeds 5000+r, 6000+r and 7000+r (disjoint from H2's). Nested C tuning by inner OOF log loss. Calibration is fitted only on outer-training partitions.
- **Primary endpoint.** Δslope = slope(C) − slope(A), with an expected negative direction.
  - The slope comes from an unpenalised LR of y on logit(p), using `C=np.inf`.
  - It is tested with a 95% paired group-bootstrap CI (2,000 resamples, seed 4242, metrics per repeat and then averaged).
- **Guardrail.** ΔROC-AUC 95% CI lower bound ≥ −0.01.
- **Secondary endpoints (supportive only).** Δlog loss, ΔBrier and ΔECE, with Bonferroni 98.33% CIs.

## 3. Results

### 3.1 Arms (mean over 20 repeats [2.5–97.5 percentile across repeats])

| Metric | A: production | C: pooled OOF |
|---|---|---|
| Calibration slope (ideal 1) | 1.267 [1.169, 1.374] | **1.003** [0.910, 1.086] |
| ROC-AUC | 0.9112 [0.9038, 0.9189] | 0.9109 [0.9029, 0.9169] |
| PR-AUC | 0.9020 | 0.9013 |
| Log loss | 0.3802 | 0.3739 |
| Brier | 0.1174 | 0.1160 |
| ECE (10 bins) | 0.0589 | 0.0398 |
| Calibration intercept | −0.002 | −0.001 |
| Calibration-in-the-large | −0.0002 | −0.0001 |
| Selected C (100 folds) | 0.1 ×25, 0.3 ×74, 1.0 ×1 | 0.1 ×68, 0.3 ×32 |

### 3.2 Pre-registered acceptance criteria

| # | Criterion | Value | Result |
|---|---|---|---|
| 1 | Primary Δslope 95% CI upper bound < 0 | Δslope **−0.271 [−0.341, −0.216]** | **Pass** |
| 2 | ΔROC-AUC 95% CI lower bound ≥ −0.01 | −0.0003 [−0.0017, +0.0011] | **Pass** |
| 3 | Mean slope of arm C within [0.90, 1.10] | 1.003 | **Pass** |
| 4 | Δslope < 0 in ≥ 16 of 20 repeats | **20/20** (per-repeat Δslope range −0.300 to −0.232) | **Pass** |

**Verdict: confirmed.** The primary interval also excludes zero at the 98.33% level (upper bound −0.208).

### 3.3 Secondary endpoints (supportive only; they do not affect the verdict)

| Endpoint | Δ (C − A) | 95% CI | Bonferroni 98.33% CI | Repeats favouring C | Supportive at the adjusted level? |
|---|---|---|---|---|---|
| Log loss | −0.0066 | [−0.0198, +0.0088] | [−0.0233, +0.0118] | 18/20 | No |
| Brier | −0.0014 | [−0.0044, +0.0017] | [−0.0051, +0.0025] | 20/20 | No |
| ECE | −0.0130 | [−0.0273, +0.0044] | [−0.0294, +0.0073] | 19/20 | No |

Every secondary endpoint moves in the expected direction in almost all repeats. The effects are small relative to patient-level sampling uncertainty, so none is statistically supported at the adjusted level. The confirmed effect is therefore specifically on **calibration slope** (less under-confidence). Improvements in log loss, Brier score and ECE are consistent with it but not established.

## 4. Interpretation
1. **The production recipe is systematically under-confident.** Its predicted probabilities are compressed toward 0.5 (slope ≈ 1.27). Pooled OOF calibration removes this almost exactly (slope ≈ 1.00), consistently across 20 new partitions.
2. **The mechanism is plausible.** The production ensemble averages five sigmoids, each fitted on about 48 calibration rows, and averaging probabilities pulls them toward the middle. A single sigmoid fitted on all pooled OOF decision values of the training partition avoids both problems.
3. **No discrimination cost.** As expected, recalibration barely changes the ranking (ΔAUC −0.0003).
4. **Combined with R7.** R7 showed that dropping the unresolved features does not fix the under-confidence (slope stays at 1.23–1.29). Calibration method and feature set are separate decisions for any model v2.

## 5. External cohorts (excluded, as pre-registered)
Hungary (n = 294) and Long Beach VA (n = 200) were **not evaluated** and no external data was parsed. The existing mappings are incompatible with the production 13-feature recipe:
- the `slope` and `thal` code mappings are `unverified`;
- the documented −9 missing counts are large. Hungary is missing `ca` 290, `thal` 266 and `slope` 190. Long Beach is missing `ca` 198, `thal` 159 and `slope` 101, plus vitals.
- the contract rejects missing values.

These cohorts were also already used in Phase 17, so they would not be untouched independent validation.

## 6. Limitations
- **Same patients.** The patients are the same as in H2. The new evidence comes from new partitions and a prospective endpoint, not new data, so the replication is internal.
- **Small sample.** 242 patients. The bootstrap intervals for log loss, Brier and ECE are wide.
- **One recipe.** The finding applies to this LR recipe with sigmoid calibration. Isotonic or other methods were not re-tested here.
- **Calibration is not clinical validity.** Better calibration on retrospective development data does not establish calibration in other populations or clinical usefulness.
- **No adoption.** Adopting pooled calibration would mean a new, separately registered model version (for example `2.0.0`) with its own metadata, model card, checksums and golden synthetic predictions, and your explicit approval.

## 7. Verification

| Check | Result |
|---|---|
| Reproducibility | Run 1 took 3,903 s and run 2 took 4,804 s (run 2 overlapped with R7). Their content is identical excluding runtime (`70b6b136…`) |
| Warnings | None in either run log |
| Data | 242 rows; 0 locked rows parsed; no external data parsed |
| Tests | 7/7 synthetic tests pass |
| Production isolation | The artifact integrity check passes. All 18 files under `artifacts/`, `cardiovanta_ml/contracts/` and `data/` have unchanged checksums. There are no changes under `artifacts/`, `cardiovanta_ml/`, `backend/`, `src/`, `api/`, `data/`, `contracts/` or `vercel.json` |
