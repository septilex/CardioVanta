# Spec Delta

## ADDED Requirements

### Requirement: Synthetic-Only Explanation Stability Measurement
The R5 experiment SHALL evaluate the frozen production model on deterministic synthetic profiles drawn from the canonical 13-feature contract. It SHALL perturb one feature at a time within accepted constraints, and SHALL NOT load any dataset, locked observation or external cohort.

#### Scenario: No data loaded
- **WHEN** the experiment runs
- **THEN** every profile is generated from the contract, and no dataset file is opened

### Requirement: Separate Continuous and Categorical Reporting Without Clinical Meaning
The experiment SHALL report continuous and categorical perturbations separately. It SHALL identify categorical codes only by code number and contract verification level, without assigning clinical meaning.

#### Scenario: Unverified codes
- **WHEN** a perturbation involves a `slope` or `thal` code, or `ca=4`
- **THEN** the results label it with its verification level, and no clinical label is attached

### Requirement: Production Isolation
The experiment SHALL load the production model only through the SHA-256-verified registry, read-only, and SHALL NOT modify production artifacts, the registry, the contract, the API or the frontend.

#### Scenario: Integrity after execution
- **WHEN** the experiment has run
- **THEN** the artifact integrity check passes
