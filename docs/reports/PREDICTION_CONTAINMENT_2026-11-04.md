# CardioVanta Prediction Containment (2026-11-04)

> **Status: PREPARED ON THE BRANCH, NOT DEPLOYED.** This change lives on `horizon0/research-ci-quarantine` (PR #2, unmerged). The live site is **not** contained: it still serves the inverted, pre-R0.3 output recorded in `docs/reports/PRODUCTION_VERIFICATION_2026-11-03.md`. Containment takes effect only after an approved, verified production deployment (§4).

## 1. Purpose

Production returns exactly 1 − the correct probability, so its estimates must not be presented as trustworthy. This change switches off every way of generating a prediction until a corrected deployment has been verified. It does not fix the inversion, and it does not change the model (`cardiovanta-lr13@1.0.0`), its artifacts or any research evidence.

## 2. How it works

| Part | Behaviour while predictions are unavailable |
|---|---|
| **Switch:** `configs/prediction_service.json` | `"predictions_enabled": false`. It is committed, reviewed and read by both the API and the web app, so one deployment cannot disagree with itself. It is **not** an environment variable, so production settings cannot re-enable predictions |
| **Fail-safe** | Predictions are enabled only when the file parses as a JSON object and `predictions_enabled` is exactly `true`. A missing, unreadable or malformed file, or any other value, keeps them unavailable |
| **API:** `backend/app/core/prediction_availability.py`, route dependency on `POST /api/v1/predict` | Every request gets HTTP **503** with `Cache-Control: no-store` and the body `{"detail": <notice>, "code": "predictions_temporarily_unavailable", "predictions_available": false}`. The dependency runs before body validation and before any model call, so invalid bodies also get 503 and the model is never invoked. Refusals are logged without input values |
| **Unchanged API behaviour** | Startup still loads and SHA-256-verifies the registered model (fail-closed). `GET /api/v1/health` is unchanged. Other routes are unchanged |
| **Web app:** `/assessment` | Renders a notice instead of the form. The form, its state and its submit handler are never mounted |
| **Web app:** `src/lib/api.ts` `predict()` | Refuses without sending a request (`ApiError`, status 503, the same code). If the web app were enabled while the API is contained, it shows the API's notice |
| **Landing page and other routes** | Unchanged. Links to `/assessment` lead to the notice |
| **Bundle inspector:** `scripts/ci/inspect_vercel_bundle.py` | Checks the golden values through the bundled engine, and checks that the bundled API does exactly what the switch says (503 while closed) |

Notice text: "CardioVanta predictions are temporarily unavailable while we verify the prediction service. No risk estimate can currently be generated."

## 3. Verification on the branch

- **Backend tests:** `backend/tests/test_prediction_containment.py` and `test_r3_deployment.py::test_shipped_bundle_refuses_predictions` use the real, shipped switch. Existing serving tests run with the gate opened in-process only (root `conftest.py`), so their assertions are unchanged.
- **Frontend tests:** `__tests__/containment.test.tsx` uses the shipped switch. The existing form tests (`__tests__/page.test.tsx`) open the switch for that file only.
- **Tripwire:** the containment tests assert that the shipped switch is closed. An accidental change of the switch therefore fails CI.

## 4. Activating containment in production (owner approval required for every step)

1. Run the Linux build workflow `vercel-linux-build.yml` on this branch (R3.1; it uses the `production` environment's secrets). Confirm that `inspect_vercel_bundle.py` passes, including `golden_probabilities`, `prediction_api_matches_availability_switch` (503 expected) and the function size limit. **If the bundle does not fit, this path is blocked** (see `docs/reports/VERCEL_BUNDLE_INVESTIGATION_2026-11-03.md`).
2. Recommended first: protect `main` and add reviewers to the `production` environment.
3. Merge PR #2 into `main` with CI. Never use `[skip ci]`. The `deploy` job then runs `vercel --prod`.
4. Verify read-only with the synthetic fixtures only:
   - `POST /api/v1/predict` returns 503 with `code` `predictions_temporarily_unavailable` and no probability;
   - `GET /assessment` shows the notice and no form;
   - `GET /` and `GET /api/v1/health` return 200.
5. Record the evidence. Only then may production be described as contained.

If the Linux build cannot fit the limit, a separate, reviewed hotfix would be needed, for example the same containment applied to the code of the deployed commit `3b46957`. That hotfix has **not** been prepared.

## 5. Re-enabling predictions later

1. Deploy the corrected serving code with containment still active. The bundle inspector checks the golden values through the engine.
2. In a separate pull request, set `predictions_enabled` to `true` and deliberately update the shipped-state containment tests.
3. Verify that pull request on a non-production (preview) deployment with the read-only check:
   - HIGH ≈ 0.985790929 and LOW ≈ 0.016065906 (tolerance 1e-6);
   - `prediction.outcome` is present;
   - `cp` 0 is "Asymptomatic".
4. Merge with CI, then repeat the check against production.
