# Proposal

## Why

The CardioVanta machine learning system currently lacks the ability to detect when the production patient population diverges significantly from the development dataset. Establishing a scientifically cautious drift-detection layer (Phase 15B) enables the operations team to monitor for cohort shifts over time without violating privacy constraints or making unverified claims of clinical deterioration. True concept drift and real performance degradation cannot currently be measured because CardioVanta does not collect post-prediction ground-truth outcomes.

## What Changes

- Implement an offline, stateless script to parse Phase 15A production telemetry logs and perform statistical drift detection.
- Establish the baseline prediction probabilities derived strictly from the original 242 development samples (the 61 locked test samples remain untouched).
- Apply a robust Kolmogorov-Smirnov (KS) methodology, incorporating permutation or resampling techniques to handle ties and small-sample uncertainty, evaluating distribution shifts in prediction probabilities between the baseline and production batches.
- Require both statistical evidence (p-value) and a meaningful effect size to declare statistical drift.
- Apply support-boundary violation monitoring for out-of-development-range flags, recognizing the development bounds as strict data-support limits rather than stochastic baselines.
- Establish a strict 50-observation minimum as an operational eligibility threshold. Below 50 observations yields insufficient evidence; no drift conclusion will be drawn. This is an operational policy, not a clinically or statistically validated threshold.
- Implement an explicit repeated-monitoring policy using non-overlapping evaluation periods to reduce multiple-testing false positives.
- Establish a configurable engineering/privacy retention policy (e.g., 30-day default) and restricted access for prediction probability telemetry, treating it as health-related data.
- Explicitly prevent raw clinical features from being monitored, processed, or logged for drift, adhering to strict privacy constraints.

## Capabilities

### New Capabilities
- `drift-detection`: Offline statistical monitoring to detect shifts in prediction probability distributions (using effect size, KS testing with permutations) and support-boundary violations, governed by strict minimum-observation and non-overlapping window policies.

### Modified Capabilities
- None

## Impact

- **Code:** A new standalone script (e.g., `scripts/detect_drift.py`) and associated unit tests will be created. The existing FastAPI application and Vercel serverless environment remain completely untouched and unmodified.
- **APIs:** No changes to the prediction API contract, threshold policy, calibration, or SHAP mathematics.
- **Systems:** The drift detection will run in an isolated environment (e.g., a CI/CD cron job, or triggered manually by MLOps). No database is introduced.
- **Operations:** MLOps personnel will review human-readable reports. The following are explicitly out of scope (non-goals): automated clinical alerts, automatic retraining, automatic model replacement, frontend dashboards, chatbot functionalities, and LLM integrations.
