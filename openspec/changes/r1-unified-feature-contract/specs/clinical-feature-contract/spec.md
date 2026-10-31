# Spec Delta

## ADDED Requirements

### Requirement: Single Versioned Clinical Feature and Outcome Contract
The system SHALL define the production clinical input schema and outcome semantics in exactly one versioned, machine-readable file, `contracts/feature_schema.v2.json`. Backend Pydantic definitions and frontend TypeScript definitions of the clinical features SHALL be generated from it and MUST NOT be hand-maintained.

#### Scenario: Generated definitions are current
- **WHEN** `python contracts/codegen/generate.py --check` runs
- **THEN** it exits 0 if and only if the generated Python and TypeScript files equal the output rendered from the current contract
- **THEN** otherwise it exits non-zero and names the stale files

#### Scenario: Malformed or unsupported contract
- **WHEN** the contract is malformed JSON or contains unsupported keys, types or inconsistent definitions
- **THEN** generation fails with a clear error and writes no output

### Requirement: Disease-Positive Outcome Semantics
The contract SHALL define the clinical outcome as significant obstructive coronary artery disease present, meaning greater than 50% diameter stenosis in at least one major coronary vessel. Positive value 1 SHALL mean disease present, and the API probability SHALL be P(disease present). Artifact-specific model label mappings SHALL be recorded separately from the clinical outcome definition.

#### Scenario: Legacy model mapping kept separate
- **WHEN** the legacy package 1.0.0, trained on an inverted target, is served
- **THEN** its disease label (0) is read from the contract's `model_label_mappings`, not from the outcome definition
- **THEN** the API still reports P(disease present), with class 1 meaning disease present

### Requirement: Verified and Unverified Code Mappings
Every accepted categorical input code SHALL carry a verification status. Codes whose clinical meaning is not established SHALL have no clinical meaning asserted. They SHALL be displayed as unverified or as undefined codes, never as fabricated clinical categories.

#### Scenario: Unverified slope and thal codes
- **WHEN** the contract defines `slope` codes 0-2 and `thal` codes 1-3
- **THEN** each is marked `unverified`, with `clinical_meaning` null

#### Scenario: Codes undefined in the UCI codebook
- **WHEN** the contract defines `ca` code 4 and `thal` code 0
- **THEN** each is marked `undefined_in_codebook`, with `clinical_meaning` null
- **THEN** each is displayed neutrally as a code that is not in the UCI codebook

### Requirement: Backward-Compatible Request Validation
Integrating the generated definitions SHALL NOT change `/api/v1/predict` request validation. The following SHALL stay the same:
- the 13 fields, with the same names and order;
- rejection of unexpected fields;
- rejection of NaN and infinity;
- the accepted categorical codes.

#### Scenario: Equivalence with the pre-contract schema
- **WHEN** a matrix of synthetic valid and invalid payloads is validated by both the generated request model and a frozen copy of the pre-R1 model
- **THEN** both accept and reject exactly the same payloads
- **THEN** accepted payloads produce identical validated values, and rejected payloads produce identical error types
