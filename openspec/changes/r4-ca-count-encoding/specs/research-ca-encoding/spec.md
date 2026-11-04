# Spec Delta

## ADDED Requirements

### Requirement: Leakage-Free Development-Only Evaluation
The R4 experiment SHALL use only the 242 Cleveland development rows, and SHALL parse only header and development-row lines of the raw file. All preprocessing, hyperparameter tuning and calibration SHALL be fitted inside training folds of duplicate-aware cross-validation.

#### Scenario: Locked rows are never parsed
- **WHEN** the experiment loads the development data
- **THEN** lines for non-development indices are discarded without being parsed, and exactly 242 rows are returned

### Requirement: Pre-Registered Comparison Against the Production Recipe
The experiment SHALL compare the production preprocessing recipe with a candidate that changes only the encoding of `ca`. It SHALL use identical outer splits and seeds for both arms, and SHALL report its verdict using the decision rule fixed in the design before execution.

#### Scenario: Verdict reporting
- **WHEN** the experiment completes
- **THEN** the results record the paired bootstrap intervals and whether H1 was supported under the pre-registered rule

### Requirement: Production Isolation
The experiment SHALL NOT read or write production model artifacts, registry entries or the clinical contract. Its only output SHALL be its research results file.

#### Scenario: Production unchanged
- **WHEN** the experiment has run
- **THEN** the production artifact checksums are unchanged
