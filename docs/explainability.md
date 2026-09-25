# Explainability

## Dual-Model Explanation Architecture
The system employs a dual-model explanation architecture.
- **Note:** Local explanations detail the underlying uncalibrated Logistic Regression decision function (log-odds). They **do NOT** decompose the final calibrated ensemble probability.
- Neither global nor local explanations imply clinical causality.

## Global Permutation Importance
Calculated using Out-of-Fold Permutation Importance (ROC-AUC). The top contributing features are:
1. `thal` (mean: 0.0468)
2. `cp` (mean: 0.0319)
3. `ca` (mean: 0.0211)
4. `oldpeak` (mean: 0.0169)
5. `sex` (mean: 0.0135)
