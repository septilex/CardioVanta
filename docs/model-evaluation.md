# Model Evaluation & Robustness

## Nested CV Evaluation
Models were evaluated on the 242 development samples utilizing Out-of-Fold (OOF) predictions.

## Subgroup Analysis
Subgroup-specific estimates were analyzed to observe descriptive differences.
- **Constraint:** Minimum subgroup size of 20 and minimum class size of 5 for estimability.
- Subgroups smaller than 20 (e.g., `cp=3` with size 15, `restecg=2` with size 4, `slope=0` with size 17) were explicitly marked as "Not estimable".
- This analysis is descriptive only and not for ranking clinical subsets.

## Feature Stability
Models were subjected to data perturbations and resampling robustness evaluations to measure prediction stability. All evaluations excluded the locked 20% test samples.
