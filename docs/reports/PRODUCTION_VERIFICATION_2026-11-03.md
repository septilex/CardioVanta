# CardioVanta Production Prediction Verification (2026-11-03)

> **Result: PRODUCTION BLOCKER.** The live deployment returns the pre-R0.3, **inverted** probability. The outcome-orientation correction is not deployed. No fix was attempted, and nothing in production was modified.

| Field | Value |
|---|---|
| Check time | 2026-11-03 05:27 UTC |
| Production URL | `https://cardio-vanta-prod.vercel.app`, from `audit_tests.py:8`, `docs/deployment.md:18` and `README.md:13` |
| Endpoint | `POST /api/v1/predict` (`backend/app/api/endpoints/predict.py`; called by `src/lib/api.ts`) |
| Method | Strictly read-only: one `GET /api/v1/health`, two `POST /api/v1/predict` with synthetic inputs, one `GET /assessment`. TLS verification on; 60-second timeouts |
| Inputs | Only the project's synthetic golden fixtures `HIGH` and `LOW` (`scripts/ci/verify_wheel_install.py:33-36`; the same profiles appear in `backend/tests/test_r0_outcome_semantics.py`). No real patient information |
| Repository state | Branch `horizon0/research-ci-quarantine`; last GitHub-recorded production deployment `3b46957` (2026-10-19) |

## 1. Synthetic fixtures

| Feature | HIGH | LOW |
|---|---:|---:|
| age | 67.0 | 37.0 |
| sex | 1 | 0 |
| cp | 0 | 2 |
| trestbps | 160.0 | 120.0 |
| chol | 286.0 | 200.0 |
| fbs | 0 | 0 |
| restecg | 0 | 1 |
| thalach | 108.0 | 187.0 |
| exang | 1 | 0 |
| oldpeak | 3.0 | 0.0 |
| slope | 1 | 2 |
| ca | 3 | 0 |
| thal | 3 | 2 |

The expected values are pinned in the repository:
- **After R0.3 (correct orientation):** P(disease present) HIGH = **0.985790929**, LOW = **0.016065906** (`verify_wheel_install.py:37`, `test_r0_outcome_semantics.py:53`).
- **Before R0.3 (inverted):** HIGH = **0.014209**, LOW = **0.983934** (`test_r0_outcome_semantics.py:52`).

## 2. Results

| Request | HTTP | Result |
|---|---|---|
| `GET /api/v1/health` | 200 | `{"status":"ok","service":"CardioVanta"}` |
| `POST /api/v1/predict` HIGH | 200 | `probability` **0.014209070903** |
| `POST /api/v1/predict` LOW | 200 | `probability` **0.983934094106** |
| `GET /assessment` | 200 | Static HTML (111,073 bytes) |

| Check | Live value | Expected (R0.3) | Verdict |
|---|---|---|---|
| HIGH probability | 0.014209071 | 0.985790929 | **Inverted**: equals 1 − expected (difference 9.7e-11) |
| LOW probability | 0.983934094 | 0.016065906 | **Inverted**: equals 1 − expected (difference 1.1e-10) |
| High > low | No (0.014 < 0.984) | Yes | **FAIL** |
| Model identity | `metadata.package_version: "1.0.0"`, `model_type: "Logistic Regression"`, `calibration_method: "sigmoid"`. No model ID exposed | `cardiovanta-lr13@1.0.0` | Same artifact package |
| Post-R0.3 fields `prediction.outcome`, `probability_definition`, `metadata.outcome_mapping` | **Absent** | Present | Pre-R0.3 serving code |
| Linear explanation log-odds | HIGH −3.837, LOW +3.485 (log-odds of label 1 = disease absent) | Disease orientation (HIGH positive) | Legacy orientation |
| Assessment page `cp` options | 0 "Typical Angina", 1 "Atypical Angina", 2 "Non-anginal Pain", 3 "Asymptomatic" | 0 Asymptomatic … 3 Typical Angina (patient-matched, Phase 17) | **Inverted labels** (pre-R0.3) |
| R1 helper text "not yet verified against the training encoding" | Absent | Present in the current source | Pre-R1 frontend |

Response headers show `Server: Vercel` and `X-Vercel-Id: bom1::iad1::…`. The function ran in the `iad1` region, with no cache.

## 3. Interpretation

1. **Production uses the correct artifacts with the old serving code [verified].** The probabilities are exactly the complement of the golden values, so the same `1.0.0` model is loaded, but the API returns the probability of model label 1. For this model that is **disease absent**.
2. **The R0.3 correction is not deployed [verified].** The response schema, the explanation orientation and the chest-pain labels all match the code before `f72ae4d`. This is consistent with the last recorded deployment, `3b46957` (2026-10-19).
3. **User impact.** A profile with textbook high-risk findings is shown as about 1.4%, a low-risk profile as about 98.4%, and the chest-pain choices are encoded in reverse. **The live application presents an inverted estimate.**

## 4. Blocker status and options (not performed)

This is recorded as a **production blocker**. No automatic fix was attempted, and no deployment was triggered.

| Option | Effect | Prerequisites | Owner decision |
|---|---|---|---|
| A. Deploy the current architecture (R0.3–R3 plus Horizon 0) | Corrects the orientation, labels and schema | A Vercel build that fits the function size limit (the local build was 301 MB against 225 MB; see `docs/reports/VERCEL_BUNDLE_INVESTIGATION_2026-11-03.md`); `main` and `production` protection; a smoke test with assertions; merge of PR #2 | Yes |
| B. Interim mitigation on the live site, for example temporarily disabling the assessment or showing a prominent notice | Stops misleading output while A is prepared | A deliberate, separate deployment | Yes |
| C. Roll back to an earlier deployment | Does not help: every recorded deployment predates R0.3 | — | — |

**Confirmation criterion for a future fix:**
- the same read-only check returns HIGH ≈ 0.985790929 and LOW ≈ 0.016065906 (tolerance 1e-6);
- the response includes `prediction.outcome = "significant_obstructive_cad_present"` and `metadata.outcome_mapping`;
- the assessment page lists `cp` 0 as "Asymptomatic".

This check should become an assertion in `audit_tests.py`.
