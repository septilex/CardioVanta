# Proposal: Phase 15C Automated Verification / CI/CD

## Why

CardioVanta currently relies on manual local verification before deployment. While the ML model is fully verified and stable (with a locked 242-dev / 61-test split), any future engineering changes (Next.js updates, API adjustments, dependency bumps) risk introducing regressions if human error skips local tests. An automated Continuous Integration (CI) pipeline on GitHub Actions ensures that the rigorous standards established in prior phases are cryptographically and automatically enforced on every Pull Request and merge to `main`, preventing broken frontend, backend, or ML-serving code from reaching production.

## What Changes

- Introduce GitHub Actions workflow (`verify.yml`) for automated PR and `main` branch verification using Linux (Ubuntu) runners.
- **Frontend Verification**: Automate deterministic dependency installation (`npm ci`), TypeScript compilation (`npx tsc --noEmit`), Jest tests (`npm run test -- --passWithNoTests`), and Next.js production build (`npm run build`) against the active Next.js root application (ignoring the stale `frontend/` directory).
- **Backend Verification**: Automate reproducible Python 3.11 environment setup, dependencies installation (`pip install -r requirements.txt`), and execution of `pytest tests/` (which intrinsically covers backend logic, model loading, artifact integrity, and drift detection logic).
- **Security & Vulnerability Scanning**: Include a lightweight check via `npm audit` and `pip-audit` to prevent introducing supply chain vulnerabilities, without adding heavy infrastructure.
- **No Deployment Interference**: Vercel will continue to handle production deployments seamlessly. CI strictly adds pre-merge verification.
- **Post-Deployment Testing Isolation**: `audit_tests.py` is explicitly excluded from PR blocking workflows because it tests live production (`https://cardio-vanta-prod.vercel.app`). It will be explicitly designated for post-deployment or manual execution.
- **No Training**: CI will strictly verify inference and offline stateless logic; it will NEVER modify or retrain the locked production artifacts in `artifacts/model/`.

## Capabilities

### New Capabilities
None. (This is a pure infrastructure/tooling change. `skip_specs: true` is set in `.openspec.yaml`).

### Modified Capabilities
None.

## Impact

- **Infrastructure**: Adds `.github/workflows/verify.yml` to the repository root.
- **Developer Experience**: PRs will be blocked from merging if they fail type checks, linting, or tests.
- **Security**: Ensures no broken code reaches the `main` branch, protecting the integrity of the locked test set and the production artifact behavior without adding complex external systems (no Docker/K8s).
