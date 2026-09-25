# Calibration

Calibration was performed using a 5-fold Cross-Validation approach to ensure predicted probabilities reliably reflect true likelihoods.

## Method Comparison
The selection rule sought the lowest mean Brier score combined with a Log Loss stability check.
- **Uncalibrated:** Mean Brier = 0.1235, Mean Log Loss = 0.3959
- **Isotonic:** Mean Brier = 0.1200, Mean Log Loss = 0.6516
- **Sigmoid:** Mean Brier = 0.1210, Mean Log Loss = 0.3860
- **Temperature:** Mean Brier = 0.1218, Mean Log Loss = 0.3871

## Selected Calibration: Sigmoid
Although Isotonic regression achieved a marginally lower Brier score, its high Log Loss (0.65) was consistent with a high risk of overfitting on the small calibration dataset. Therefore, **Sigmoid** calibration was selected as the optimal method.
