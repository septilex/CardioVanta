# Tasks

## 1. Input Validation
- [x] 1.1 Update `backend/app/schemas/predict.py` to use `Field(allow_inf_nan=False)` on all float fields.

## 2. Error Sanitization
- [x] 2.1 Update `backend/app/main.py` to sanitize `RequestValidationError` logs by stripping the raw `input` key.
- [x] 2.2 Update `backend/app/api/endpoints/predict.py` to only log the exception type, rather than the raw string, for unhandled failures.
- [x] 2.3 Update `backend/app/api/middleware.py` to remove `exc_info=True` from unhandled exceptions.

## 3. Testing & Verification
- [x] 3.1 Create `backend/tests/test_stage6_security.py` to cover adversarial inputs and logging tests.
- [x] 3.2 Run Pytest suite and ensure 100% pass rate.
- [x] 3.3 Validate the OpenSpec change directory.
