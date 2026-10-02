# Design

## Context
As part of the v1.0.1 hardening, we must enforce strict application boundary validations. Pydantic normally accepts `NaN` and `Infinity` as standard `float` values, but scikit-learn models crash or produce garbage when presented with them. Additionally, Pydantic's `ValidationError.errors()` contains a dictionary with an `input` key containing the raw literal value passed. This is a severe HIPAA/PII leak vector if logged or returned to clients.

## Decisions
1. **Validation at Schema Level**: Pydantic v2 `Field(allow_inf_nan=False)` will be used on all continuous float features to stop execution before the InferenceEngine.
2. **Error Scrubbing**: The global `RequestValidationError` handler in `main.py` will loop through the errors and `pop("input", None)` from each error dictionary before passing them to the logger or client response.
3. **Prevent Exception Leakage**: Unhandled `Exception` blocks (e.g. in `middleware.py` and `predict.py`) will log the exception type instead of the raw exception string or the full `exc_info=True` traceback, ensuring that local variables containing clinical data are not accidentally leaked.

## Risks
- **Over-sanitization**: If we remove too much, debugging becomes hard. However, we preserve the `loc` (field name), `msg` (what went wrong), and `type`, which are completely sufficient for debugging.
