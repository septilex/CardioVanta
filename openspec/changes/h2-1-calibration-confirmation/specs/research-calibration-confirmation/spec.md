# Spec Delta

## ADDED Requirements

### Requirement: Prospective Signed-Slope Confirmation
The H2.1 experiment SHALL test the paired signed difference in calibration slope between pooled OOF calibration and the production recipe. It SHALL use the expected direction, confidence intervals, multiplicity adjustment and acceptance criteria fixed in `design.md` before execution, and seeds disjoint from H2.

#### Scenario: Verdict
- **WHEN** the experiment completes
- **THEN** the results record whether each pre-registered acceptance criterion held, and the overall confirmed or not-confirmed verdict

### Requirement: Development-Only, Leakage-Free Evaluation
The experiment SHALL fit models and calibration only on the 242 Cleveland development rows, SHALL parse no locked-row line, and SHALL fit preprocessing, tuning and calibration only within training partitions.

#### Scenario: Locked rows
- **WHEN** development data is loaded
- **THEN** exactly 242 rows are returned and no locked-row line is parsed

### Requirement: External Cohorts Excluded Without Invented Mappings
The experiment SHALL NOT parse or evaluate the Hungary or Long Beach VA cohorts, because their feature mappings are incompatible with the production 13-feature recipe. It SHALL record the documented reasons and the Phase 17 reuse disclosure in its results.

#### Scenario: Exclusion recorded
- **WHEN** the results are written
- **THEN** they state that the external evaluation was not performed, why, and that those cohorts were previously used in Phase 17

### Requirement: Production Isolation
The experiment SHALL NOT read or write production model artifacts, the registry or the API, beyond read-only feature definitions and provenance hashes.

#### Scenario: Production unchanged
- **WHEN** the experiment has run
- **THEN** the production artifact checksums are unchanged
