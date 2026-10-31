# Model Card: `cardiovanta-lr13` v1.0.0

> **CardioVanta is a research tool. It is not clinically validated, is not a medical device, and must not be used for diagnosis or treatment decisions.**

## 1. Identity

| Field | Value |
|---|---|
| Model ID / version | `cardiovanta-lr13` / `1.0.0` (registry entry `artifacts/models/cardiovanta-lr13/1.0.0/`) |
| Package metadata | `package_version` 1.0.0, `model_version` "Phase5-Final" (`artifacts/model/metadata.json`) |
| Artifacts | `artifacts/model/` (registered in place, byte-for-byte unchanged; SHA-256 values in `checksums.sha256`) |
| Feature contract | `cardiovanta.clinical_feature_and_outcome_contract` v2.0.0, SHA-256 `ec8918e7…5c431b` |
| Training script | `src/experiment/phase5.py` |

## 2. Architecture

- **Prediction model** (`model.joblib`): `CalibratedClassifierCV(method="sigmoid")`, an ensemble of 5 calibrated members. Each member is a pipeline:
  1. `ColumnTransformer`: StandardScaler on the 5 continuous inputs, passthrough on the 3 binary inputs, `OneHotEncoder(handle_unknown="ignore")` on the 5 categorical inputs;
  2. `LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=42)`.

  The calibration splits are 5 `StratifiedGroupKFold` folds that group duplicate feature rows.
- **Explanation model** (`explanation_model.joblib`): a separate *uncalibrated* LogisticRegression with the same preprocessing and hyperparameters, fitted on the same 242 development rows.
- **SHAP background** (`shap_background.json`): frozen background means used for the closed-form linear SHAP-equivalent attribution of the explanation model.

## 3. Intended use

This is a research and engineering demonstration of calibrated probability estimation and transparent attribution on a small historical dataset. It is not for clinical use, screening, triage or individual medical decisions.

## 4. Inputs

The 13 production features are defined by the clinical contract, in this order: `age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal`.

All 13 are required. Missing values, unexpected fields, NaN and infinity are rejected. Continuous values outside the development range are accepted but flagged with a warning.

The contract records a verification status for every categorical code:
- `cp`: verified by patient matching.
- `sex`, `fbs`, `exang`, `restecg` and `ca` 0–3: follow the UCI codebook and the project contract.
- `slope` and `thal` 1–3: **unverified** legacy labels.
- `ca=4` and `thal=0`: **not defined in the UCI codebook**. Their meaning is unknown and is not assumed to be "missing".

## 5. Output definition and outcome orientation

- **Output:** calibrated P(significant obstructive coronary artery disease present), defined by the contract as greater than 50% diameter stenosis in at least one major coronary vessel (UCI `num` > 0).
- **Class mapping (artifact-specific):** model classes are `[0, 1]`. **Label 0 = disease present; label 1 = disease absent.** The model was trained on the raw `target` column of the Kaggle-derived `heart.csv`, whose encoding is inverted relative to UCI `num`. This was established in Phase 17 and verified in R0.3.
- **How it is applied:** P(disease) is read from the `predict_proba` column of label 0. This equals 1 − P(label 1) exactly. Threshold class 1 means P(disease) ≥ threshold.
- **Mapping status:** `interim_legacy`. A retrained model should use a harmonised target (disease = 1) and declare its own `disease_present_label`.

## 6. Training and data provenance (documented records only)

- **Source data:** `data/raw/heart.csv` (SHA-256 `7c3014…d859`), a Kaggle redistribution of the UCI Cleveland Heart Disease data (303 rows according to package metadata).
- **Development split:** 242 rows (`data/processed/dev_indices.json`, SHA-256 `382f0f…5e6`). The remaining 61 rows are a separate partition, recorded for provenance only.
- **Seed:** 42.
- **Recorded git commit:** `43859481ad4c4ba78a8d9aa9bf5a672e31ec4041` (package metadata).
- **Environment:** scikit-learn 1.9.1, Python 3.11.9 at training.
- **Not established in project records:** population characteristics beyond the UCI dataset documentation; data-collection procedures; any data-quality review of the Kaggle redistribution beyond the Phase 17 encoding findings.

## 7. Performance evidence (as documented; not re-run in R2)

| Evidence | Value | Source | Caveats |
|---|---|---|---|
| Nested CV ROC-AUC (5×5, development rows only) | mean 0.902 | `reports/phase2b_nested_cv_results.csv` | Small sample; plain StratifiedKFold (not duplicate-grouped) |
| Calibration CV, sigmoid (development rows) | Brier 0.121, log loss 0.386 | `reports/phase3_calibration_results.json` | Development data only |

**Orientation caveat.** Historical threshold-dependent figures in Phase 2–16 reports (recall, precision, specificity, "positive" counts, Youden and max-F1 thresholds) refer to label 1, which is the disease-*absent* class. They must not be read as disease sensitivity or specificity. ROC-AUC and Brier score are unaffected in magnitude by this relabelling.

**The 61-row Cleveland partition is not an independent test set.** It has been scored in several experiments and used for error analysis that informed later research, so any metric on it is optimistically biased.

**No external validation.** Phase 17's multi-centre (LOCO) results concern different candidate models (9–11 inputs). This 13-feature model was not externally validated, because `slope`, `ca` and `thal` are largely missing in the external cohorts.

## 8. Known limitations

- Small, historical, single-source development data (242 rows), so generalisation is unknown.
- The categorical meanings of `slope` and `thal`, and of `ca=4` / `thal=0`, are unresolved for the training encoding.
- The model depends on the exact scikit-learn version (1.9.1). The registry refuses to load it under any other version.
- No outcome feedback is collected in production, so drift monitoring cannot measure performance.

## 9. Calibration considerations

- Sigmoid calibration was selected over isotonic because of isotonic's high log loss on this small sample (`reports/phase3_calibration_results.json`).
- Calibration was assessed on the development data only.
- Calibration under dataset shift is not established for this model. Phase 17 showed substantial calibration-in-the-large shift for other models at external centres.

## 10. Explanation limitations

- Both attribution methods (linear contributions and SHAP-equivalent) explain the **uncalibrated explanation model**, not the calibrated ensemble that produces the reported probability.
- They decompose the explanation model's log-odds exactly, but the attribution does NOT decompose the calibrated probability. On synthetic profiles they are strongly but not perfectly rank-concordant with the calibrated P(disease) (R0.3 analysis), so treat them as directional signals.
- Contributions are expressed in disease-present orientation (positive = toward disease presence).
- Attributions describe model behaviour, not clinical causality.

## 11. Integrity

Artifacts are verified against `checksums.sha256` before deserialization, and the manifest itself is pinned by SHA-256 in `metadata.json`. These checks detect modification relative to the registered manifest. They are unsigned, so they do not prove authenticity against a party who can rewrite the manifest and metadata consistently.
