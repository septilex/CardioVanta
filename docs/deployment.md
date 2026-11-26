# Deployment & Production Artifacts

## Production Artifacts
The API loads an explicitly versioned model from `artifacts/models/` and verifies its registry metadata and artifact checksums before deserializing/serving it. The current 1.1.1 serving package uses portable JSON model parameters. PostgreSQL and MongoDB are optional for prediction; they support research metadata and anonymous feedback respectively.

## Local Docker development
Docker Compose starts the FastAPI backend, PostgreSQL 16, and MongoDB 7. Create a local-only environment file from the committed placeholders and keep it untracked:

```powershell
Copy-Item .env.docker.example .env.docker
# Replace both placeholder passwords with local values.
docker compose --env-file .env.docker up --build
```

The backend uses Compose service DNS (`postgres`, `mongo`), waits for database health checks, and exposes the model-backed API at `http://localhost:8000/api/v1/health`. It runs as a non-root account. The Docker image contains only the current registered model files needed by the API, not the research data or experiment/report trees. `LLM_ENABLED` is forced to false in Compose and the image; no OpenAI key is supplied. This is a local development topology and does not alter Vercel's architecture.

The `Backend Docker smoke check` GitHub Actions workflow builds but never publishes the image, starts it without database or provider credentials, and polls the health endpoint. PostgreSQL and MongoDB in Compose are available to developers for database feature work; they are not required to pass this image health check.

## Request-time platform status
Open `/platform-status` to see when the FastAPI health endpoint was last checked and whether the backend and registered model package are available. Its App Router page is explicitly dynamic, and the server fetch uses `cache: "no-store"` with a 2.5-second abort bound; refresh the route to demonstrate a request-time result rather than a build-time snapshot. On Vercel it calls the current deployment's own host and existing `/api/*` rewrite; in Compose or self-hosted deployments, set the server-only `CARDIOVANTA_BACKEND_URL`. Internal errors and response bodies are not rendered.

## Scheduled dependency audit
`.github/workflows/scheduled-dependency-audit.yml` runs weekly and can also be started manually. It runs `npm audit` for the frontend and `pip-audit` separately against the root, backend, and API requirements. It uses no application credentials. This job reports known dependency advisories; it does not replace PR verification or audit application logic.

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
