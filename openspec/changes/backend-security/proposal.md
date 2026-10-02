# Proposal

## Why
Clinical predictive models can be vulnerable to unsafe input handling, potentially leading to adversarial behaviors, unhandled exceptions, and leakage of sensitive PII/PHI in application logs. We must harden the backend API to strictly reject non-finite inputs and sanitize error logs to guarantee data privacy.

## What Changes
1. Update `backend/app/schemas/predict.py` to explicitly reject NaN and Infinity for all float features via `Field(allow_inf_nan=False)`.
2. Update `backend/app/main.py` exception handlers (like `RequestValidationError`) to strip the raw input value before writing to logs.
3. Update `backend/app/api/endpoints/predict.py` and `backend/app/api/middleware.py` to prevent logging the direct exception message or `exc_info=True` for unhandled exceptions to prevent stack trace/message leakage of inputs.
4. Introduce a new comprehensive test suite `backend/tests/test_stage6_security.py` covering adversarial inputs and logging sanitization.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- **Validation**: Will now return 422 for non-finite values (NaN/Infinity).
- **Logging**: Will no longer contain raw input values during validation/inference failures.

## Impact
- `backend/app/schemas/predict.py`
- `backend/app/main.py`
- `backend/app/api/endpoints/predict.py`
- `backend/app/api/middleware.py`
- New file: `backend/tests/test_stage6_security.py`
