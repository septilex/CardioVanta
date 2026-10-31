# Spec Delta

## ADDED Requirements

### Requirement: Explicit Versioned Model Selection
The system SHALL load a model only by an explicit model ID and exact semantic version from `<registry root>/models/<model_id>/<model_version>/`. It SHALL NOT scan for, or fall back to, a "latest" or default version. The registry root SHALL be an explicit absolute path.

#### Scenario: Unknown or malformed version
- **WHEN** a version that is not registered (for example `9.9.9`), or a non-semantic version (for example `latest` or `../1.0.0`), is requested
- **THEN** loading fails with `ModelNotRegisteredError`, and no artifact is read

### Requirement: Integrity Verification Before Deserialization
The registry SHALL verify that the checksum manifest matches the SHA-256 pinned in the registry metadata, that the manifest lists exactly the declared artifacts, and that every artifact matches its SHA-256. It SHALL do this before deserializing any artifact. All artifact paths SHALL resolve inside the registry root and the declared artifact directory.

#### Scenario: Modified artifact
- **WHEN** any registered artifact's bytes differ from its manifest entry
- **THEN** loading fails with `IntegrityError` and no model is deserialized

#### Scenario: Path traversal
- **WHEN** metadata declares an absolute path, a `..` segment or a nested file name
- **THEN** loading fails with `ArtifactPathError`

### Requirement: Explicit Outcome Mapping and Contract Compatibility
Each registered model SHALL declare its class labels, the clinical meaning of each label, and the disease-present label, with no implicit fallback. The registry SHALL reject a model when:
- its declared feature contract name, version or SHA-256 differs from the bundled contract;
- its feature order differs from the contract order;
- its outcome is not the contract outcome;
- its label mapping contradicts the contract's model-label record.

The registry SHALL also reject an interim legacy mapping that the contract does not record.

#### Scenario: Legacy model
- **WHEN** `cardiovanta-lr13@1.0.0` is loaded
- **THEN** classes are `[0, 1]`, label 0 is disease present, and the API probability equals `predict_proba[:, 0]`, which is P(disease present)

#### Scenario: Contradictory mapping
- **WHEN** metadata declares disease label 1 for `cardiovanta-lr13@1.0.0`, even with internally consistent class semantics
- **THEN** loading fails with `OutcomeMappingError`, because the contract records label 0

### Requirement: Post-Load Validation and Single Load
After deserialization the registry SHALL verify:
- both models' class labels and feature names against the metadata and contract;
- the input schema;
- the package metadata version;
- that the explanation model and SHAP background are associated with the same registered model.

A model version SHALL be deserialized at most once per process.

#### Scenario: Repeated startup
- **WHEN** the API starts twice in the same process
- **THEN** the same loaded model object is reused, and each joblib artifact is deserialized exactly once

### Requirement: Behaviour-Preserving Refactor
Moving inference into `cardiovanta_ml` SHALL NOT change any `/api/v1/predict` request or response.

#### Scenario: Pre-refactor parity
- **WHEN** the synthetic snapshot profiles are submitted with and without a threshold
- **THEN** every response equals the pre-R2 snapshot, including P(disease present) of 0.9858 for the high-risk profile and 0.0161 for the low-risk profile
