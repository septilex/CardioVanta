# Design: R5 — Explanation Stability (pre-specified before execution)

## Model
- `cardiovanta-lr13@1.0.0`, loaded with `cardiovanta_ml.load_model(..., registry_root=<abs>/artifacts)`, which verifies SHA-256 before deserialisation.
- Inference uses `InferenceEngine`:
  - `predict` returns calibrated P(disease present);
  - `explain` returns linear contributions of the explanation model;
  - `explain_shap_equivalent` returns SHAP-equivalent contributions.
- Read-only: nothing is written to `artifacts/`.

## Synthetic profiles
- 100 profiles from `numpy.random.default_rng(20261031)`.
- **Continuous features:** uniform within the contract's development range. Values outside that range are accepted by the API but flagged, so the profiles stay in-distribution.
- **Binary and categorical features:** uniform over the contract's accepted codes.

## Perturbations (one feature at a time)
- **Continuous.** The value is shifted by ±5% and ±10% of the development-range width (`max − min`), giving 4 perturbations per feature. A shift that would leave the development range is skipped and counted, not clipped, so every perturbation has its nominal size.
- **Binary and categorical.** The value is replaced by every other accepted code. Codes are reported by number with their contract verification level (`verified_patient_matched`, `codebook_and_project_contract`, `unverified`, `undefined_in_codebook`). No clinical meaning is attached.

## Metrics (per perturbation; both explanation methods)
| Metric | Definition |
|---|---|
| Δp | Calibrated P(disease) after perturbation − before |
| Rank correlation | Spearman correlation of \|contribution\| across the 13 features, before vs after |
| Top-3 / top-5 overlap | \|top-k(before) ∩ top-k(after)\| / k, ranked by \|contribution\| (ties broken by contract feature order) |
| Perturbed-feature sign flip | The sign of the perturbed feature's contribution changes (contributions within 1e-12 of zero are treated as 0) |
| Other-feature sign flips | The number of non-perturbed features whose contribution sign changes |
| Additivity error | \|base + Σ contributions − decision_function_log_odds\| (base = intercept or expected value) |
| Direction agreement | sign(Δ contribution of the perturbed feature) equals sign(Δp), for perturbations with \|Δp\| > 1e-9 |

## Pre-stated analytical expectations (checked, not assumed)
1. **Locality.** Both methods are additive per feature for a linear model, so a perturbation of feature j changes only feature j's contribution. Other-feature contributions are expected to be unchanged, within 1e-12, and other-feature sign flips to equal 0.
2. **Additivity.** The error should be below 1e-9; the engine already asserts it to 5 decimals.
3. **Same deltas, different signs.** The two methods differ only by a per-feature constant offset (background means), so their Δ contributions are identical. Their sign-flip rates and rankings can still differ.

## Reporting
- Summaries for continuous and categorical perturbations separately, plus per-feature and per-magnitude tables.
- Summaries give the mean, median, 5th/95th percentiles, maximum and rates.
- Descriptive only: there is no hypothesis test and no decision rule.

## Reproducibility
- Deterministic seed.
- Two runs must give identical result content, excluding runtime.
- Production artifact integrity is checked after the runs.
