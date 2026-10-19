# Proposal

## Why

The evaluated model achieved 86.89% accuracy on the existing 61-observation locked test (TN=22, FP=6, FN=2, TP=31). The current experiments do not establish a theoretical accuracy ceiling or determine whether 95% accuracy is achievable. Formal error analysis indicates the model struggles with non-linear relationships in `oldpeak` and interaction effects like age-adjusted maximum heart rate (`thalach` × `age`). These error patterns serve as exploratory hypotheses rather than independent confirmation. This change proposes investigating targeted feature representations within a leak-free nested cross-validation framework to determine if they can safely improve predictive performance over the frozen baseline.

## What Changes

- A new ML research phase (Phase 16) targeting feature engineering.
- Introduction of controlled, explicit feature representations including:
  - `thalach` × `age` interaction term.
  - A nonlinear representation of `oldpeak` (polynomial degree 2).
- Rigorous nested-CV framework specifying fold-local sigmoid calibration with duplicate-aware grouping for both candidates and baseline (resolving the uncalibrated evaluation limitation of the prior advanced model search), with explicit design controls whose correct enforcement must be demonstrated through implementation and tests.
- **BREAKING**: No production behavior, threshold, or model artifacts will be modified by this specific change. It is strictly for generating reproducible research evidence.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None.

## Impact

- **Affected Code**: `experiments/phase_16_feature_engineering.py` (dedicated research script implementing nested CV with calibration isolation), preserving existing production code and `experiments/advanced_model_search.py` untouched.
- **Data Lineage**: The design specifies controls intended to prevent data leakage: preprocessing, candidate selection, and calibration fitting must remain strictly fold-local, calibration folds must respect duplicate-aware grouping via `StratifiedGroupKFold`, and production calibrator artifacts must never be reused for validation folds. Implementation and tests must demonstrate that these controls are correctly enforced. Locked-test data is strictly protected from candidate selection; evaluation on the previously inspected locked test is retrospective, and independent external data are required for stronger independent generalization claims.
