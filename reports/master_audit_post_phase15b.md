# CardioVanta: Master Audit Report (Post-Phase 15B)

## 1. PROJECT IDENTITY & PURPOSE
**Purpose:** CardioVanta is a clinical decision-support tool providing cardiovascular risk assessment via a highly interpretable, lightweight Logistic Regression model.
**Architecture Assessment:** The architecture remains strictly centered on a cardiovascular ML API serving a Next.js frontend form.
**Feature Drift:** No feature drift or unnecessary product expansion observed. The system remains focused on its core 13-feature prediction task.
*(Evidence: DESIGN DECISION / VERIFIED BY SOURCE CODE)*

## 2. ORIGINAL PROJECT FORENSICS
**Cardio-Monitor History:** The old methodology utilized uncalibrated, black-box approaches with poor evaluation practices (no strict train/test isolation, data leakage, lack of explainability constraints). 
**CardioVanta Transition:** CardioVanta established a rigorous ML lifecycle (Nested CV, strict 242/61 split, sigmoid calibration, explicit SHAP equivalence, and structured telemetry) to replace the legacy system.
*(Evidence: HISTORICAL FACT)*

## 3. DATA FOUNDATION
**Dataset:** `heart.csv` with exactly 13 input features + 1 target (`target`).
**Integrity:** Raw dataset SHA256 is `7c3014365675306819510a49ff289efbec1d1a6a666a2dc7652f1547b383d859`. Duplicate-aware grouping was applied.
**Isolation:** Exactly 242 development samples and 61 locked-test samples. The locked test set remains entirely isolated and protected from drift baselining, monitoring, and threshold selection.
*(Evidence: VERIFIED BY SOURCE CODE / VERIFIED BY CURRENT TEST/ARTIFACT)*

## 4. ML DEVELOPMENT
**Methodology:**
- **Preprocessing:** StandardScaler (continuous), OneHotEncoder (categorical), passthrough (binary).
- **Model:** Logistic Regression (C=0.1, class_weight=balanced, lbfgs, seed=42).
- **Calibration:** Sigmoid calibration (CV=5) due to isotonic overfitting risk.
- **Evaluation:** Nested 5-fold CV to select the optimal hyperparameter constraints.
- **Production Artifact:** Output to `artifacts/model/`.
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT)*

## 5. ADVANCED ML RESEARCH
**Research History:**
- Evaluated XGBoost, LightGBM, and CatBoost against Logistic Regression. LR matched performance without complexity overhead.
- Evaluated TabICLv2 (in-context learning). It matched LR but required GPU/VRAM overhead; LR was retained.
- **SHAP:** Investigated official SHAP package but rejected it due to a 147MB bundle penalty and 2.65s cold start. A mathematically equivalent SHAP approximation (`coef * (X - E[X])`) was implemented and proven to match identical attribution.
**Conclusion:** All advanced research models were explicitly rejected for production in favor of the calibrated LR model.
*(Evidence: HISTORICAL FACT / LIMITATION)*

## 6. PRODUCTION ARTIFACTS
**Metadata:** `artifacts/model/metadata.json` confirms `package_version: 1.0.0`, `model_version: Phase5-Final`, `algorithm: Logistic Regression`, `calibration_method: sigmoid`.
**Explainability Artifact:** Background references for SHAP-equivalence are preserved securely.
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT)*

## 7. BACKEND
**Architecture:** FastAPI application.
**Endpoints:** 
- `GET /api/v1/health` (Returns OK, CORS validated)
- `POST /api/v1/predict` (Accepts 13 features, returns prediction, range warnings, base explanation, and SHAP-equivalent explanation).
**Behavior:**
- Strict input validation via Pydantic (out of range gives warning, invalid categorical/missing fields give 422).
- Does not automatically enforce a clinical threshold (`threshold_applied: null`).
- Exact deterministic inference.
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT)*

## 8. FRONTEND
**Architecture:** Next.js 16.3.5 (React 19, Turbopack).
**Components:** Assessment form mapping to the exact 13-field API contract. Results UI surfaces probability, support boundary warnings, and both standard + SHAP-equivalent explanations transparently.
**Testing:** Jest coverage (13 tests passing) spanning all form logic, error boundaries, UI components, and API integration.
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT)*

## 9. DEPLOYMENT
**Vercel Architecture:** Deployed as a serverless monolithic FastAPI backend (`api/index.py`) and Next.js frontend (`vercel.json` routing configuration).
**Health:** Build runs cleanly in 5.7 seconds. API passes all health and CORS security checks.
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT)*

## 10. PRODUCTION VERIFICATION
- **Health:** HTTP 200 OK
- **Canonical Prediction:** `0.8061117606132114`
- **Threshold:** `null`
- **Explanations:** Technical and SHAP-equivalent explanations are intact and correctly decompose the log-odds.
- **Metadata:** Intact.
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT)*

## 11. PHASE 15A MONITORING
**Implementation:** Offline JSON structured telemetry via standard logging.
**Privacy:** Raw 13 clinical inputs are strictly excluded.
**Telemetry:** `prediction_probability`, `status`, `latency`, `request_id`, `package_version`, `model_type`, `outside_development_range`.
**Architecture:** Stateless operation; logging failure does not block prediction execution.
*(Evidence: VERIFIED BY SOURCE CODE / DESIGN DECISION)*

