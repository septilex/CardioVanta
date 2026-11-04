# Proposal: H2.1 — Confirmation of the Pooled OOF Calibration Finding (research only)

## Why
H2 (`reports/h2_calibration_recipe.md`) did not meet its pre-registered rule. That rule used the folded endpoint |slope − 1|. Descriptively, however, pooled out-of-fold sigmoid calibration (`CalibratedClassifierCV(ensemble=False)`) moved the production recipe's calibration slope:
- from 1.287 to 1.024;
- in 10 of 10 repeats;
- with a signed Δslope 95% CI of [−0.335, −0.217];
- with no ROC-AUC cost.

H2.1 tests that finding prospectively, with:
- a **signed** primary endpoint;
- a pre-declared direction, intervals, multiplicity handling and acceptance criteria;
- **new** resampling seeds that H2 did not use.

## What Changes
- New research experiment `experiments/h2_1_calibration_confirmation.py`, with two arms on identical splits:
  - **A**, the production recipe;
  - **C**, pooled OOF calibration.
- Synthetic regression tests in `tests/test_h2_1_calibration_confirmation.py`.
- Results in `experiments/results/h2_1_calibration_confirmation.json`, and a report in `reports/h2_1_calibration_confirmation.md`.

## External cohorts: excluded (pre-registered)
Hungary and Long Beach VA are **not** evaluated. Their existing feature and outcome mappings are not compatible with the production 13-feature recipe.
- The canonical→training code mappings for `slope` and `thal` are `unverified` in the R1 clinical contract (`cardiovanta_ml/contracts/feature_schema.v2.json`).
- Documented missingness (`reports/external_data_profiling.json`, "-9" sentinels) is as follows:

  | Feature | Hungary | Long Beach VA |
  |---|---|---|
  | `ca` | 290/294 | 198/200 |
  | `thal` | 266/294 | 159/200 |
  | `slope` | 190/294 | 101/200 |
  | `thalach`, `exang`, `oldpeak`, `trestbps` | — | about 53–56/200 each |

- The production recipe and contract reject missing values (`missing_value_policy: rejected`).

Evaluating externally would require inventing code mappings or imputing values, which this study forbids. The outcome mapping (UCI `num > 0`) is compatible, but that alone is insufficient.

**Disclosure.** These cohorts were already used in Phase 17, so they are not untouched independent validation data for any future analysis.

## Non-goals
- No change to production models, artifacts, the registry, the contract, the API or the frontend.
- No access to the 61 locked rows.
- No external calibration or tuning.
- No adoption decision.

## Independence caveat
H2.1 uses the same 242 development patients as H2. It therefore tests robustness to new data partitions and a prospectively specified endpoint. It is **not** an independent replication on new patients.
