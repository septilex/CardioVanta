# Proposal: R3 — Deployment Reproducibility, CI & Model-Loading Hardening

## Why
- All tests ran on Python 3.11, but Vercel supports only 3.12 (default), 3.13 and 3.14. The deployed function therefore ran on an implicit, untested runtime.
- `api/requirements.txt` left numpy and scipy unpinned. A fresh resolve picks numpy 2.5.4 and scipy 1.18.1, not the 2.4.6 and 1.17.1 that were validated.
- The deprecated legacy `ModelLoader` could deserialize artifacts without checksum verification.
- CI did not build or verify the package wheel, did not run the contract `--check`, and mixed data-dependent research suites with production checks.

## What Changes
- **Runtime:** pin Python 3.12. `api/.python-version` is the file Vercel's builder reads; it was verified with a local `vercel build`, and a root-level file alone is ignored for `/api` functions. A root `.python-version` is kept for CI and tooling. `requires-python` becomes `>=3.11,<3.13`, with 3.11 kept for local development.
- **Dependencies:** pin the model's transitive numerical stack (numpy 2.4.6, scipy 1.17.1, threadpoolctl 3.7.0) in `api/requirements.txt`, `backend/requirements.txt` and the package metadata. No new packages are added.
- **Legacy loader:** `ModelLoader` becomes an adapter that delegates to the verified registry. It keeps its interface and pre-load checks, and no longer calls `joblib.load` itself.
- **Wheel verification:** add `scripts/ci/verify_wheel_install.py`, which checks an installed wheel in isolated mode from outside the repository.
- **CI:** restructure `.github/workflows/verify.yml`.
  - Production job (3.12, from `.python-version`): documented install, contract `--check`, artifact integrity, wheel build and clean-venv verification, the full synthetic suite with install tests, and pip-audit.
  - Separate required `research-data-tests` job (3.11).
  - The frontend job is unchanged. The deploy job needs all three.
- **Configuration:** `.env.example` documents the explicit `MODEL_ID` and `MODEL_VERSION` pin. `.gitignore` and `.vercelignore` ignore local `vercel build` side effects (`_uv/`).
- **Tests:** `backend/tests/test_r3_deployment.py` covers the runtime pin, dependency pins, packaging, bundle registry resolution, no version fallback, centralized deserialization, the legacy adapter, and CI enforcement.

## Non-goals
- No model, artifact, contract, API, outcome-orientation or research change.
- No deployment.
- No `vercel link` or `vercel pull` against the real project.
