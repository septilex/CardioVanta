# Spec Delta

## ADDED Requirements

### Requirement: Evidence-Graded Codebook Mappings
Every training-encoding code of `slope`, `thal` and `ca` SHALL have an evidence record that distinguishes the canonical UCI source code from the transformed production code. Each evidence item SHALL carry an evidence level (E1–E4). A code's verification status SHALL change only on E1 (patient-matched) or E2 (primary-source transformation) evidence.

#### Scenario: No qualifying evidence
- **WHEN** only codebook definitions of canonical codes (E3) or secondary claims (E4) are available for a code
- **THEN** the code keeps its existing `unverified` or `undefined_in_codebook` status, and no clinical meaning is assigned

### Requirement: No Inferred Meanings
Mappings SHALL NOT be inferred from model coefficients, feature importance or frequency distributions. Such information MAY be recorded only as a labelled hypothesis.

#### Scenario: Hypotheses are labelled
- **WHEN** a secondary claim about a code exists (for example, that `ca = 4` encodes a missing value)
- **THEN** it is recorded under `hypotheses_not_evidence` and does not affect the status

### Requirement: Contract and Production Unchanged
The R6 work SHALL NOT modify the clinical contract, production artifacts, the registry, the API or the frontend, and SHALL NOT parse any `heart.csv` row or locked observation.

#### Scenario: Consistency with the contract
- **WHEN** the evidence record is generated
- **THEN** each code's resolved status equals its status in the unchanged contract, and the contract SHA-256 is unchanged
