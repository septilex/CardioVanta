# Spec Delta

## ADDED Requirements

### Requirement: Pinned, Platform-Supported Python Runtime
The production Python runtime SHALL be pinned to a Vercel-supported version (3.12) in the location the Vercel Python builder reads for the `/api` function, `api/.python-version`. Repository tooling and CI SHALL use the same version. The pinned dependency set SHALL include the model's exact scikit-learn version and its transitive numerical stack.

#### Scenario: Builder version detection
- **WHEN** the Vercel Python builder resolves the function's Python version
- **THEN** it selects 3.12 from `api/.python-version`, not the implicit platform default

#### Scenario: Pins agree with the registered model
- **WHEN** the deployment requirements are inspected
- **THEN** scikit-learn equals the registered model's `runtime.sklearn_version`, and numpy, scipy and threadpoolctl are pinned to the validated versions

### Requirement: Single Verified Deserialization Path
Production code SHALL deserialize model artifacts only through `cardiovanta_ml.registry.loader`, after checksum verification. The legacy `ModelLoader` interface SHALL delegate to the registry and SHALL NOT deserialize artifacts itself.

#### Scenario: Tampered artifact through the legacy interface
- **WHEN** `ModelLoader(...).load_and_validate()` is called on a registered directory whose artifact bytes were modified
- **THEN** it fails with `IntegrityError`, and nothing is deserialized

### Requirement: Explicit Model Pin Without Fallback
The deployed function SHALL serve exactly the model named by `MODEL_ID` and `MODEL_VERSION`, resolved inside the function bundle's registry root.

#### Scenario: Unregistered version requested
- **WHEN** the bundle starts with `MODEL_VERSION` set to an unregistered or non-semantic value
- **THEN** startup fails, and no other model version is served

### Requirement: Enforced CI Checks
CI SHALL fail when any of these production checks fails:
- the generated-contract `--check`;
- artifact integrity;
- wheel build and installed-wheel verification;
- the synthetic backend, registry, contract and deployment suite;
- the frontend type check, tests and build.

Data-dependent research suites SHALL run in a separate job.

#### Scenario: Stale generated contract files
- **WHEN** the generated contract files do not match the canonical contract
- **THEN** the production CI job fails before deployment
