# Design

## Context

CardioVanta currently relies on a tiny dataset (303 rows total, 242 development) and operates as a stateless API on Vercel. Phase 15A successfully implemented privacy-safe structured telemetry that excludes raw patient features. True concept drift and real performance degradation cannot currently be measured because CardioVanta does not collect post-prediction ground-truth outcomes; measuring actual predictive performance in a future phase would require gathering verified clinical diagnoses to join against historical predictions.

## Goals / Non-Goals

**Goals:**
- Implement robust statistical tests for drift on output distributions (prediction probabilities) using permutation/resampling to handle ties and uncertainty.
- Create a stateless, offline script capable of analyzing JSON log exports deterministically.
- Treat prediction probabilities as sensitive health-related telemetry with explicit retention and access controls.

**Non-Goals:**
- Measuring true within-range feature-level covariate drift (impossible without raw features).
- Inferring clinical deterioration, model failure, or concept drift from statistical drift.
- Introducing a stateful database or caching layer.
- Frontend dashboards, chatbot functionality, or LLM integrations.
- Automated retraining, automated model replacement, or clinical alerting.

## Decisions

**1. Statistical Methodology: Permutation-based Two-Sample Kolmogorov-Smirnov (KS) Test**
- *Rationale*: We must detect drift in continuous `prediction_probability` metrics. Given the tiny 242-sample baseline, asymptotic KS test assumptions break down, especially in the presence of ties or constant probabilities. We will use a permutation-based Monte Carlo p-value estimation using at least 10,000 permutations. The exact procedure will combine the frozen reference probabilities and production probabilities, preserve the observed reference and production sample sizes, randomly permute the pooled labels, recompute the KS D-statistic, and repeat at least 10,000 times using a reproducible deterministic seed, reporting the observed D and permutation-based p-value. Finite-sample p-value handling must be defined appropriately to avoid reporting an impossible finite-simulation p=0.
- *Effect Size & Classification*: p-value alone MUST NOT declare drift. The final drift classification requires a combination of: 1) meeting the operational minimum observation eligibility (>= 50), 2) strong statistical evidence (e.g., permutation p-value < 0.05), and 3) a meaningful effect size measured by the observed KS D-statistic meeting an ENGINEERING MONITORING POLICY threshold (e.g., D >= 0.2). This threshold is not statistically validated, clinically validated, or evidence of model failure/clinical deterioration.

**2. Baseline Population: 242 Development Predictions**
- *Rationale*: We must use the predictions generated from the 242 development set samples as the frozen reference baseline. The 61 locked test samples are strictly excluded to preserve unbiased performance evaluation.

**3. Minimum Observation Policy: 50 Samples (Operational Eligibility)**
- *Rationale*: A script run against a small sample will falsely trigger drift alerts due to extreme high-variance noise against the small 242-sample baseline. We define 50 observations strictly as an operational minimum eligibility threshold. Below 50 observations yields insufficient evidence, and no drift conclusion will be drawn. This threshold is not clinically or statistically validated; it is an engineering guardrail.

**4. Architecture: Offline Python Script**
- *Rationale*: Running drift detection inside the stateless Vercel API is computationally and statistically invalid. An offline script (`scripts/detect_drift.py`) reading JSON log dumps preserves the architecture. No database is introduced.

**5. Privacy and Retention Policy**
- *Rationale*: `prediction_probability` is treated as health-related telemetry. An engineering/privacy policy of a configurable 30-day default retention is established, with access restricted to authorized MLOps personnel. No clinical or legal compliance claims are invented here.

**6. Out-of-Range Monitoring**
- *Rationale*: The development min/max support boundary is a strict data-support boundary, not a normal stochastic baseline. Production out-of-range frequencies will be monitored as support-boundary violations rather than compared to an unjustified conventional baseline.

## Risks / Trade-offs

- **[Risk] Repeated Monitoring and False Positives:** Evaluating drift repeatedly over sliding windows inflates the Type I error rate.
  - *Mitigation:* The system enforces non-overlapping evaluation windows to reduce repeated-testing issues. However, this does not completely eliminate Type I error. The reports will explicitly contextualize uncertainty and multiple-testing risks.
- **[Risk] Missing True Covariate Shift:** We cannot detect if internal feature distributions shift within valid ranges.
  - *Mitigation:* This is a deliberate and accepted trade-off to strictly exclude raw 13-feature clinical inputs.
