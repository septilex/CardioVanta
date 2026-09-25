# Deployment & Production Artifacts

## Production Artifacts
The production model bundle is self-contained in the `artifacts/model/` directory. No external databases are required for inference.
- `model.joblib`: The calibrated ensemble model wrapper.
- `explanation_model.joblib`: The underlying uncalibrated Logistic Regression model for SHAP/linear explanations.
- `feature_schema.json`: The authoritative contract for expected feature types, ranges, and allowed categories.
- `metadata.json`: Immutable provenance, configuration, and policy constraints.

## Security & Configuration
- **CORS:** Highly restricted. The API strictly limits origins and disallows credentials.
- **Credentials:** No secrets, keys, or credentials exist in the source or artifacts.
- **Environment:** Defaults to `production` via Pydantic settings. OpenAPI docs (`/docs`) are disabled in production contexts.
- **Reproducibility:** Seed (`42`) and dataset hashes are stored in `metadata.json` for full artifact rebuildability.
