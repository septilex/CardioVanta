# Tasks

## 1. Contract
- [x] 1.1 Create `contracts/feature_schema.v2.json` with:
  - outcome semantics;
  - separate model label mappings;
  - all 13 features: types, units, accepted values, development ranges, and options with verification status and evidence.

  Acceptance: the inventory, mapping and outcome tests in `backend/tests/test_r1_feature_contract.py` pass.

## 2. Generator
- [x] 2.1 Implement `contracts/codegen/generate.py` using the standard library only, with strict validation, deterministic output and `--check`.

  Acceptance: the determinism, stale-detection, malformed-JSON and unsupported-definition tests pass, and `python contracts/codegen/generate.py --check` exits 0.

## 3. Backend integration
- [x] 3.1 Generate `backend/app/schemas/generated_features.py`, and make `PredictRequest` and `FeatureContributions` inherit the generated bases. Source the outcome and legacy-mapping constants in `src/inference/outcome.py` from the generated module.

  Acceptance: the request-validation equivalence matrix, the JSON non-finite tests and the full backend suite pass.

## 4. Frontend integration
- [x] 4.1 Generate `src/types/generated-features.ts`, re-export it from `src/types/index.ts`, and render the assessment page's categorical selects from the generated options with unchanged visible text.

  Acceptance: the generated-TypeScript and frontend-reuse tests pass.

  Not run locally: TypeScript compilation and Jest (no `node_modules`).

## 5. Regression
- [x] 5.1 Keep the R0.3 disease-positive semantics intact.

  Acceptance: `backend/tests/test_r0_outcome_semantics.py` passes in full.
