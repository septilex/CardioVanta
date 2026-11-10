# Proposal: R7 — Unverified Feature Ablation (research only)

## Why
R6 (`reports/r6_feature_codebook_resolution.md`) found that the training encodings of `slope` (0–2) and `thal` (1–3) cannot be mapped to canonical UCI codes. It also found that `ca = 4` and `thal = 0` are undefined in the codebook. Nevertheless the production model `cardiovanta-lr13@1.0.0` one-hot encodes all of these codes. R5 showed that its predictions move materially when `thal` changes. Before any future model version keeps or drops these inputs, we need to know how much predictive and calibration performance depends on them.

## Question
How much do the discrimination and calibration of the production training recipe depend on `slope`, `thal` and `ca`? Each is removed individually, and then all three together.

## What Changes
- New research experiment `experiments/r7_unverified_feature_ablation.py`. It compares five arms on identical, duplicate-aware, repeated nested-CV splits, using only the 242 development rows:
  - A: the 13-feature baseline;
  - B: without `slope`;
  - C: without `thal`;
  - D: without `ca`;
  - E: without all three.
- Synthetic tests in `tests/test_r7_unverified_feature_ablation.py`.
- Results in `experiments/results/r7_unverified_feature_ablation.json`, and a report in `reports/r7_unverified_feature_ablation.md`.

## Non-goals
- No change to the production model, artifacts, registry, contract, outcome orientation, API or frontend.
- No retraining of the production model and no adoption decision.
- No access to the 61 locked rows.
- No clinical meaning is assigned to any code. The ablation measures statistical dependence on the training encoding only.
- R8 is not started.
