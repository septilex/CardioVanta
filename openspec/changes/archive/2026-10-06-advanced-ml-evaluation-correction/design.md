# Design

## Context

See proposal.md. The existing evaluation relies on a single-level cross-validation loop and uses standard (non-grouped) stratification for its stacking ensemble, which allows duplicate rows to leak across training and validation folds. 

## Goals / Non-Goals

**Goals:**
- Implement a true nested cross-validation architecture (Outer Grouped CV -> Inner Grouped CV).
- Prevent duplicate-row leakage in all phases.
- Capture exact dependencies (versions of Python, scikit-learn, etc.).
- Produce automated tests verifying the absence of data leakage.

**Non-Goals:**
- Modifying production model artifacts or tags.
- Exhaustively searching all possible ML models (we stick to the defined candidate families).
- Writing a custom stacking regressor from scratch.

## Decisions

1. **Nested Cross-Validation Implementation**:
   - **Decision**: We will implement a custom nested CV loop.
   - **Rationale**: For each model family (e.g., Logistic Regression, Random Forest), we will perform an inner `StratifiedGroupKFold` (5 splits) over the parameter grid to select the best hyperparameter configuration for that outer fold. We will then fit this best configuration on the entire outer training fold and evaluate it on the outer validation fold (`StratifiedGroupKFold`, 5 splits). This yields an unbiased estimate of generalization performance for each model family.
   - **Alternatives**: Using `GridSearchCV(cv=StratifiedGroupKFold(...))` inside `cross_val_predict(cv=StratifiedGroupKFold(...))`. This works but requires careful passing of the `groups` parameter. Custom loop is more explicit and easier to assert/test for leakage.

2. **Stacking and Ensembles**:
   - **Decision**: Exclude `StackingClassifier` and `VotingClassifier` from the candidate comparison.
   - **Rationale**: `StackingClassifier` natively uses standard `StratifiedKFold` for generating meta-features, which ignores duplicate-aware groupings unless carefully hacked or rewritten. Given that the user requested to exclude it rather than force it if it's unsafe, and because ensembles provide minimal benefit over the linear baseline on this specific dataset, exclusion is the safest path.

3. **Preprocessing Standardization**:
   - **Decision**: Strictly apply linear preprocessing (scaling + OHE) only to linear models (LR, SVM), and tree preprocessing (OHE only) to tree models.
   - **Rationale**: Prevents unnecessary scaling for tree models and ensures fair comparison. All preprocessing remains encapsulated within `sklearn.pipeline.Pipeline`.

4. **Reproducibility Metadata**:
   - **Decision**: Capture `sys.version`, and `__version__` of `sklearn`, `numpy`, `scipy`, `pandas`, `xgboost`, `lightgbm`, and `catboost` in the final output JSON.

## Risks / Trade-offs

- **Risk**: Increased computational time due to Nested CV (5x more fits).
  - **Mitigation**: The dataset is small (242 dev samples), so the overhead is acceptable and necessary for methodological validity.
- **Risk**: Automated tests for leakage might be flaky if data subsets naturally have unique groups.
  - **Mitigation**: The tests will explicitly check that `set(train_groups).intersection(set(val_groups))` is empty.
