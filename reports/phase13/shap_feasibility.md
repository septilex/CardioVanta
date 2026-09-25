# Phase 13C.1 — SHAP Feasibility Report

## 1. Overview
This audit evaluates the feasibility of replacing the custom Logistic Regression explanation logic with **SHAP (SHapley Additive exPlanations)**. The analysis was conducted on the isolated `.venv311` environment using the existing production uncalibrated `explanation_model.joblib`.

## 2. Compatibility & Installation
- **SHAP Version:** 0.51.0
- **Compatibility:** Excellent. `shap.LinearExplainer` is 100% compatible with the `scikit-learn` Logistic Regression pipeline. It correctly ingests the transformed background dataset outputted by our `OneHotEncoder` and `StandardScaler` pipeline.

## 3. Runtime & Memory Overhead
SHAP's `LinearExplainer` is exceptionally lightweight:
- **Initialization Time:** ~0.015 seconds
- **Explanation Time (per sample):** <0.001 seconds
- **Peak Memory:** ~0.05 MB
*Conclusion:* SHAP introduces effectively zero overhead and is entirely feasible for real-time production API latency.

## 4. Local Explanation Agreement
We compared SHAP's mathematically derived feature contributions against the current logic (`coefficient * transformed_value`).

**Sum-to-Log-Odds Consistency: PERFECT**
- SHAP (`sum(shap_values) + expected_value`): **0.99276**
- Current Logic (`sum(contributions) + intercept`): **0.99276**

**Individual Feature Contribution Discrepancies**
While the total sum matches perfectly, the individual feature attributions differ significantly:
- *Example discrepancies:* `sex` (0.29), `ca` (0.21), `cp` (0.21)

*Why does this happen?*
- **Current Logic:** Calculates contribution relative to the feature's preprocessed "zero" value (`contrib = coef * X`).
- **SHAP:** Calculates contribution relative to the *average patient* in the background dataset (`contrib = coef * (X - E[X])`). 

**Which is better?**
SHAP is clinically and mathematically superior. Explaining why a patient has a high risk by saying "their cholesterol is higher than the average patient's" (SHAP) is much more intuitive than saying "their cholesterol is higher than a mathematical zero-point vector."

## 5. Raw Feature Mapping
SHAP naturally outputs values for the transformed one-hot encoded columns (e.g., `cp_1`, `cp_2`). We verified that we can seamlessly map these back to the 13 raw features by simply summing the SHAP values of the associated one-hot columns. This preserves the 13-feature structure of the API response.

## 6. Global Feature Importance
By taking the mean absolute SHAP value across the development dataset, we derived the definitive global feature importance for the production model:

1. **thal** (Thalassemia): 0.525
2. **cp** (Chest Pain Type): 0.473
3. **ca** (Number of Major Vessels): 0.381
4. **oldpeak** (ST Depression): 0.329
5. **thalach** (Max Heart Rate): 0.240
6. **slope** (ST Segment Slope): 0.237
7. **chol** (Cholesterol): 0.219
8. **exang** (Exercise Induced Angina): 0.198
9. **sex**: 0.188
10. **restecg** (Resting ECG): 0.127
11. **trestbps** (Resting Blood Pressure): 0.086
12. **age**: 0.007
13. **fbs** (Fasting Blood Sugar): 0.003

## 7. Conclusion
**SHAP adds immense, meaningful value.** It is fast, lightweight, and provides a much more intuitive baseline (the "average patient") for local explanations than the current manual coefficient multiplication. 

Replacing the custom logic in `src/inference/predict.py` with `shap.LinearExplainer` is highly recommended for a future production update, as it aligns the API with industry-standard interpretable machine learning practices without impacting inference latency.
