# Tasks

## 1. Automated Tests
- [x] 1.1 Create `tests/test_global_leakage.py` proving inner and outer folds share no groups, and inner folds never use outer validation data. Run `python tests/test_global_leakage.py`.

## 2. Global Nested CV Implementation
- [x] 2.1 Refactor `experiments/advanced_model_search.py` to loop over all 97 candidates inside the inner CV, select the single best candidate per outer fold, and evaluate. Exclude stacking explicitly. 
- [x] 2.2 Record the raw dataset byte hash and accurate library versions.

## 3. Execution & Reporting
- [x] 3.1 Run `python experiments/advanced_model_search.py` to produce final locked-test JSON.
- [x] 3.2 Update `reports/advanced_ml_performance_investigation.md` without overclaims.
