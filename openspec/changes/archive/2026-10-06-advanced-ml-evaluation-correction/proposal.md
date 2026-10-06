# Proposal

## Why

The current `advanced_model_search.py` experiment contains critical methodological flaws including a lack of genuine nested cross-validation and duplicate-row leakage in stacking ensembles. This correction establishes a rigorous, leakage-free ML evaluation framework to ensure any claims about global optimums or Bayes error are scientifically valid and reproducible.

## What Changes

- **BREAKING**: Replaces the single-level `StratifiedGroupKFold` with a true nested CV architecture (Outer Grouped CV -> Inner Grouped CV -> Hyperparameter Selection).
- **BREAKING**: Replaces standard `StratifiedKFold` inside `StackingClassifier` with duplicate-aware grouping, or excludes stacking if unsupported.
- Enforces strict isolation of the 61-sample locked test set during all stages of model selection, feature engineering, and hyperparameter tuning.
- Captures environment and dependency versions (Python, scikit-learn, XGBoost, etc.) into the experiment's final JSON output.
- Refines the candidate search reporting to accurately reflect it as the "best candidate among the evaluated search space" rather than an "absolute global optimum."
- Validates these properties via automated tests before final execution.

## Capabilities

### New Capabilities
<!-- No new application capabilities, skip_specs is true -->

### Modified Capabilities
<!-- No existing capabilities changed -->

## Impact

- `experiments/advanced_model_search.py` will be completely overhauled for nested CV.
- `reports/advanced_ml_performance_investigation.md` will have its claims corrected.
- Automated tests will be introduced to validate the leakage-free implementation.
- Will not affect production model `artifacts/model/` or the `v1.0.1` tag.
