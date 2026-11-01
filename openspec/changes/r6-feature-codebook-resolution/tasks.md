# Tasks

## 1. Evidence collection
- [x] 1.1 Inventory the provenance sources: the codebook, contract, Phase 17 module and report, profiling report, the UCI page (loaded) and the Kaggle page (404). Confirm that no canonical Cleveland file is present locally.

## 2. Implementation
- [x] 2.1 Implement `experiments/r6_codebook_evidence.py`: a deterministic evidence record and the contract-consistency check.
- [x] 2.2 Add `tests/test_r6_codebook_resolution.py`, covering verified mappings, unresolved mappings, the evidence/contract consistency and the absence of dataset access. Result: 22/22 pass.

## 3. Verification
- [x] 3.1 Run the builder twice. Acceptance: identical output. Result: byte-identical (`ed4c17b1…`).
- [x] 3.2 Verify artifact integrity. Acceptance: the integrity check passes and the contract SHA-256 is unchanged.

## 4. Reporting
- [x] 4.1 Write `reports/r6_feature_codebook_resolution.md`.

## Outcome
No mapping could be verified: there is no E1 or E2 evidence within the constraints. `slope` 0–2 and `thal` 1–3 remain `unverified`, and `ca = 4` and `thal = 0` remain `undefined_in_codebook`, with no clinical meaning assigned. The resolution options are in the report, §8.
