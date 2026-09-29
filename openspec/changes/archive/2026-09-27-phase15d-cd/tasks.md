# Tasks: Phase 15D - Automated Continuous Delivery

## 1. Configuration & Secrets
- [x] Vercel runner configuration: Add `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` as non-secret GitHub Variables.
- [x] Secret/variable configuration: Add `VERCEL_TOKEN` as a GitHub Environment Secret bound to the `production` environment.

## 2. Script Compatibility (audit_tests.py)
- [x] Dynamic smoke tests: Modify `audit_tests.py` to optionally consume `CARDIO_VANTA_AUDIT_URL` from the environment, falling back to the production alias for backward compatibility.
- [x] Verify no clinical telemetry is logged during tests.

## 3. CI/CD Workflow (.github/workflows/verify.yml)
- [x] Permissions: Add `permissions: contents: read` to the workflow.
- [x] Security: Add a `deploy` job using `environment: production` and gated by `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`.
- [x] Concurrency: Add `concurrency: production-delivery` to serialize deployments.
- [x] Deployment: Configure the runner with `VERCEL_ORG_ID`/`VERCEL_PROJECT_ID` and execute `npx vercel --prod --yes --token=${{ secrets.VERCEL_TOKEN }}`.
- [x] Deployment provenance: Parse the unique deployment URL from stdout, explicitly log it alongside `github.sha`, and save it as a job output.

## 4. Post-Deployment Smoke Tests
- [x] Minimal Environment: Configure the `verify-production` job to install only Python 3.11 and `requests` (bypassing the ML stack).
- [x] Unique URL Verification: Run `audit_tests.py` against the unique deployment URL using `CARDIO_VANTA_AUDIT_URL`.
- [x] Production alias verification: Run `audit_tests.py` against the production alias.
- [x] Failure handling: Ensure failures halt the workflow without attempting automated reversals.

## 5. Finalization
- [x] Documentation (docs/deployment.md): Update documentation outlining the automated process and manual rollback semantics.
- [x] Local verification: Test `audit_tests.py` locally.
- [x] Actual GitHub Actions verification: Observe a successful run in the GitHub UI.
- [x] Actual production verification: Confirm Vercel accurately reflects the newly pushed commit.
- [x] Final OpenSpec validation: Run `openspec validate --all` and update task statuses in `openspec/changes/2026-09-27-phase15d-cd/tasks.md` before archiving.
