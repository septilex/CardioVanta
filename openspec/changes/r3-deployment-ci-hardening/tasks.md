# Tasks

## 1. Runtime and dependencies
- [x] 1.1 Verify the Vercel-supported Python versions and select 3.12. Add `.python-version` at the root and in `api/`, and set `requires-python = ">=3.11,<3.13"`.
  - Acceptance: a local `vercel build` reports "Using Python 3.12 from api\.python-version", and the runtime-pin tests pass.
- [x] 1.2 Pin numpy 2.4.6, scipy 1.17.1 and threadpoolctl 3.7.0 in `api/requirements.txt`, `backend/requirements.txt` and the package metadata.
  - Acceptance: a clean 3.12 install resolves exactly these versions, and the dependency-pin tests pass.

## 2. Package distribution
- [x] 2.1 Add `scripts/ci/verify_wheel_install.py`. Build the wheel with 3.12, install it into a clean 3.12 venv, and verify in isolated mode from outside the repository.
  - Acceptance: all 14 checks pass (installed copy, contract hash consistency across bundle, generated module and registry, integrity re-verification, golden values, thresholds, explanation direction, no FastAPI, working-directory independence).

## 3. Centralized model loading
- [x] 3.1 Make the legacy `ModelLoader` delegate to the verified registry, with no direct deserialization.
  - Acceptance: the AST scan finds `joblib.load` only in `registry/loader.py`; the tampered-artifact, unregistered-directory and identity tests pass; the backend never imports the legacy adapter; `test_stage1` and R0 tests pass unchanged.

## 4. CI
- [x] 4.1 Restructure `verify.yml` into:
  - a production job on 3.12 (install, `--check`, integrity, wheel build and verification, synthetic suite with install tests, pip-audit);
  - a separate required research job on 3.11;
  - the unchanged frontend job;
  - a deploy job that needs all three.

  Acceptance: the workflow YAML parses and the CI-enforcement tests pass. The workflow itself was not executed on GitHub in this session.

## 5. Verification
- [x] 5.1 Run the synthetic suite on 3.12 and 3.11. Acceptance: 518 passed on each, 0 failed, 0 skipped.
- [x] 5.2 Run the frontend checks after `npm ci` from the existing lockfile. Acceptance: tsc, Jest 13/13 and `next build` all succeed, and `package.json` and `package-lock.json` are unchanged.
- [ ] 5.3 Complete a Linux `vercel build` with the real project settings.
  - Not done (R3.1). It needs GitHub Actions execution and access to the `VERCEL_TOKEN` secret and the `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID` variables.
  - The remote workflow has no non-deploying, dispatchable job, and pushing or committing was not authorised.
- [x] 5.4 Prepare the non-deploying Linux build job and bundle inspector (R3.1).
  - `.github/workflows/vercel-linux-build.yml`: pinned `vercel@59.26.0`, runs `vercel pull --environment=preview` and `vercel build`, with no deploy step.
  - `scripts/ci/inspect_vercel_bundle.py`: checks the detected Python version and requirements file, measures size and the largest packages, checks the required resources are present, loads `cardiovanta-lr13@1.0.0`, and confirms there is no fallback.
  - Acceptance: the YAML parses and the workflow-safety test passes. The job has never run.
