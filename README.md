# CardioVanta

**Project Purpose:** Provide a robust, containerized, leakage-safe ML prediction system for cardiovascular health.

## Project Structure
CardioVanta consists of:
- **ML Pipeline**: A calibrated Logistic Regression ensemble enforcing strict schema constraints and avoiding data leakage.
- **Backend**: A FastAPI inference service serving the model predictions.
- **Frontend**: A Next.js App Router UI providing the assessment interface.

## Local Development & Testing
- **Backend Tests**: Run `pytest backend/tests` (via `.venv311\Scripts\pytest` on Windows)
- **Frontend Tests**: Run `npm run test` inside the `frontend/` directory.
- For convenience, run all tests from the repository root using the provided `test.ps1` script (on Windows) or equivalent runner.

---

## Production Deployment

CardioVanta is production-ready via Docker Compose. The architecture is a multi-container stack where the Next.js frontend interfaces with the FastAPI backend over HTTP.

### Prerequisites
- Docker Engine & Docker Compose (v2+)

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
- **Backend Container (`backend`)**: Port `8000`. Runs the FastAPI app via `uvicorn`. Includes health checks.
- **Frontend Container (`frontend`)**: Port `3000`. Runs the built Next.js application.

### Start the Stack
Build and start the services in detached mode:
```bash
docker compose build
docker compose up -d
```

### Health Check
Verify the backend is healthy:
```bash
curl http://localhost:8000/api/v1/health
```
*(Expected output: `{"status":"ok","service":"CardioVanta"}`)*

### Shutdown
To cleanly stop and remove the containers and default network:
```bash
docker compose down
```
