# Advanced ML Performance Investigation: Final Report

## FACTS

- **Baseline**: Logistic Regression (`C=0.1`, `class_weight="balanced"`).
- **Candidates Evaluated**: Exactly 97 distinct configurations across 8 families (LR, SVM, RF, GBM, XGB, LGBM, CatBoost) plus the baseline. Stacking and Voting ensembles were explicitly excluded to prevent duplicate-row leakage.
- **Validation Scheme**: Grouped 5-fold Nested Cross-Validation (outer grouped stratified CV -> inner grouped stratified CV -> candidate selection -> outer validation evaluation).
- **Selection Rule**: Predefined global selection rule using raw uncalibrated Inner ROC-AUC as primary metric and Inner Accuracy as tie-breaker.
- **Calibration**: Candidate selection uses raw uncalibrated model probabilities. The final selected candidate is calibrated with sigmoid calibration on development data. The locked test remains untouched until final evaluation.
- **Nested-CV OOF Estimates (Selection Process)**:
  - Accuracy: 0.8430
  - ROC-AUC: 0.9088
  - Average Precision: 0.9077
  - F1: 0.8571
- **Outer Fold Exploratory Observations**: The highest outer-fold accuracy observed during the selection process was 85.41% (from `LR C=0.5` configurations). This is not an unbiased independent global performance estimate for those configurations, but rather a fold-specific exploratory observation, as global nested CV estimates the complete model-selection procedure.
- **Final Selected Candidate**: `LR_production (C=0.1, class_weight='balanced')` (the selected candidate under the predefined global nested-CV selection rule from the evaluated 97-configuration search space).
- **Locked-Test Evaluation** (Evaluated exactly once):
  - Accuracy: 0.8689
  - ROC-AUC: 0.9048
  - Average Precision: 0.9225
  - Precision: 0.8378
  - Recall: 0.9394
  - Specificity: 0.7857
  - F1: 0.8857
  - Brier: 0.1280
  - Log loss: 0.3997
- **95% Target**: NOT ACHIEVED.

## DECISIONS

- The 95% accuracy target was not achieved.
- No model modifications are deployed. The existing production configuration remains the selected candidate under the predefined global nested-CV selection rule from the evaluated 97-configuration search space.

## CONCLUSIONS

The corrected global nested-CV evaluation selected LR_production under the predefined selection rule. The 95% accuracy target was not achieved. The results do not establish an absolute accuracy ceiling or clinical validity.

## LIMITATIONS

- The evaluation is strictly limited to the 97 configurations and the specific hyperparameters defined in the search space.
- Global nested CV estimates the performance of the model-selection procedure itself; it does not provide unbiased performance estimates for every candidate individually.
- The results do not guarantee absolute future performance ceilings or represent an irreducible Bayes error.
