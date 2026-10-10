# CardioVanta ML Revision Audit

## 1. Executive Summary
This comprehensive revision audit reconstructs the complete ML lifecycle of CardioVanta. It evaluates the dataset, methodology, and empirical evidence to determine the true state of the ML models and recommend the next research phase. The audit confirms that while extensive model families (97 configurations across 8 families, plus TabICLv2) have been rigorously evaluated using a corrected global nested-CV pipeline, the 95% accuracy target remains unachieved. The evaluated model search did not achieve 95% accuracy. The results motivate investigation of feature representation and data characteristics before further expanding the model search space. The next recommended phase is Feature Engineering based on existing error analysis hypotheses.

## 2. Complete ML Timeline

- **Phase 1: Dataset acquisition and schema**
  - **Objective:** Establish the foundation dataset.
  - **Result:** 303 rows, 13 predictor features + 1 target, split into 242 dev and 61 test samples.
  - **Status:** Frozen.

- **Phase 2: Baseline model selection/tuning**
  - **Objective:** Establish baseline predictive performance.
  - **Result:** Logistic Regression selected over KNN, SVM, RF, GBM, and XGBoost via initial nested CV.
  - **Status:** Superseded by Global Nested-CV correction.

- **Phase 3: Calibration**
  - **Objective:** Ensure output probabilities are reliable.
  - **Result:** Sigmoid (Platt) scaling applied using 5-fold CV. Isotonic regression rejected due to small sample size overfitting risk.
  - **Status:** Frozen.

- **Phase 4: Threshold investigation**
  - **Objective:** Optimize decision boundaries and evaluate robustness.
  - **Result:** Analyzed Youden J and Max F1 thresholds, perturbation bounds, resampling stability, and subgroup performance. 
  - **Status:** Complete. Default threshold retained.

- **Phase 5: Model packaging/reproducibility**
  - **Objective:** Serialize production artifacts.
  - **Result:** `metadata.json` and joblib files generated with SHA256 hashes.
  - **Status:** Frozen.

- **Phase 6–12: API, UI, and CI/CD Foundation**
  - **Objective:** Wrap ML in a robust, verifiable product architecture.
  - **Result:** FastAPI backend, Next.js frontend, contract testing, security CORS, deployment to Vercel, and automated tests established.
  - **Status:** Active.

- **Phase 13: Advanced ML experiments and explainability**
  - **Objective:** Evaluate Tabular Foundation Models (TabICLv2) and SHAP.
  - **Result:** TabICLv2 Native achieved 0.9167 ROC-AUC (Test) but was rejected for production due to GPU/VRAM overhead (105MB checkpoints vs lightweight LR). Official SHAP rejected for bundle size penalty; exact mathematical equivalent implemented.
  - **Status:** Complete/Archived.

- **Phase 14: Explainability UX**
  - **Objective:** Surface attribution to users safely.
  - **Result:** UI component visualizing linear attribution arrays.
  - **Status:** Active.

- **Phase 15: Telemetry/drift/CI/CD and production hardening**
  - **Objective:** Monitor production and automate deployment.
  - **Result:** Middleware JSON logging (15A), offline KS drift test (15B), GitHub Actions CI (15C) and CD (15D) implemented.
  - **Status:** Active.

- **v1.0.1 hardening**
  - **Objective:** Solidify reproducibility, artifact integrity, and factual correctness.
  - **Result:** Pipeline enforces exact artifact hashes; UI updated with clinical disclaimers.
  - **Status:** Active.

- **Global nested-CV correction**
  - **Objective:** Fix outer-fold candidate-selection leakage and duplicate-row leakage.
  - **Result:** Rewrote search using duplicate-aware StratifiedGroupKFold evaluating 97 configurations. 
  - **Status:** Complete.

- **Global nested-CV freeze**
  - **Objective:** Lock the final corrected evaluation results.
  - **Result:** LR_production (C=0.1, balanced) retained. 95% target formally missed.
  - **Status:** Frozen.

## 3. Dataset & Provenance
**FACT**: The dataset is the Cleveland/UCI Heart Disease dataset.
- **Row count**: 303 rows.
- **Feature count**: 13 predictors (age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal).
- **Target**: Presence of cardiovascular disease (binary).
- **Missing values**: Historically imputed or dropped; currently preprocessed cleanly.
- **Duplicates**: Known duplicates exist.
- **Duplicate grouping**: Duplicate records share the same `dev_groups` identifier to prevent fold contamination (leakage) during CV.
- **Splits**: 
  - **RAW DATASET**: The full 303 rows (SHA256: `7C3014365675306819510A49FF289EFBEC1D1A6A666A2DC7652F1547B383D859`).
  - **DEVELOPMENT DATA**: 242 rows used strictly for training, calibration, thresholding, and nested CV. These are the *only* rows allowed to influence model selection.
  - **LOCKED TEST DATA**: 61 rows strictly isolated. Evaluated exactly once for the final unbiased performance estimate.

