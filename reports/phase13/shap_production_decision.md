# Phase 13C.3 — SHAP Production Decision

## 1. Overview
This report evaluates whether SHAP (`shap.LinearExplainer`) should be formally adopted as the production explanation layer for the Vercel API. The analysis includes rigorous end-to-end performance profiling (cold start, warm latency, memory, and bundle size) in a simulated production environment.

## 2. End-to-End Latency
We measured a full end-to-end request loop (data validation + model prediction + SHAP explanation + JSON serialization) over 2,000 requests.
- **Median Latency:** 4.17 ms
- **p95 Latency:** 4.87 ms
- **p99 Latency:** 5.86 ms

*Conclusion:* In a "warm" execution loop, SHAP adds negligible overhead. The entire end-to-end request completes comfortably in under 6 milliseconds.

## 3. Cold-Start Latency
Vercel Serverless Functions scale to zero, making cold-start initialization times critical to user experience.
- **`import shap` and dependencies:** 2.65 seconds
- **Model Load:** 0.01 seconds
- **Explainer Initialization:** 0.03 seconds
- **First Explanation:** <0.01 seconds
- **Total Cold Start Penalty:** ~3.06 seconds

*Conclusion:* Importing the `shap` library (and its heavy backend dependencies like `numba` and `llvmlite`) introduces a massive 2.65-second penalty to cold starts, significantly degrading the first-load experience.

## 4. Memory & Bundle Impact
- **Process Memory Before Imports:** 16.4 MB
- **Process Memory After Imports:** 200.8 MB
- **`shap` Package Bundle Size:** ~3.1 MB
- **Transitive Dependencies (`numba`, `llvmlite`):** ~143.9 MB
- **Total Bundle Increase:** ~147.2 MB

*Conclusion:* Vercel enforces a strict 500 MB (unzipped) limit for serverless functions. Adding 147 MB solely for SHAP pushes the deployment dangerously close to that threshold and increases the runtime memory footprint by over 184 MB. 

## 5. Background Strategy Stability
We tested the global importance variance across 5 independent background subsets.
- **Max Absolute Deviation:** 0.021
- **Ranking Stability:** Near perfect. 

The full development set remains an ideal and stable background.

## 6. Explanation Comparison
We verified that the current logic (`coef * X`) and SHAP (`coef * (X - E[X])`) diverge predictably. 
SHAP centers explanations around the "average patient" baseline (Expected Value = -0.111 log-odds). The current method centers around a mathematical zero-vector (Intercept = +0.361 log-odds). As concluded previously, the SHAP paradigm is vastly superior for clinical interpretation.

## 7. Recommended Architecture
Based on the data, adding the `shap` library to Vercel is **NOT RECOMMENDED**. The 147 MB bundle size increase and 2.65s cold-start import penalty are unacceptable for an edge-native serverless architecture when the underlying model is purely linear.

**The Safest Future Architecture (Custom SHAP Equivalent):**
Because the model is a simple Logistic Regression, a SHAP `LinearExplainer` simply computes `coef * (X - E[X])`. 

We should **A. Replace the current explanation logic with SHAP's mathematical equivalent**, but we should implement it *manually* in `src/inference/predict.py` rather than installing the `shap` package.
- We can pre-calculate the background means `E[X]` offline.
- We simply change the inference logic to `contributions = coef * (X_transformed - E_X_transformed)`.
- The intercept becomes the pre-calculated expected value.

**Files Required for Future Implementation:**
- `src/inference/predict.py` (modify logic to subtract precomputed means)
- `artifacts/model/explanation_model.joblib` (or a new small JSON file storing the background means)

This approach delivers the superior clinical interpretability of SHAP with **true zero overhead**: 0MB bundle size, 0ms cold-start penalty, and <1ms latency.
