# API Documentation

## Request / Response Behavior
The primary inference endpoint is `POST /api/v1/predict`.

### Request
Accepts JSON representing the 13 feature columns in `feature_schema.json`.
An optional `threshold` query parameter can be provided (between 0.0 and 1.0).

### Response
The response is structured into four main objects:
- **`prediction`:** Contains the calibrated `probability`, the `class_` (if a threshold was applied), and `threshold_status` indicating whether an unvalidated threshold was applied.
- **`development_range_warning`:** Flags features that fall outside the minimum or maximum values observed in the development dataset (`min`/`max` in feature schema).
- **`explanation`:** Provides the uncalibrated `decision_function_log_odds`, the `intercept`, and feature `contributions`.
- **`metadata`:** Returns the `model_type` ("Logistic Regression") and `calibration_method` ("sigmoid").

### Edge-Case Behavior
Inference gracefully catches exceptions and returns an HTTP 500 without leaking stack traces. Out-of-bounds continuous features are reported directly in the `development_range_warning`.
