# Proposal: R5 — Explanation Stability (research only)

## Why
CardioVanta shows two feature-attribution views next to every prediction:
- linear contributions of the uncalibrated explanation model;
- SHAP-equivalent contributions against the frozen background.

Nothing has yet measured how these explanations behave under small, controlled input changes, or whether their direction of change agrees with the calibrated probability the user sees.

## What Changes
- New research experiment `experiments/r5_explanation_stability.py`. It uses the frozen production model `cardiovanta-lr13@1.0.0`, loaded read-only through the SHA-256-verified registry, and evaluates:
  - 100 deterministic synthetic profiles drawn from the canonical 13-feature contract;
  - one-feature-at-a-time perturbations within accepted constraints.
- Synthetic regression tests in `tests/test_r5_explanation_stability.py`.
- Results in `experiments/results/r5_explanation_stability.json`, and a report in `reports/r5_explanation_stability.md`.

## Non-goals
- No dataset is loaded: no `heart.csv`, no locked rows, no external cohorts.
- No retraining or recalibration.
- No change to production artifacts, the API, the contract, the registry or the frontend.
- No clinical interpretation. In particular, no clinical meaning is assigned to unverified or undefined categorical codes.