## 12. PHASE 15B DRIFT DETECTION
**Implementation:** `scripts/detect_drift.py` provides stateless offline drift analysis using the two-sample Kolmogorov-Smirnov (KS) test.
**Configuration:**
- 242-sample frozen development baseline strictly isolated. 61 locked samples excluded.
- Validates `package_version` and `model_type` against authoritative metadata, rejecting mismatches.
- Minimum N=50 operational eligibility policy.
- KS D-statistic evaluated via 10,000 Monte Carlo permutations (deterministic seed=42) for robust finite-sample p-value estimation.
- D >= 0.2 effect size threshold serves strictly as an engineering monitoring policy, not a clinical interpretation.
- Aborts safely without taking automated action (no retraining, no clinical alerts).
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT / VERIFIED BY SOURCE CODE)*

## 13. OPENSPEC
**State:** `drift-detection` and `production-monitoring-foundation` are fully complete and stored in `openspec/changes/archive`.
**Sync Status:** Main specs are perfectly synced. No active unarchived changes exist. No stale tasks remain.
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT)*

## 14. TESTING
**Results:**
- **Backend:** 46/46 passed (pytest)
- **Frontend:** 13/13 passed (jest)
- **Drift Suite:** 14/14 passed. Covers model integrity mismatches, permutation logic, clear drift, no drift, and support boundary tracking.
- **Static Analysis:** TypeScript (`tsc --noEmit`) passes with 0 errors.
- **Audit Suite:** `audit_tests.py` passes all mathematical, metadata, and threshold assertions.
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT)*

## 15. SECURITY / PRIVACY
**Privacy:** No raw clinical inputs are logged in telemetry (Phase 15A compliance).
**Secrets:** No hardcoded tokens, API keys, or exposed `.env` credentials in source control.
**Security:** FastAPI docs (`/docs`, `/redoc`) are disabled. CORS restricts wildcard origins (`evil.com` -> 400).
*(Evidence: VERIFIED BY CURRENT TEST/ARTIFACT / VERIFIED BY SOURCE CODE)*

## 16. DOCUMENTATION
**Status:** All architecture, methodology, calibration, explainability, threshold, monitoring, and drift design decisions are thoroughly documented within the OpenSpec main specs and Markdown archives, perfectly mirroring actual implementation.
*(Evidence: VERIFIED BY SOURCE CODE)*

## 17. GIT / REPOSITORY STRUCTURE
**Structure:** The project operates cleanly at the root `C:\Users\praji\OneDrive\Desktop\Cardio-Vanta`.
**Risk:** No nested repository conflicts or untracked architecture deviations that threaten reproducibility.
*(Evidence: VERIFIED BY SOURCE CODE)*

## 18. CURRENT LIMITATIONS
- **Data Size:** Extremely small dataset (303 total samples) limits model capacity.
- **Ground Truth:** True concept drift and clinical degradation cannot be measured due to lack of post-prediction patient outcomes.
- **Drift Granularity:** Inability to measure within-range feature-level drift due to the privacy requirement preventing raw clinical telemetry retention.
*(Evidence: LIMITATION)*

## 19. REMAINING GAPS
- **Blockers:** None.
- **Engineering Gaps:** Lacks automated infrastructure-as-code (IaC) deployment pipelines (currently relies on manual Vercel push).
- **Polish:** The frontend assessment form could benefit from enhanced accessibility (ARIA live regions for results).
- **Research Opportunities:** Secure enclaves/federated approaches to allow feature-level drift monitoring without violating privacy.
*(Evidence: INFERENCE)*

## 20. PHASE 15C RECOMMENDATION
**Top Recommended Area: Automated CI/CD Deployment Pipeline**
- **Problem it solves:** Validates tests, linting, and drift artifacts automatically on PR, ensuring human error doesn't break production.
- **Why it follows:** The foundation (tests, drift scripts, static analysis) is entirely in place and highly stable. It is the logical next step.
- **Scope risk:** Low risk if restricted to GitHub Actions/Vercel integration.
- **Phase 15C Viability:** Yes.

**Alternative Area: Feature-Level Differential Privacy Telemetry**
- **Problem it solves:** Solves the inability to measure feature drift while respecting strict privacy requirements.
- **Why it follows:** Phase 15A/B laid the probability monitoring foundation. Feature telemetry is the missing half.
- **Scope risk:** High risk of complexity (requires epsilon-delta privacy math, noise injection, and complex density estimations).
- **Phase 15C Viability:** Debatable; potentially too research-heavy.

## 21. EVIDENCE CLASSIFICATION
All points above derive strictly from:
- VERIFIED BY CURRENT TEST/ARTIFACT
- VERIFIED BY SOURCE CODE
- HISTORICAL FACT
- DESIGN DECISION
- LIMITATION
- INFERENCE

## 22. FINAL PROJECT STATE
**Chronological Phase Table:**
| Phase | Title | Status |
|---|---|---|
| 1-12 | Foundational ML Lifecycle | Complete |
| 13 | Explainability & Advanced Research | Complete |
| 14 | FastAPI & Next.js Architecture | Complete |
| 15A | Production Monitoring Foundation | Complete |
| 15B | Drift Detection | Complete |

**Final Verdict:**
`CURRENT STATE: VERIFIED AND STABLE`
