# Tasks

## 1. Setup Logging Utilities

- [ ] 1.1 Create `backend/app/core/logging.py` containing a custom JSON formatter for the standard Python `logging` module. Verify by importing the module and printing a test log message formatted as valid JSON.
- [ ] 1.2 Update `backend/app/main.py` to initialize the custom JSON logger configuration on startup. Verify by checking that startup messages print in JSON format.

## 2. Request Interception and Exception Handling

- [ ] 2.1 Create `backend/app/api/middleware.py` containing a `BaseHTTPMiddleware` class that generates a request ID, measures latency, and catches status codes. Verify by writing a unit test that confirms latency is >0 and the `request_id` is assigned to request state.
- [ ] 2.2 Add the middleware to the FastAPI application in `backend/app/main.py`. Verify by running a local health check and confirming the middleware processes the request.
- [ ] 2.3 Implement custom exception handlers for `RequestValidationError` and `HTTPException` in `backend/app/main.py` that emit JSON logs before returning a response. Verify by triggering a 422 error and confirming the JSON error log is printed to stdout.

## 3. Emitting Prediction Events

- [ ] 3.1 Modify `predict_endpoint` in `backend/app/api/endpoints/predict.py` to emit a structured JSON log on successful predictions containing metadata, latency, and status, but excluding raw 13 features. Verify by sending a warm payload and checking stdout for the exact schema required.
- [ ] 3.2 Ensure the logging call in `predict_endpoint` degrades gracefully (e.g., using a try/except block around the `logger.info` call) so logging failures do not break the API response. Verify by mocking the logger to raise an Exception and confirming the API still returns 200 OK.

## 4. Testing & Verification

- [ ] 4.1 Create `tests/test_monitoring.py` with integration tests for latency measurement, 422 error logging, and the prediction event schema. Verify by running `pytest tests/test_monitoring.py` and seeing all tests pass.
- [ ] 4.2 Run `audit_tests.py` to verify no performance regressions or broken API contracts exist. Verify by checking that all audit tests pass with similar latency to prior runs.
