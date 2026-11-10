# Proposal: R4 — Count Encoding of `ca` (research only)

## Why
- The production model (`cardiovanta-lr13@1.0.0`) one-hot encodes `ca`, the number of major vessels coloured by fluoroscopy, into five dummy columns (codes 0–4).
- The UCI codebook defines `ca` as a vessel **count, 0–3**. The R1 contract records codes 0–3 at verification level `codebook_and_project_contract`. Code 4 is `undefined_in_codebook`, with no clinical meaning asserted.
- One-hot encoding discards the ordering of a count and spends five coefficients on 242 development rows, where the higher counts and code 4 are rare.

No earlier phase tested an ordinal or count encoding of any input:
- Phase 2: algorithm benchmarking.
- Phase 3: calibration methods.
- Phase 4: thresholds and robustness.
- Phase 13: trees and TabICL.
- Phase 16: interaction and quadratic terms.
- "90%" study: domain features, B-splines, elastic-net, voting.
- Nested LDA and threshold optimisation.
- Phase 17: excluded `ca` entirely.

## Hypothesis (H1)
Replacing the five `ca` dummies with a fold-locally standardized count (codes 0–3) plus an explicit indicator for the undefined code 4 will:
- improve calibration (log loss / Brier score);
- improve prediction stability;
- cause no meaningful loss of discrimination.

## What Changes
- New research experiment `experiments/r4_ca_count_encoding.py`, with:
  - repeated, duplicate-aware nested cross-validation on the 242 development rows only;
  - preprocessing, C tuning and sigmoid calibration fitted inside training folds;
  - deterministic seeds.
- Synthetic regression tests in `tests/test_r4_ca_count_encoding.py`.
- Machine-readable results in `experiments/results/r4_ca_count_encoding.json`.
- Technical report `reports/r4_ca_count_encoding.md`.

## Non-goals
- No change to the production model, its artifacts, the registry, the 13-feature contract, accepted codes, outcome orientation, API or frontend.
- No access to the 61 locked Cleveland rows (lines are discarded unparsed).
- No use of external cohorts.
- No adoption decision for production. A positive result would only motivate a future registered v2 model.
