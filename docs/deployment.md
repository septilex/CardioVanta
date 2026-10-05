# Deployment & Production Artifacts

## Production Artifacts
The production model bundle is self-contained in the `artifacts/model/` directory. No external databases are required for inference.
- `model.joblib`: The calibrated ensemble model wrapper.
- `explanation_model.joblib`: The underlying uncalibrated Logistic Regression model for SHAP/linear explanations.
- `feature_schema.json`: The authoritative contract for expected feature types, ranges, and allowed categories.
- `metadata.json`: Immutable provenance, configuration, and policy constraints.

## Continuous Integration (CI)
CardioVanta uses GitHub Actions for automated, secretless CI verification before code reaches production.
- **PR & Main Verification:** Every pull request to `main` and push to `main` runs automated Linux (Ubuntu) workflows (`.github/workflows/verify.yml`). This parallelizes Python backend checks (`pytest`, artifact integrity, `pip-audit`) and Node frontend checks (`npm ci`, `tsc`, `jest`, `next build`, `npm audit --audit-level=critical`). The critical audit level is explicitly set as the project's security policy to gracefully handle unfixable high-severity transitives (e.g. `braces`) without failing the CI, whilst strictly blocking critical vulnerabilities.
- **Immutable Artifacts:** The CI workflow executes inference and offline validation solely using the pre-generated artifacts. It never retrains or updates ML models.

## Continuous Delivery (CD) & Smoke Testing
- **Automatic Production Delivery:** Upon a successful push/merge to `main`, and only after CI verification passes, the workflow automatically deploys to Vercel using the `deploy` job. This requires the `VERCEL_TOKEN` GitHub Environment Secret (bound to `production`), alongside `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` repository variables.
- **Deployment Provenance:** The deploy job explicitly maps the triggering `github.sha` to the newly provisioned Vercel deployment URL, outputting this association to the workflow logs.
- **Post-Deployment Smoke Tests:** Immediately following deployment, the `verify-production` job runs `audit_tests.py`. It first targets the unique deployment URL to verify the application code, and then targets the production alias (`https://cardio-vanta-prod.vercel.app`) to ensure proper Vercel routing.
- **Failure Handling:** There are no automatic rollbacks. If deployment fails, existing production is untouched. If deployment succeeds but the URL smoke fails, manual recovery (`vercel rollback`) is required. If the URL passes but the alias is stale, manual Dashboard intervention is required.
- **Manual Fallback:** If GitHub Actions CD is unavailable, administrators can manually run `npx vercel --prod` locally.

## Security & Configuration
- **CORS:** Highly restricted. The API strictly limits origins and disallows credentials.
- **Credentials:** No secrets exist in the source. `VERCEL_TOKEN` is strictly isolated to the `production` environment and blocked from PR execution.
- **Environment:** Defaults to `production` via Pydantic settings. OpenAPI docs (`/docs`) are disabled in production contexts.
- **Reproducibility:** Seed (`42`) and dataset hashes are stored in `metadata.json` for full artifact rebuildability. Dependencies are rigidly bound via `requirements.txt` and `package-lock.json`.
