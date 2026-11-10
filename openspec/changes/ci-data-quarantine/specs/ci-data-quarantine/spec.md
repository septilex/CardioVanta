# Spec Delta

## ADDED Requirements

### Requirement: Quarantined Default CI
Default CI verification jobs SHALL NOT have the locked Cleveland source, development indices, external cohort files or locked-derived research outputs in their checkout. They SHALL run every Python step after setup under a runtime guard that refuses and logs access to those files and writes to research results, artifacts, the contract and data.

#### Scenario: Attempted access fails the job
- **WHEN** any Python process in a quarantined job attempts to open a quarantined file, even if the error is caught
- **THEN** the attempt is refused, logged, and the job fails at the clean-log assertion

### Requirement: Explicitly Classified Tests
CI SHALL run test modules only by explicit classification. Every test module SHALL be classified as `ci_safe`, `ci_safe_research_deps` or `research_data`, and `research_data` modules SHALL NOT be run in CI.

#### Scenario: New unclassified test
- **WHEN** a new `test_*.py` module is added without a classification
- **THEN** the classification check fails CI

### Requirement: Static Data-Access Guard
Every Python file that directly references quarantined data SHALL be registered with a role. Unregistered references SHALL fail CI.

#### Scenario: Unauthorized reference
- **WHEN** a file introduces a literal naming `heart.csv` (or another quarantined resource) without registration
- **THEN** the static guard reports it as unauthorized and CI fails

### Requirement: Safe Checks Preserved
The quarantine SHALL keep the existing checks enabled: backend synthetic tests, contract generation, artifact integrity, package and wheel verification, TypeScript, Jest, the Next.js build, and dependency audits.

#### Scenario: Safe checks still run
- **WHEN** the workflow runs on a pull request
- **THEN** all of these checks execute inside quarantined jobs
