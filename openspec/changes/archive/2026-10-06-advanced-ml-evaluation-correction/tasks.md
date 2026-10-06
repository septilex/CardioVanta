# Tasks

## 1. Automated Tests

- [ ] 1.1 Create `tests/test_leakage.py` with mock tests verifying that `StratifiedGroupKFold` outer and inner splits do not overlap groups, and the locked test set indices are isolated. Run `pytest tests/test_leakage.py` to verify the test suite runs.

## 2. Preprocessing & Candidate Space

- [ ] 2.1 Update `get_candidates` in `experiments/advanced_model_search.py` to remove `VotingClassifier` and `StackingClassifier`. Verify removal via code inspection.
- [ ] 2.2 Update `experiments/advanced_model_search.py` to assign tree preprocessing strictly to tree models, and linear preprocessing to linear models. Verify via code inspection.

## 3. Nested CV Implementation

- [ ] 3.1 Implement a custom nested CV loop in `experiments/advanced_model_search.py` using outer and inner `StratifiedGroupKFold` splits for hyperparameter selection per model family. Verify via `python experiments/advanced_model_search.py` (or a dry run mode).
- [ ] 3.2 Update the script to collect metadata (Python, sklearn, pandas, numpy, xgboost, lightgbm, catboost versions) and include it in `experiments/results/candidate_comparison.json`. Verify the JSON output contains these fields.

## 4. Execution and Reporting

- [ ] 4.1 Execute `experiments/advanced_model_search.py` to generate the corrected `candidate_comparison.json`. Verify the script completes successfully and outputs valid nested-CV metrics.
- [ ] 4.2 Update `reports/advanced_ml_performance_investigation.md` to reflect the new nested-CV results, remove overclaims (e.g., "absolute global optimum", "irreducible Bayes error"), and document the exclusion of Stacking. Verify the markdown renders correctly and claims are scientifically sound.