## 4. Production Model
**FACT**: The current production model is `LR_production`.
- **Algorithm**: Logistic Regression.
- **Hyperparameters**: `C=0.1`, `class_weight='balanced'`, `solver='lbfgs'`.
- **Preprocessing**: StandardScaler (continuous), OneHotEncoder (categorical), passthrough (binary).
- **Calibration**: Sigmoid (Platt scaling) fitted on development data.
- **Threshold**: Standard probability threshold (`0.5`), unadjusted for clinical asymmetry.
- **Inference flow**: Pydantic validation -> preprocessing -> LR predict_proba -> probability.
- **Explanation flow**: Mathematical exact SHAP-equivalent (`coef * (X - E[X])`).
- **Rationale**: Selected under the predefined global nested-CV evaluation procedure for having the highest uncalibrated Inner ROC-AUC, breaking ties with Inner Accuracy, across 97 candidates.

## 5. Complete Model Inventory
Every model family evaluated across historical and global nested-CV phases:
- **Logistic Regression**: 10+ configs (GridSearchCV). Best ROC-AUC, chosen for prod. Validated.
- **SVM**: 16+ configs. RBF/Linear kernels. Rejected: Suboptimal metrics compared to LR. Validated.
- **Random Forest**: 20+ configs. Rejected: Lower accuracy/ROC-AUC. Validated.
- **Gradient Boosting**: Evaluated. Rejected: Suboptimal metrics. Validated.
- **XGBoost**: Evaluated. Rejected: Suboptimal metrics. Validated.
- **LightGBM**: Evaluated in historical benchmarking. Rejected: Overfit on small dataset. Validated.
- **CatBoost**: Evaluated in historical benchmarking. Rejected. Validated.
- **TabICLv2**: 2 configs (Native, Calibrated). Best locked-test ROC-AUC (0.9167). Rejected: 105MB VRAM overhead not suitable for Vercel serverless. Validated.
- **KNN**: 28 configs. Rejected. Validated.
- **Stacking / Voting**: Explicitly EXCLUDED from global nested-CV to prevent duplicate-row leakage (sklearn lacks native group-aware stacking support). Rejected/Invalid.

## 6. Historical Experiments
- **Initial Phase 2B (Independent CV)**: Evaluated model families independently. Caused selection bias by picking the global best via outer OOF scores. Superseded.
- **Uncalibrated Output Use**: Historical reliance on uncalibrated tree margins vs calibrated LR probabilities. Addressed via Phase 3.
- **SHAP Package Benchmark**: Tested official `shap` library. Discovered 147MB bundle penalty and 2.65s cold start. Superseded by equivalent math.

## 7. Methodology & Leakage Corrections
- **Duplicate Leakage**: Standard K-Fold splits duplicate patients into both train and validation sets, inflating scores. **Corrected**: Implemented `StratifiedGroupKFold` using duplicate identifiers.
- **Candidate-Selection Leakage**: Choosing the best model based on cross-validated scores overestimates unseen performance. **Corrected**: Implemented Global Nested-CV, forcing hyperparameter selection into the inner loop.
- **Stacking Leakage**: Meta-models blend predictions but fail to respect group boundaries easily. **Corrected**: Explicitly excluded ensembles from the final search space.
- **Locked-Test Contamination**: Thresholds or calibrators previously fitted globally. **Corrected**: Locked test strictly isolated until final scoring.

## 8. Calibration & Threshold History
- **Calibration**: Isotonic regression was tested but rejected due to the small sample size (242 dev) risking severe overfitting. Sigmoid calibration was adopted and validated. TabICLv2 calibration degraded its Brier score (since it reduced its context window), proving Native was better.
- **Threshold**: Youden J and Max F1 thresholds were calculated on the dev set. However, applying them on the locked test was deemed high-risk without clinical justification. The default threshold was retained.

## 9. Explainability History
- **Initial**: Black-box approach.
- **Exploration**: Official `shap` library tested.
- **Correction**: Official package bloats serverless functions. Replaced with exact mathematical equivalence for linear models (`coef * (X - E[X])`), verified against the official package. UI renders this attribution dynamically.

## 10. Current Best Valid Evidence
**FACT**: The strongest methodologically valid, duplicate-aware nested-CV estimate is:
- **Nested-CV OOF Estimate**: Accuracy = 0.8430 | ROC-AUC = 0.9088 | AP = 0.9077 | F1 = 0.8571
- **Locked-Test Performance**: Accuracy = 0.8689 | ROC-AUC = 0.9048 | Precision = 0.8378 | Recall = 0.9394 | Specificity = 0.7857 | F1 = 0.8857 | Brier = 0.1280

