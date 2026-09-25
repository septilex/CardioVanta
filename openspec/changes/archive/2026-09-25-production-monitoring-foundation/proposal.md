# Proposal

## Why

### Problem
The current CardioVanta production environment lacks centralized telemetry and observability for inference requests. While errors are generically logged, there is no structured monitoring of successful predictions, request latency, model versioning, threshold application, or out-of-range inputs. This prevents operational oversight, debugging of production validation errors, and future detection of statistical drift.

### Goals
Establish a production monitoring foundation that captures operational and model metadata for each inference request without impacting user latency. Create a structured, Vercel-compatible JSON log stream containing critical execution context to support future drift monitoring (Phase 15B).

### Non-Goals
- No logging of raw patient input payloads (13 cardiovascular features) in standard logs by default, treating them as sensitive.
- No automatic retraining, model replacement, clinical alerting, chatbot, frontend dashboard, or unrelated product features.
- No changes to the model, calibration, threshold policy, prediction response contract, or SHAP mathematics.
- No addition of a separate database (Postgres, etc.) unless strictly required.
- No third-party logging packages (`structlog` or `python-json-logger`) unless standard-library logging is insufficient.
- No deployment in this phase.

## What Changes

- **Add Observability Middleware**: Create a FastAPI middleware to intercept requests, assign request IDs, measure latency, and capture status codes.
- **Implement Exception Handlers**: Capture `RequestValidationError` and `HTTPException` to emit structured logs on failures.
- **Emit Prediction Events**: Output a structured JSON log containing operational and model metadata at the end of the `/predict` endpoint. 
- **Privacy Enforcement**: Ensure the raw 13-feature patient input payload is NOT logged, but out-of-range feature flags are logged.
- **Vercel-Safe Logging Strategy**: Rely on asynchronous Log Shipping via standard `sys.stdout` JSON formatting, which Vercel will drain without penalizing the API response time.
- **Future-Proofing**: Design the schema to be compatible with Phase 15B (drift detection) without locking into KL divergence, supporting future feature-type-specific drift methods.

## Capabilities

### New Capabilities
- `production-monitoring`: Defines the requirements for structured telemetry, event schemas, latency tracking, and privacy constraints for the ML prediction API.

### Modified Capabilities
None.

## Impact

### Architecture & Storage Strategy
The foundation uses standard Python logging formatted as JSON, outputting to `sys.stdout`. Vercel's serverless environment natively captures stdout and ships it asynchronously to configured Log Drains. This avoids the latency overhead and connection pooling complexity of introducing a relational database.

### Failure Behavior
Monitoring must never block or break prediction inference. If the telemetry mechanism fails, the API must still return the prediction response to the user.

### Privacy & Security Constraints
The 13 cardiovascular input features are treated as sensitive health-related data. They are EXCLUDED from the monitoring event schema. No PII, IP addresses, or identifiable user-agent strings will be logged.

### Monitoring Event Schema
```json
{
  "event_type": "prediction_request",
  "timestamp": "2026-09-25T14:30:00Z",
  "request_id": "uuid",
  "endpoint": "/api/v1/predict",
  "metadata": {
    "package_version": "1.0.0",
    "model_type": "Logistic Regression",
    "calibration_method": "sigmoid"
  },
  "status": {
    "status_code": 200,
    "latency_ms": 45
  },
  "outputs": {
    "probability": 0.85,
    "threshold_status": "mathematical_model_operating_point",
    "outside_development_range": false,
    "out_of_range_features": []
  }
}
```
*Note: This schema explicitly excludes the raw inputs to respect privacy constraints, while including model version and probability distributions for future drift detection.*

### Future Compatibility with Phase 15B
Phase 15B (drift detection) will require statistical analysis of inputs. Since raw inputs are not logged by default for privacy, Phase 15B can either use the `probability` distribution for concept drift, or implement a secure, opt-in feature-hashing or differential privacy mechanism. This proposal does not lock into KL divergence.

### Testing Strategy
- Unit tests for the custom JSON log formatter.
- Integration tests verifying the middleware measures latency and catches 422 validation errors.
- Tests ensuring the prediction response remains intact even if logging throws an internal exception.

### Exact Files Expected to Change
- `backend/app/main.py`: Add exception handlers and middleware.
- `backend/app/api/endpoints/predict.py`: Emit the JSON log.
- `backend/app/core/logging.py` (New): Configure standard-library JSON logging.
- `backend/app/api/middleware.py` (New): Implement latency and request ID tracking.
- `tests/test_monitoring.py` (New): Verify schema and privacy constraints.

### Risks/Tradeoffs
- **Tradeoff**: By excluding the raw 13 features for privacy, detecting *covariate drift* (feature distribution changes) in Phase 15B will be more complex and may require a separate secure data vault. We accept this tradeoff to prioritize patient privacy.
- **Risk**: Vercel Log Drains require a third-party integration (e.g., Datadog, Axiom) for long-term retention.

### Acceptance Criteria
1. Successful inference requests emit a single JSON log line to stdout matching the defined schema.
2. Validation errors (422) emit a structured JSON error log.
3. Raw patient features (age, sex, etc.) do NOT appear in the logs.
4. Inference latency increases by < 5ms.
5. No new database dependencies are introduced.
6. The prediction API contract is unmodified.
