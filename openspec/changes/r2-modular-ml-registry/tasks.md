# Tasks

## 1. Package
- [x] 1.1 Create the installable `cardiovanta_ml` package with `pyproject.toml`, declared runtime dependencies, a `test` extra and `py.typed`, and no FastAPI or Next.js imports. Acceptance:
  - `pip install "./cardiovanta_ml[test]"` succeeds in a fresh Python 3.11 venv;
  - the install test passes, and resources load from the installed copy;
  - the AST import scan and the FastAPI-blocked subprocess test pass.
- [x] 1.2 Move the canonical contract into `cardiovanta_ml/contracts/` byte-identically (SHA-256 `50249533…`, contract hash `ec8918e7…` unchanged), and repoint the generator outputs. Acceptance: `python contracts/codegen/generate.py --check` exits 0, and the R1 suite passes.

## 2. Registry
- [x] 2.1 Implement the integrity, metadata, loader and exceptions modules: explicit ID and version, SHA-256 verification before deserialization, strict validation, post-load checks, and a single load. Acceptance: all registry tests in `backend/tests/test_r2_registry.py` pass, including the rejection cases:
  - selection and unknown or invalid versions;
  - metadata, outcome mapping and integrity;
  - path traversal, contract mismatch and class mismatch;
  - single load.
- [x] 2.2 Register `cardiovanta-lr13@1.0.0` (`metadata.json`, `checksums.sha256`, `model_card.md`), referencing the unmodified `artifacts/model/`. Acceptance: the manifest equals the original SHA-256 values and `configs/artifact_hashes.json`, and the model-card content test passes.

## 3. Inference and integration
- [x] 3.1 Port the inference, outcome and explanation code into the package unchanged. Make FastAPI startup load through the registry once, and keep compatibility wrappers. Acceptance:
  - 8/8 full API responses equal the pre-R2 snapshot;
  - the golden values are 0.9858 and 0.0161;
  - all pre-existing backend, R0.3 and R1 tests pass.
- [x] 3.2 Ship the package in the Vercel function (`includeFiles`). Acceptance: the bundle-simulation test serves a 200 response with P = 0.9858.

## 4. Verification
- [x] 4.1 Frontend: `npm ci` from the existing lockfile (package.json and package-lock.json unchanged), then `tsc --noEmit`, Jest and `next build`. Acceptance: all three succeed.