## 11. Error/Failure Knowledge Already Available
- **False Positives (Dev: 19, Test: 6)** [OBSERVATION]: Tends to happen in patients with lower cholesterol or higher resting BP in the observed samples. The model occasionally over-predicts disease in patients with asymptomatic chest pain (`cp=0`) if other features are borderline.
- **False Negatives (Dev: 21, Test: 2)** [OBSERVATION]: Patients with disease who are missed present with lower maximum heart rates (`thalach`) in both dev and test sets.
- **Feature Discrepancy** [OBSERVATION]: `oldpeak` distributions vary sharply between True Positives (median 0.0-0.4) and False Negatives (median 0.6-0.8) based on descriptive analysis.
- **Model Bias** [OBSERVATION]: The baseline model favors sensitivity over specificity in the observed splits.
- **Decision Boundary** [INFERENCE]: The linear boundary is unable to dynamically threshold `thalach` conditionally upon `age`.
- **Sample Size** [LIMITATION]: These findings derive from small subsets (e.g., 2 test FNs) and should be treated as hypotheses, not robust generalizations.

## 12. What Has Already Been Tried
- Baseline Linear Models (LR, SVM).
- Tree Ensembles (RF, GBM, XGBoost, LightGBM, CatBoost).
- Tabular Foundation Models (TabICLv2).
- Sigmoid Calibration.
- Exhaustive Hyperparameter Grids (97 configurations).

## 13. What Has NOT Been Tried
- **Feature Engineering / Interactions (Not Tested)**: E.g., `age` × `thalach` to model age-adjusted maximum heart rate.
- **Nonlinear Transformations (Not Tested)**: Polynomial features or binning for `oldpeak`.
- **Ordinal Encoding (Not Tested)**: Encoding `cp` or `restecg` as ordinal rather than one-hot to preserve severity relationships.
- **Domain-Informed Features (Not Tested)**: Clinical risk indices (e.g., framing ratios).
- **Cost-Sensitive Thresholds (Not Tested for Prod)**: Deploying a threshold optimized for clinical utility (e.g., prioritizing recall over specificity explicitly).
- **Robust Preprocessing / Missingness Indicators (Not Explored)**.
- **Bayesian Modeling (Not Tested)**.
- **TabPFN (Not Tested)**.

## 14. 95% Target Reality Check
**FACT**: No methodologically valid experiment has exceeded 90% accuracy on the locked test set or the nested-CV OOF estimates. 
- Strongest valid accuracy is ~86.89%.
- Historical scores approaching 90%+ were artificially inflated by duplicate-row leakage and candidate-selection bias.
- **INFERENCE**: The evaluated model search did not achieve 95% accuracy. The available feature set and small sample size are plausible constraints and warrant investigation, but this audit does not establish that either imposes a hard accuracy ceiling.

## 15. Remaining Research Opportunities
1. **Feature Engineering (Interactions & Nonlinearities)**: Addressing the `thalach` and `oldpeak` error clusters. (Highest Expected Improvement).
2. **Clinical Threshold Policy Integration**: Allowing the API to take a target recall/specificity constraint. (Lowest Leakage Risk).
3. **Tabular Foundation Model API (TabPFN)**: For dynamic datasets where user-uploaded data needs zero-shot predictions. (Highest Scientific Value, low impact on current CardioVanta dataset).

## 16. Recommended Next ML Phase
**DECISION**: **Phase 16 - Feature Engineering & Robust Representation**.
**Why:** The currently evaluated search space covers the tested configurations across the investigated model families, but did not achieve the target accuracy. The `error_analysis.md` report hypotheses identified `thalach` vs `age` interactions and `oldpeak` nonlinearities as potential factors for False Negatives. Feature engineering is a promising next direction to explore these hypotheses.

## 17. Recommended Experiment Design
- **Mechanism**: Introduce polynomial features for `oldpeak` and an interaction term for `age` × `thalach`. Implement ordinal encoding for `cp`.
- **Methodology**: Use the exact same Global Nested-CV `StratifiedGroupKFold` pipeline to evaluate the new preprocessing pipeline against the existing `LR_production` baseline.
- **Success Criteria**: Nested CV accuracy > 0.86 (currently 0.8430) without degrading recall below 0.85.
- **Stop Criteria**: If nested-CV accuracy does not improve by at least 1.5% absolute, abandon feature engineering and declare the 87% test accuracy the absolute dataset limit.

## 18. Limitations
**LIMITATION**: The proposed feature engineering relies on hypotheses drawn from a small sample of errors (21 FNs in dev). Interaction terms risk overfitting on small datasets (N=242). Strict nested CV is mandatory to prevent feature-selection leakage.

## 19. Final Conclusion
The CardioVanta repository correctly reconstructs a robust, leakage-free ML pipeline. The 95% target was not achieved in the evaluated search space, though this does not establish an accuracy ceiling. The next appropriate step is feature engineering targeted specifically at age-adjusted heart rates and ST-depression nonlinearities, evaluated strictly under the established global nested-CV framework, as one of several possible promising directions.
