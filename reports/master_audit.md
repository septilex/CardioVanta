# CardioVanta Master Audit

**Generated:** 2026-09-24

## Executive Summary
This document provides a chronological and comprehensive master audit of the CardioVanta project. It traces the project's evolution from the initial data foundations to the current production-ready ML architecture, backend and frontend integrations, and experimental phases (TabICL and SHAP analysis).

All claims in this audit are directly sourced from the project's documentation, reports, metadata, and artifacts.

---

## 1. Project Origins & Data Foundation
**Sources:** `docs/ml-methodology.md`, `artifacts/model/metadata.json`

- **Goal:** Provide a robust, containerized, leakage-safe ML prediction system for cardiovascular health.
- **Data Source:** `heart.csv` (SHA-256: `7c3014365675306819510a49ff289efbec1d1a6a666a2dc7652f1547b383d859`).
- **Data Splitting Strategy:**
  - **Total Samples:** 303 rows.
  - **Development Set:** 242 samples (used for nested CV, calibration, error analysis).
  - **Locked Test Set:** 61 samples (20% of data, completely isolated from all training and decision phases).
- **Features:** 13 features (continuous, binary, categorical). Target is a binary classification.

---

## 2. Machine Learning Lifecycle

### Phase 2: Baseline & Nested Cross-Validation
**Sources:** `docs/ml-methodology.md`, `artifacts/model/metadata.json`, `reports/phase2b_nested_cv_results.json`, `reports/phase2c_model_selection.json`
- **Methodology:** Nested 5-fold Cross-Validation on the development set.
- **Preprocessing:** 
  - Continuous features: `StandardScaler`
  - Categorical features: `OneHotEncoder(handle_unknown="ignore")`
  - Binary features: `passthrough`
- **Selected Algorithm:** Logistic Regression.
- **Hyperparameters:** `C=0.1`, `class_weight="balanced"`, `solver="lbfgs"`, `random_state=42`.

### Phase 3: Calibration
**Sources:** `docs/calibration.md`, `reports/phase3_calibration_results.json`
- **Goal:** Ensure predicted probabilities reliably reflect true likelihoods.
- **Evaluated Methods:** Uncalibrated, Isotonic, Sigmoid, Temperature.
- **Selected Method:** **Sigmoid**.
- **Rationale:** Although Isotonic regression had a marginally lower Brier score (0.1200) than Sigmoid (0.1210), its high Log Loss (0.6516) indicated a high risk of overfitting on the small dataset. Sigmoid was chosen for better generalization (Log Loss: 0.3860).

### Phase 4: Thresholding, Error Analysis & Robustness
**Sources:** `docs/threshold-policy.md`, `docs/model-evaluation.md`, `reports/phase4a_error_patterns.json`, `reports/phase4b_perturbation_summary.json`
- **Threshold Policy:** Inference must return calibrated probabilities. No authoritative clinical threshold exists. Mathematical candidates on the development set:
  - Default: `0.50` (F1 = 0.8496)
  - Youden's J: `0.46`
  - Max F1: `0.43`
- **Subgroup Analysis:** Evaluated descriptive differences with a constraint of min size 20 (and min class size 5). Smaller subgroups were marked "Not estimable".
- **Robustness:** Evaluated via data perturbations and resampling robustness to ensure prediction stability.

---

## 3. Explainability & SHAP Phase (Phase 13C)
**Sources:** `docs/explainability.md`, `reports/phase13/shap_production_decision.md`, `reports/phase13/shap_equivalent_validation.md`
- **Objective:** Evaluate SHAP for production explainability.
- **Performance Profiling:** SHAP addition introduced a 2.65-second cold-start import penalty and a ~147.2 MB bundle size increase, risking Vercel's 500 MB serverless limit.
- **Decision:** **Do NOT install the `shap` package in production.**
- **Implementation:** SHAP was implemented mathematically as a custom equivalent (`coef * (X - E[X])`) in `src/inference/predict.py`. Background means (`E[X]`) were pre-calculated offline.
- **Result:** True zero overhead (0 MB bundle, 0 ms cold-start penalty) while delivering identical SHAP interpretability.

---

## 4. Advanced Research: TabICLv2 Benchmark (Phase 13B)
**Sources:** `reports/phase13/tabicl_benchmark.md`, `reports/phase13/tabicl_statistical_audit.md`
- **Objective:** Benchmark TabICLv2 Tabular Foundation Model against the production Logistic Regression.
- **Methodology:** Nested 5-fold StratifiedGroupKFold on development set and evaluation on the locked 61-sample test set.
- **Results:**
  - TabICLv2 Native (Zero-shot) matched Logistic Regression on the test set.
  - A 10,000-iteration paired bootstrap analysis showed **no statistically significant difference** between TabICLv2 and LR.
- **Decision:** Logistic Regression was retained as the production model due to its 0 MB VRAM requirement, microsecond latency, and lack of dependency on large checkpoints.

---

## 5. Backend & Frontend Architecture
**Sources:** `docs/architecture.md`, `docs/api.md`, `README.md`
- **Frontend:** Next.js 16.3.5 (React 19) utilizing the App Router.
- **Backend:** FastAPI, deployed via Vercel-compatible structure / Docker Compose.
- **API Endpoint:** `POST /api/v1/predict` accepts JSON of 13 features and returns `prediction`, `development_range_warning`, `explanation`, and `metadata`.
- **Local Connectivity Fix:** A bug where `npm run dev` failed to route `/api/v1/predict` due to IPv4/IPv6 `localhost` mismatch was resolved by updating `src/lib/api.ts` and `.env.local` to strictly use `127.0.0.1:8000`. Both servers run concurrently and communicate successfully.

---

## 6. Test Status & OpenSpec Integration
**Sources:** Prior session logs, recent shell tasks
- **Test Status:** 
  - Backend: `pytest` passed successfully (46/46).
  - Frontend: `npm test` passed successfully (13/13).
  - Local endpoint testing confirmed the backend correctly processes and returns 200 OK.
- **OpenSpec Integration:**
  - OpenSpec (`@fission-ai/openspec@latest`) was installed globally.
  - Initialized with `openspec init --tools antigravity`.
  - Application code, deployment, and ML artifacts remained completely untouched.

---
**Audit Concluded.** No code or deployment changes were made during this audit phase.
