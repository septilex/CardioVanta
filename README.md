# CardioVanta

**Project Purpose:** Provide a robust, containerized, leakage-safe ML prediction system for cardiovascular health.

## Project Structure
CardioVanta consists of:
- **ML Pipeline**: A calibrated Logistic Regression ensemble enforcing strict schema constraints and avoiding data leakage.
- **Backend**: A FastAPI inference service serving the model predictions.
- **Frontend**: A Next.js App Router UI providing the assessment interface.

## Local Development & Testing
- **Backend Tests**: Run `pytest tests/` and `pytest backend/tests/` (via `.venv311\Scripts\pytest` on Windows)
- **Frontend Tests**: Run `npm run test` in the repository root.
- **Typecheck**: Run `npm run typecheck`
- **Linting**: Run `npx eslint .`
- **OpenSpec Validation**: Run `npx openspec validate --all`

---

## Production Deployment

CardioVanta is deployed via Vercel serverless functions. The architecture is a monolithic repository where the Next.js App Router interfaces with the FastAPI backend mapped to `api/index.py`.

### Prerequisites
- Node.js (v24)
- Python (v3.11)

### Environment Variables
For production deployment, create a `.env` file at the repository root.

```env
# Backend Settings
ENVIRONMENT=production
CORS_ORIGINS=["https://your-frontend-domain.com"]

# Frontend Settings
NEXT_PUBLIC_API_BASE_URL=https://api.your-backend-domain.com
```
*Note: If testing locally, you can omit `NEXT_PUBLIC_API_BASE_URL` to let the frontend default to `http://localhost:8000`, and set `CORS_ORIGINS=["http://localhost:3000"]`.*

### Deployment Architecture
- **Backend**: FastAPI serverless function configured in `vercel.json`.
- **Frontend**: Next.js App Router statically compiled and served via Vercel.

### Continuous Integration (CI)
Automated Linux (Ubuntu) workflows (`.github/workflows/verify.yml`) run on every push and pull request to `main`. The pipeline enforces:
- `pip-audit` and `npm audit --audit-level=critical` for security dependency checks.
- Comprehensive `pytest` (backend and ML) and `jest` (frontend) test suites.
- Strict ML artifact integrity via `verify_artifact_integrity.py`.
- Automated deployment to Vercel upon successful verification.
