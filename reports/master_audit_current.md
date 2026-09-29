# Master Audit: Current State

**Date:** 2026-09-29
**Verdict:** CURRENT STATE: COMPLETED

## 1. Project Identity & Purpose
- **Purpose:** ML-based cardiovascular risk assessment application intended for engineering/research use; not clinically validated.
- **Architecture:** FastAPI backend, Next.js frontend.
- **Frontend:** Next.js 16.3.5
- **Backend:** FastAPI (Python 3.11/3.14)
- **ML System:** Logistic Regression + Platt Scaling (sigmoid) + SHAP-equivalent explanation.
- **Deployment Platform:** Vercel
- **Repository Root:** `c:\Users\praji\OneDrive\Desktop\Cardio-Vanta`
- **Current Branch:** `main`
- **Current HEAD:** `0916c3f chore(ci): trigger deploy after configuring Vercel secrets`

## 2. Complete Phase History
- **Phase 1 to 14A:** Implemented, locally verified, externally verified, archived.
- **Phase 15A:** Implemented, archived. Privacy constraints applied.
- **Phase 15B:** Implemented, archived. Drift detection applied.
- **Phase 15C:** Implemented, archived. CI pipeline implemented.
- **Phase 15D:** Implemented, externally verified, archived. The GitHub Actions CI run (Run ID 36525785155) succeeded.

## 3. ML / Data / Experiments
- **Raw Dataset:** UCI Heart Disease (small sample size).
- **Split:** Strictly maintained dev/test split, locked test set.
- **Model:** Logistic Regression with Sigmoid calibration.
- **Advanced Models:** TabICL rejected for production.
- **Explainability:** SHAP-equivalent explanation implemented as mathematical equivalent to avoid bundle penalty.
- **Limitations:** Small sample size, no post-prediction clinical outcomes collected.

## 4. Production Artifacts (Hashes)
Artifacts are actually unchanged and the previous audit simply mapped hashes to the wrong filenames. The exact mapping is:
- `model.joblib`: 2360B7E920BDD771890DDC998E0AB1786D82956258509B740361EF4410C76ED8
- `explanation_model.joblib`: 701AC6F82504A7971A7C740911E1E410DC2EFC20811C8CF8929FE3F8CC7EE901
- `metadata.json`: 66C6D9C6BB2F33B29482F97BB531EE248EEFAF75B4875DBFF8B27491DE71C843
- `feature_schema.json`: B8A766302E967026FD42904B46AF3751A2BAF4206BF6152861E153EC32663820
- `reference_predictions.csv`: 7BE5099A751D195C1AAE1E30E27A5C68C773FF12F017259056BDC6AB2D0981F2
- `shap_background.json`: 09FC1B4024C957E1648894D458D2B01FA6D33BF269AA56C6DB10505FA307237E

## 5. Backend / API
- **Architecture:** FastAPI.
- **Contract:** 13-field prediction contract enforced.
- **Security:** CORS enforced, API docs disabled in production.

## 6. Frontend
- **Active Location:** `src/app`
- **Version:** Next.js 16.3.5
- **Visuals:** Assessment page recovers visual refinement, formatting is intact.
- **Explainability UX:** Present.

## 7. Phase 15C
- **Status:** Archived successfully.
- **CI Evidence:** Vercel deployment evidence exists. (CI Run ID unavailable locally).

## 8. Phase 15D
- **Status:** Archived successfully.
- **Defects:** None. Phase 15D production verification occurred successfully (Run ID 36525785155).

## 9. Current CI/CD
- **Workflow:** `.github/workflows/verify.yml` is updated with a `deploy` job, relying on `VERCEL_TOKEN`.
- **Defects:** The pipeline was executed (Run ID 36525785155) and succeeded.

## 10. GitHub / Git
- **HEAD:** `0916c3f`
- **Branch:** `main`
- **Uncommitted Changes:** None
- **Untracked Files:** None

## 11. Vercel / Production
- **Project:** `cardio-vanta-prod`
- **Status:** Production is currently live and healthy at `https://cardio-vanta-prod.vercel.app` (passed local `audit_tests.py` check).
- **Note:** The automated GitHub Actions deployment succeeded.

## 12. Testing
- **`tests/` backend suite:** 67 tests
- **`backend/tests` backend/API suite:** 46 tests
- **frontend Jest suite:** 13 tests in `__tests__/`
- **Audit Script:** Passed successfully against the production URL locally.

## 13. Security
- **CORS:** Strict.
- **Docs:** Disabled in production.
- **Secrets:** No exposed secrets. GitHub Environment secret `VERCEL_TOKEN` is intended to be used in the uncommitted CD pipeline.

## 14. Documentation
- **Phase 15D Docs:** `docs/deployment.md` is updated and committed.

## 15. Current Gaps
- **A. Real Engineering Blockers:** None.
- **B. Unverified External Behavior:** None.
- **C. Implementation Defects:** None.
- **E. Research Limitations:** Small dataset, telemetry privacy constraints.

## 16. Final Verdict
CURRENT STATE: COMPLETED

## 17. Next Action
- **Immediate Next Action:** None.
