# Proposal: R6 — Clinical Feature Codebook Resolution (research and provenance only)

## Why
The R1 contract marks the following training-encoding codes as unresolved:
- `slope` codes 0–2 and `thal` codes 1–3: `unverified`;
- `ca = 4` and `thal = 0`: `undefined_in_codebook`.

R5 showed that the production model relies materially on these inputs (for example, `thal` perturbations move P(disease) by up to 0.30). Their provenance and meanings need to be established from evidence, or their unresolved status confirmed explicitly.

## What Changes
- A deterministic evidence builder, `experiments/r6_codebook_evidence.py`. It assembles a machine-readable evidence record, `experiments/results/r6_codebook_evidence.json`, from:
  - the UCI codebook;
  - the R1 contract;
  - the Phase 17 validation module and report;
  - the external profiling report;
  - a dated record of the public UCI and Kaggle documentation checks.
- An evidence-backed mapping report, `reports/r6_feature_codebook_resolution.md`.
- Tests, `tests/test_r6_codebook_resolution.py`, covering the verified and the unresolved mappings, and the consistency of the evidence record with the contract.

## Non-goals
- No change to the clinical contract. Changing it would alter its SHA-256, which the registered model pins.
- No change to production artifacts, the registry, the API or the frontend; no retraining.
- No access to `heart.csv` rows or the 61 locked observations.
- No download of `processed.cleveland.data`: it contains the canonical records of all 303 Cleveland patients, including the locked 61.
- No inference of meanings from coefficients, feature importance or frequency distributions.
