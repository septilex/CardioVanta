## 1. CI/CD Workflow Generation

- [x] 1.1 Create `.github/workflows/verify.yml` and define `verify-backend` and `verify-frontend` jobs, verifying the YAML is well-formed.
- [x] 1.2 Implement the `verify-backend` job to setup Python 3.11, install dependencies from `requirements.txt`, run `pytest tests/`, and run `pip-audit`, verifying it executes completely without Windows path assumptions.
- [x] 1.3 Implement the `verify-frontend` job to setup Node.js 24, run `npm ci`, `npx tsc --noEmit`, `npm run test`, `npm run build`, and `npm audit --audit-level=high` at the root Next.js application, verifying all commands are correct.
- [x] 1.4 Add `pull_request` and `push` to `main` triggers, verifying the logic scopes cleanly to branch updates and maintains Vercel's decoupled deployment boundary.
- [x] 1.5 Update `requirements.txt` to resolve Python 3.11 compatibility conflicts by pinning `contourpy==1.3.3`, `numpy==2.4.6`, `scipy==1.17.1`, and `xgboost==3.2.0`.

## 2. Documentation Updates

- [x] 2.1 Update `docs/deployment.md` to document the new GitHub Actions verification steps, branch protection requirements, and the distinct post-deployment execution boundary of `audit_tests.py`, verifying the instructions are clear and accurate.
