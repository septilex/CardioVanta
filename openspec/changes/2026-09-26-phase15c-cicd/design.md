# Design: Phase 15C Automated Verification / CI/CD

## Context

CardioVanta consists of a monolithic repository where the root directory serves as the active Next.js application, integrating a FastAPI backend mapped via `api/index.py` for Vercel serverless deployment. The repository includes fully stabilized ML artifacts (`artifacts/model/`), backend tests (`pytest`), drift detection tests, and frontend tests (`jest`). The stale `frontend/` directory is ignored. Development commands currently rely on local Windows environments (e.g. `.venv311\Scripts\pytest`), requiring normalization for a unified Linux CI system. Vercel handles production deployment, while `audit_tests.py` manually verifies live production status.

## Goals / Non-Goals

**Goals:**
- Guarantee backend inference, drift detection, and ML artifact integrity remain intact via automated `pytest` on PRs/main.
- Guarantee frontend form logic, TypeScript compilation, and static build generation via automated Next.js tools.
- Provide a clean separation between pre-merge verification (GH Actions) and deployment (Vercel).
- Utilize standard Linux paths, reproducible environments (Node 20, Python 3.11), and dependency lockfiles.

**Non-Goals:**
- Do NOT introduce Docker, Kubernetes, or alternative CI platforms.
- Do NOT automatically deploy from GitHub Actions (Vercel manages this).
- Do NOT run `audit_tests.py` on PRs (prevents false negatives against live production).
- Do NOT modify or retrain ML models in CI.

## Decisions

1. **Workflow Architecture (`.github/workflows/verify.yml`)**:
   - **Triggers**: `pull_request` (targeting `main`) and `push` (to `main`).
   - **Strategy**: Two parallel jobs (`verify-backend`, `verify-frontend`) on `ubuntu-latest`.
   - *Alternative Considered*: Single sequential job. Rejected to optimize CI execution time by parallelizing Python and Node workflows.

2. **Backend Job Definition (`verify-backend`)**:
   - Standardize to Linux runner.
   - Use `actions/setup-python@v5` targeting Python 3.11.
   - Cache dependencies using `cache: 'pip'`.
   - Commands:
     ```bash
     pip install -r requirements.txt
     pip install pytest pip-audit
     pytest tests/
     pip-audit -r requirements.txt
     ```
   - *Rationale*: Running `pytest tests/` automatically collects and validates the backend logic, model artifact loading, and drift detection scripts (`test_drift_detection.py`), failing if metadata or drift permutations break. `pip-audit` adds lightweight supply-chain security without complex tooling.

3. **Frontend Job Definition (`verify-frontend`)**:
   - Standardize to Linux runner in the repository root.
   - Use `actions/setup-node@v4` targeting Node.js 20.
   - Cache dependencies using `cache: 'npm'`.
   - Commands:
     ```bash
     npm ci
     npx tsc --noEmit
     npm run test -- --passWithNoTests
     npm run build
     npm audit --audit-level=high
     ```
   - *Rationale*: `npm ci` strictly enforces `package-lock.json` reproducibility. `npx tsc --noEmit` and `npm run test` prevent logic/type errors, and `npm run build` strictly checks Vercel serverless generation limits.

4. **Testing Segregation (Post-Deployment vs. Verification)**:
   - `audit_tests.py` explicitly hits `https://cardio-vanta-prod.vercel.app`. It will remain excluded from `verify.yml`. Post-deployment verification will remain manual via local execution (or future webhook design), keeping PR checks isolated from live production traffic.

5. **Dependency Resolution**:
   - The original `requirements.txt` contained Python 3.12-exclusive versions of `contourpy`, `numpy`, `scipy`, and `xgboost`. These are explicitly downgraded to their latest Python 3.11-compatible versions (e.g., `contourpy==1.3.3`) to guarantee clean, reproducible installations on standard `ubuntu-latest` Python 3.11 runners without compromising the integrity of the locked ML models.

## Risks / Trade-offs

- [Risk] Missing exact dependency lockfile for Python (only `requirements.txt` is present, not a hardened `requirements.lock` or `Pipfile.lock`). 
  → **Mitigation**: Existing `requirements.txt` has pinned versions (e.g. `scikit-learn==1.9.1`). We will strictly install via `pip install -r requirements.txt`.
- [Risk] Vercel deploying a broken branch before GitHub Actions catches it. 
  → **Mitigation**: GitHub branch protection rules must be configured manually by repository administrators to require status checks (`verify-backend`, `verify-frontend`) to pass before merging into `main`. Vercel production deployment happens *after* merge to `main`.
- [Risk] PR verification fails because of vulnerabilities triggered in `npm audit` or `pip-audit`.
  → **Mitigation**: Keep thresholds reasonable (e.g., `--audit-level=high` for npm, `--desc` flags) so only severe CVEs block development.

## Migration Plan

1. **Commit Workflow**: Land `.github/workflows/verify.yml` in a PR.
2. **Test CI**: Validate that both jobs pass against the current stabilized `main` branch.
3. **Branch Protection**: Instruct project owner to configure GitHub settings to require `verify-backend` and `verify-frontend` jobs for all PRs to `main`.
