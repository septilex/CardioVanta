# Architecture

## Overview
CardioVanta consists of a frontend interface and a backend prediction API.

### Frontend Architecture
- **Framework:** Next.js 16.3.8 (React 19)
- **Deployment:** Vercel serverless deployment with frontend routing via `vercel.json`

### Backend Architecture
- **Framework:** FastAPI
- **Model Loading:** The backend initializes a dual-model explanation architecture on startup, loading artifacts from the `artifacts/model/` directory into a global state.
- **Inference Engine:** Validates features against `feature_schema.json`, applies preprocessing, predicts using the calibrated ensemble, and explains using the underlying uncalibrated model.
- **Security & Configuration:** Environment variables default to `production`. CORS is restricted to frontend development origins, with credentials disallowed for security. API docs are disabled in production by default.
