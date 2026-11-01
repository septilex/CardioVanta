# Spec Delta

## ADDED Requirements

### Requirement: Leakage-Free Calibration Comparison
The H2 experiment SHALL use only the 242 Cleveland development rows, parsing only their lines. It SHALL evaluate all four arms on identical outer splits. It SHALL fit preprocessing, regularisation tuning and sigmoid calibration only within training data, so that calibration uses out-of-fold predictions from the outer-training partition and never outer-test labels.

#### Scenario: Calibration never sees outer-test labels
- **WHEN** a model is evaluated on an outer test fold
- **THEN** its calibrator was fitted only on decision values and labels from that fold's outer-training partition

### Requirement: Pre-Registered Verdict
The experiment SHALL report each arm's verdict against the production recipe using the decision rule fixed in `design.md` before execution, together with paired 95% confidence intervals and repeat-level results.

#### Scenario: Reporting
- **WHEN** the experiment completes
- **THEN** the results record per-arm paired bootstrap intervals, per-repeat differences, Bonferroni sensitivity intervals and the per-arm verdict

### Requirement: Production Isolation
The experiment SHALL NOT read or write production model artifacts, the registry or the clinical contract beyond read-only feature definitions and provenance hashes.

#### Scenario: Production unchanged after execution
- **WHEN** the experiment has run
- **THEN** the production artifact checksums are unchanged
