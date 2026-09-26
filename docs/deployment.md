# Deployment & Production Artifacts

## Production Artifacts
The production model bundle is self-contained in the `artifacts/model/` directory. No external databases are required for inference.
- `model.joblib`: The calibrated ensemble model wrapper.
- `explanation_model.joblib`: The underlying uncalibrated Logistic Regression model for SHAP/linear explanations.
- `feature_schema.json`: The authoritative contract for expected feature types, ranges, and allowed categories.
- `metadata.json`: Immutable provenance, configuration, and policy constraints.

## Continuous Integration (CI)
CardioVanta uses GitHub Actions for automated, secretless CI verification before code reaches production.
- **PR & Main Verification:** Every pull request to `main` and push to `main` runs automated Linux (Ubuntu) workflows (`.github/workflows/verify.yml`). This parallelizes Python backend checks (`pytest`, artifact integrity, `pip-audit`) and Node frontend checks (`npm ci`, `tsc`, `jest`, `next build`, `npm audit`).
- **Immutable Artifacts:** The CI workflow executes inference and offline validation solely using the pre-generated artifacts. It never retrains or updates ML models.

## Deployment Strategy
- **Vercel Deployment Boundary:** Vercel automatically deploys the Next.js and serverless FastAPI application upon a successful merge to `main`. Deployments are not triggered or executed by GitHub Actions.
- **Live Production Smoke Testing:** The `audit_tests.py` script tests the live production environment (`https://cardio-vanta-prod.vercel.app`). It is strictly isolated from automated PR verification to prevent false negatives caused by testing existing production against unmerged PR code. It serves as a manual or post-deployment verification boundary.

## Security & Configuration
- **CORS:** Highly restricted. The API strictly limits origins and disallows credentials.
- **Credentials:** No secrets, keys, or credentials exist in the source or artifacts, nor are they used in the CI workflows.
- **Environment:** Defaults to `production` via Pydantic settings. OpenAPI docs (`/docs`) are disabled in production contexts.
- **Reproducibility:** Seed (`42`) and dataset hashes are stored in `metadata.json` for full artifact rebuildability. Dependencies are rigidly bound via `requirements.txt` and `package-lock.json`.
