# Formal Error Analysis: Logistic Regression Baseline

## 1. Scope
Perform a formal, diagnostic error analysis on the selected Logistic Regression baseline. This analysis is descriptive and diagnostic. It will not tune hyperparameters, thresholds, or select a new model. The purpose is to systematically profile the errors to form hypotheses for future ML phases.

## 2. Frozen Model Definition
**FACT**: The selected candidate is `LR_production`.
- **Algorithm**: Logistic Regression
- **C**: 0.1
- **class_weight**: 'balanced'
- **Calibration**: Sigmoid (fitted on development set using 5-fold CV)

## 3. Dataset/Split Definition
**FACT**: The dataset is identical to the global nested-CV phase.
- **Development Set**: 242 rows.
- **Locked Test Set**: 61 rows.
- **Data Leakage Prevention**: Duplicate records share the same `dev_groups` identifier to prevent contamination between folds.

## 4. Development-Set Diagnostic Analysis
**FACT**: Evaluated using StratifiedGroupKFold out-of-fold (OOF) uncalibrated probabilities.
- **OOF True Positives (TP)**: 111
- **OOF True Negatives (TN)**: 91
- **OOF False Positives (FP)**: 19
- **OOF False Negatives (FN)**: 21

## 5. Locked-Test Descriptive Analysis
**FACT**: Evaluated using the final model calibrated on the full development set.
- **Test True Positives (TP)**: 31
- **Test True Negatives (TN)**: 22
- **Test False Positives (FP)**: 6
- **Test False Negatives (FN)**: 2

## 6. Confusion Matrix
**OBSERVATION**: The model favors sensitivity (Recall: 0.939) over specificity (Specificity: 0.786). It is significantly more likely to produce a false positive than a false negative on both the OOF dev set (FP=19, FN=21 is balanced, but on test FP=6, FN=2). 

## 7. False-Positive Analysis
**OBSERVATION**: The false positives occur when patients without heart disease are incorrectly classified as having it. 
- In the dev set, FP cases tend to have lower cholesterol (median 244) than TN cases (median 254).
- In the test set, FP cases have higher resting blood pressure (median 132) compared to TN cases.

## 8. False-Negative Analysis
**OBSERVATION**: The false negatives occur when patients with heart disease are missed.
- Dev FN cases have notably lower max heart rate (thalach median 146) compared to TP cases (163).
- Test FN cases also show lower max heart rate (135.5) compared to TP cases (162.0).

## 9. Probability/Borderline Analysis
**OBSERVATION**: 
- **Highest-confidence error (Dev)**: FP with a probability of 0.925.
- **Highest-confidence error (Test)**: FP with a probability of 0.831.
- **Lowest-confidence correct (Dev)**: TN with a probability of 0.498 (distance to 0.5 is 0.001).
- **Lowest-confidence correct (Test)**: TP with a probability of 0.511 (distance to 0.5 is 0.011).

## 10. Feature-Level Error Analysis
**OBSERVATION**: 
- **thalach (Max Heart Rate)**: Highly distinct between correct positives and false negatives. 
- **oldpeak**: Dev FN cases have a median of 0.6, while TP cases are 0.0. Test FN cases have a median of 0.8, TP cases 0.4.

## 11. Model-Contribution Analysis
**INTERPRETATION**: The Logistic Regression baseline is heavily influenced by `thalach`, `oldpeak`, and `cp`. The model contributions are strictly mathematical weights within the linear decision function and DO NOT establish independent medical causality or clinical recommendations.

## 12. Data-Quality Observations
**OBSERVATION**: No overt systemic data quality issues (missingness, broken encodings) strongly correlate with errors. The model successfully handles the known duplicate records without fold leakage.

## 13. Stable Patterns Found
**INTERPRETATION**: 
- The model consistently struggles with patients who have lower maximum heart rates but still have heart disease (False Negatives).
- The model occasionally over-predicts disease in patients with asymptomatic chest pain (`cp`=0) if their other features are borderline.

## 14. Patterns NOT Established
**FACT**: No stable error mechanism was established from the available sample regarding demographic variables (`age`, `sex`).

## 15. Future Improvement Hypotheses
**INTERPRETATION**: Based ONLY on the evidence:
1. **Interaction Terms**: `thalach` and `age` interactions could better capture the age-adjusted heart rate thresholds that differentiate FNs from TPs. (Low leakage risk; evaluate via OOF CV).
2. **Nonlinear Transformations**: `oldpeak` could benefit from polynomial features or binning since its distribution varies sharply between TP and FN. (Low leakage risk; evaluate via OOF CV).
3. **Threshold Policy**: Since FPs outnumber FNs in the locked test, and precision is lower, adjusting the decision threshold could optimize F1 without retraining the model. (High leakage risk if tuned on locked test; must use dev set).

## 16. Limitations
**LIMITATION**: This analysis relies on a small locked test set (61 rows). The observed 6 FPs and 2 FNs are too small for statistical significance testing. All locked-test analysis is strictly descriptive and post-hoc.

## 17. Conclusions
**INTERPRETATION**: The baseline Logistic Regression model exhibits a stable error profile, primarily struggling with borderline cases involving `thalach` and `oldpeak`. The results from this diagnostic phase provide concrete hypotheses for future feature engineering. No stable error mechanism was established from the available sample that would render these errors entirely unavoidable.
