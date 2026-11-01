# Spec Delta

## ADDED Requirements

### Requirement: Leakage-Free Feature Ablation
The R7 experiment SHALL use only the 242 Cleveland development rows, parsing only their lines, with disease-positive orientation. It SHALL evaluate all five arms on identical duplicate-aware outer splits, and SHALL fit preprocessing, regularisation tuning and calibration only within training data.

#### Scenario: Ablated arm never sees removed features
- **WHEN** an ablation arm is fitted and evaluated
- **THEN** its predictions are invariant to the values of the removed features

#### Scenario: Test labels unused
- **WHEN** a model is evaluated on an outer test fold
- **THEN** changing that fold's labels does not change its predictions

### Requirement: Pre-Registered Classification
The experiment SHALL label each ablation against the baseline using the rule fixed in `design.md` before execution. It SHALL report paired 95% bootstrap intervals, Bonferroni sensitivity intervals and repeat-level differences for ROC-AUC, PR-AUC, log loss, Brier score and calibration slope.

#### Scenario: Reporting
- **WHEN** the experiment completes
- **THEN** every ablation has a label, interval estimates for every metric, and a multiplicity-robustness flag

### Requirement: No Clinical Meaning and Production Isolation
The experiment SHALL NOT assign clinical meaning to any code, and SHALL NOT modify production artifacts, the registry, the contract, the API or the frontend.

#### Scenario: Production unchanged after execution
- **WHEN** the experiment has run
- **THEN** the artifact integrity check passes and the contract SHA-256 is unchanged
