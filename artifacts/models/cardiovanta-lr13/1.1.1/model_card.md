# Model Card: `cardiovanta-lr13` v1.1.1

> **CardioVanta is a research tool. It is not clinically validated, is not a medical device, and must not be used for diagnosis or treatment decisions.**

## 1. Identity

| Field | Value |
|---|---|
| Model ID / version | `cardiovanta-lr13` / `1.1.1` (registry entry `artifacts/models/cardiovanta-lr13/1.1.1/`) |
| What it is | The fitted parameters of `cardiovanta-lr13@1.1.0`, exported to JSON and served with NumPy only |
| Artifacts | `artifacts/model-1.1.1/` (SHA-256 values in `checksums.sha256`) |
| Serialization | `runtime.serialization = "portable_json"`, format `cardiovanta.portable_linear.v1` |
| Export command | `python scripts/research/export_portable_model.py --source-version 1.1.0 --target-version 1.1.1` |
| Feature contract | `cardiovanta.clinical_feature_and_outcome_contract` v2.1.0 |

## 2. Why this version exists

Serving 1.1.0 needs scikit-learn, SciPy and pandas to unpickle and run the model. On Vercel those libraries make the
Python function large, and a cold start took about 40 seconds. The model is a scaler, a one-hot encoder, a logistic
regression and one sigmoid calibrator, all of which are a few lines of arithmetic. 1.1.1 stores those parameters
as JSON (`model.json`, `explanation_model.json`) and computes them with NumPy
(`cardiovanta_ml/inference/portable.py`). No pickle is loaded on this path.

## 3. Equivalence with 1.1.0

- Same training data, recipe, calibration and parameters; nothing was refitted.
- The exporter refuses to register unless, on 50,000 random inputs, the portable model reproduces 1.1.0's
  probabilities and explanation log-odds within 1e-12. Measured: probabilities differ by at most 2.2e-16 (one unit
  of floating-point rounding in the sigmoid); preprocessing and log-odds are bit-identical.
- Golden synthetic predictions are the same as 1.1.0: HIGH 0.994343297, LOW 0.007331075.
- `feature_schema.json` and `reference_predictions.csv` are copied from 1.1.0; `shap_background.json` differs only
  in naming `explanation_model.json` as its model.

Performance, calibration evidence (H2.1), intended use, inputs, output definition and limitations are those of
1.1.0; see `artifacts/models/cardiovanta-lr13/1.1.0/model_card.md`.

## 4. Integrity

The registry verifies every artifact against `checksums.sha256` (whose SHA-256 is pinned in `metadata.json`) before
reading it, checks the contract SHA-256, feature order and outcome mapping, and validates the portable documents
(feature names, coefficient shapes, finite parameters) before serving. scikit-learn is not imported.
