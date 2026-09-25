# Design

## Context

The current Vercel deployment of CardioVanta executes the FastAPI application in a serverless environment (`api/index.py`). See `proposal.md` for motivation. The primary constraint is Vercel's execution model: once the HTTP response is sent, the microVM is frozen. Background tasks (like pushing to a database or asynchronous I/O loops) can be suspended or killed, making traditional async telemetry unreliable unless using a fully edge-compatible architecture or synchronous stdout logs.

## Goals / Non-Goals

**Goals:**
- Design a lightweight, zero-dependency logging approach that survives Vercel's execution freeze.
- Accurately measure prediction latency without altering the core inference code in `src/inference/`.
- Ensure schema validation failures (422s) are properly intercepted and logged.

**Non-Goals:**
- Setting up the downstream Log Drain provider (Axiom, Datadog) is out of scope for this code change (handled via Vercel dashboard).
- Implementing the statistical drift monitoring (Phase 15B) algorithms.
- Changing the Pydantic schemas to ingest new fields.

## Decisions

### 1. Telemetry Mechanism: Stdout JSON Logging
- **Decision**: Use standard Python `logging` with a custom `logging.Formatter` to output single-line JSON strings to `sys.stdout`.
- **Rationale**: Vercel natively captures stdout and ships it to configured Log Drains asynchronously *outside* of the function's execution time. This avoids adding database connection latency to the user response.
- **Alternatives Considered**: 
  - *FastAPI BackgroundTasks*: Rejected because Vercel may freeze the instance before the background task completes the network request.
  - *External Database (Postgres)*: Rejected as it introduces connection pooling complexity and latency, which violates the constraint to not add a database unless necessary.

### 2. Request Interception: FastAPI Middleware vs Dependency Injection
- **Decision**: Implement a custom `BaseHTTPMiddleware` to track latency and generate a unique `request_id`.
- **Rationale**: Middleware intercepts every request, including those that fail early due to 404s or 422s. It allows us to start a timer before routing and stop it after the response is generated.
- **Alternatives Considered**: 
  - *FastAPI Dependencies*: Good for the `/predict` endpoint but misses early validation failures.

### 3. Exception Handling: Custom Exception Handlers
- **Decision**: Override FastAPI's default `RequestValidationError` handler and the generic `HTTPException` handler in `main.py` to emit the JSON error log before returning the response.
- **Rationale**: Validation errors currently bypass the endpoint logic. To log them, we must catch them at the application level.

### 4. Logging Location: Endpoint vs Middleware
- **Decision**: The final successful prediction event (with model metadata, probabilities, and out-of-range flags) will be logged inside the `predict_endpoint` in `backend/app/api/endpoints/predict.py`.
- **Rationale**: The middleware does not have easy access to the parsed Pydantic response body without consuming the response stream (which is inefficient). Logging at the end of the endpoint function gives direct access to the `PredictResponse` object.

## Risks / Trade-offs

- **[Risk] Log Size Limits**: Vercel limits stdout log lines to 4KB. 
  - **Mitigation**: By excluding the raw 13 features, our JSON payload is extremely small (<1KB) and well within limits.
- **[Risk] Unhandled Exceptions**: If the inference engine throws a hard error that bypasses our handlers, it might not log correctly.
  - **Mitigation**: The global `HTTPException` and generic `Exception` handlers in `main.py` will serve as a fallback to log 500s.
- **[Trade-off] Drift Detection Complexity**: Without raw features logged, detecting covariate drift requires separate engineering (e.g., differential privacy logs) later. We accept this to enforce patient privacy in Phase 15A.

## Migration Plan
1. Add the custom JSON logger configuration.
2. Add middleware and exception handlers.
3. Update the `/predict` endpoint to emit the log.
4. Deploy to Vercel (Staging first).
5. Verify logs appear in Vercel's integrated Log Drain.
