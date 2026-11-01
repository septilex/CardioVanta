# Proposal: H2 — Calibration of the Production Recipe (research only)

## Why
R4 (`reports/r4_ca_count_encoding.md`, §6) observed systematic under-confidence in the production training recipe:
- the out-of-fold calibration slope was about 1.28;
- the per-repeat range, 1.19–1.36, excludes 1;
- the pattern held in both arms and both analyses.

Two parts of the recipe are plausible causes, and neither has been tested for calibration in Phases 2–17:
- **`class_weight="balanced"`.** It was tuned only for ROC-AUC in Phase 2B, and it shifts and rescales the base model's scores before calibration.
- **Ensemble sigmoid calibration.** `CalibratedClassifierCV(ensemble=True)` averages 5 per-fold calibrated members, each sigmoid fitted on about 48 rows. The alternative, pooled calibration (`ensemble=False`), fits one sigmoid on the pooled out-of-fold decision values of the training partition and applies it to one model refitted on the whole partition.

## Hypothesis (H2)
Removing class-balanced weighting, using pooled out-of-fold sigmoid calibration, or both, will bring the calibration slope closer to 1 and reduce log loss, without a meaningful loss of ROC-AUC.

## What Changes
- New research experiment `experiments/h2_calibration_recipe.py`. It compares four arms on identical repeated, duplicate-aware nested-CV splits, using only the 242 development rows.
- Synthetic regression tests in `tests/test_h2_calibration_recipe.py`.
- Results in `experiments/results/h2_calibration_recipe.json`, and a report in `reports/h2_calibration_recipe.md`.
- The experiment's calibration-slope estimator uses `C=np.inf`, replacing the `penalty=None` option deprecated in scikit-learn 1.9. Pinned dependencies are unchanged.

## Non-goals
- No change to the production model, artifacts, registry, feature contract, outcome orientation, API or frontend.
- No retraining of the production model.
- No access to the 61 locked rows or to external cohorts.
- No adoption decision. A supported arm would only motivate a future, separately registered model version.
