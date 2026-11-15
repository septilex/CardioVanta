# Model Card: `cardiovanta-lr13` v1.1.0

> **CardioVanta is a research tool. It is not clinically validated, is not a medical device, and must not be used for diagnosis or treatment decisions.**

## 1. Identity

| Field | Value |
|---|---|
| Model ID / version | `cardiovanta-lr13` / `1.1.0` (registry entry `artifacts/models/cardiovanta-lr13/1.1.0/`) |
| Package metadata | `package_version` 1.1.0, `model_version` "H2.1-pooled-calibration" (`artifacts/model-1.1.0/metadata.json`) |
| Artifacts | `artifacts/model-1.1.0/` (SHA-256 values in `checksums.sha256`) |
| Feature contract | `cardiovanta.clinical_feature_and_outcome_contract` v2.1.0 |
| Training command | `python -m src.experiment.phase5 --package-version 1.1.0 --pooled-calibration --output-dir artifacts/model-1.1.0` |
| Predecessor | `cardiovanta-lr13@1.0.0` (still registered; select it with `MODEL_VERSION=1.0.0` to roll back) |

## 2. What changed from 1.0.0

Only the calibration step. 1.0.0 averages five sigmoid-calibrated members, each calibrated on about 48 rows, which
compresses probabilities toward 0.5 (calibration slope about 1.27). 1.1.0 uses
`CalibratedClassifierCV(method="sigmoid", ensemble=False)` with the same five duplicate-aware
`StratifiedGroupKFold` splits: one sigmoid is fitted on the pooled out-of-fold decision values and applied to one
pipeline refitted on all 242 development rows.

The pipeline (preprocessing and `LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs",
random_state=42)`), the training rows, the 13 inputs and their codes are unchanged. `explanation_model.joblib`,
`feature_schema.json` and `shap_background.json` are byte-identical to 1.0.0, so the "Why" explanations are unchanged.

## 3. Evidence for the change

Pre-registered study H2.1 (`reports/h2_1_calibration_confirmation.md`), 20 repeats of nested cross-validation on
the 242 development rows:

| Metric | 1.0.0 recipe | 1.1.0 recipe |
|---|---|---|
| Calibration slope (ideal 1) | 1.267 [1.169, 1.374] | **1.003** [0.910, 1.086] |
| ROC-AUC | 0.9112 | 0.9109 |
| Log loss | 0.3802 | 0.3739 |
| Brier score | 0.1174 | 0.1160 |
| ECE (10 bins) | 0.0589 | 0.0398 |

All four pre-registered acceptance criteria passed (Δslope −0.271 [−0.341, −0.216]; 20/20 repeats). Discrimination
is unchanged, so accuracy at any fixed cut-off is essentially the same; the probabilities themselves are more
trustworthy. The 61 locked rows were not used to select or fit this version.

## 4. Intended use, inputs and output

As for 1.0.0: a research demonstration of calibrated probability estimation on a small historical dataset, not
for clinical use. All 13 inputs are required; codes follow contract 2.1.0, where every categorical code is
patient-matched to the UCI codebook (`docs/reports/CATEGORICAL_ENCODING_VERIFICATION_2026-11-15.md`). The output is
P(significant obstructive coronary artery disease present) = `predict_proba[:, index of label 0]`
(`disease_present_label` 0, interim legacy mapping, as for 1.0.0).

## 5. Golden synthetic predictions

| Fixture | 1.0.0 | 1.1.0 |
|---|---|---|
| HIGH | 0.985790929 | 0.994343297 |
| LOW | 0.016065906 | 0.007331075 |

## 6. Known limitations

- 242 training patients from one centre (Cleveland, 1980s referral cohort); external transport is weaker
  (Phase 17: ROC-AUC about 0.75 at Long Beach VA for related recipes).
- Better calibration on development data does not establish calibration in other populations.
- No validated clinical decision threshold exists; the API returns a probability only unless a threshold is passed.
- Explanations describe the uncalibrated explanation model's log-odds; they do not decompose the calibrated
  probability and are not causes.

## 7. Integrity

The registry verifies every artifact against `checksums.sha256` (whose own SHA-256 is pinned in `metadata.json`)
before deserializing, and refuses to load if the contract SHA-256, feature order, outcome mapping or scikit-learn
version (1.9.1) disagree.
