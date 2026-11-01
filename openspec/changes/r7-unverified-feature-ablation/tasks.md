# Tasks

## 1. Pre-registration
- [x] 1.1 Record the arms, endpoints, uncertainty method, hypotheses and classification rule (`design.md`) before any execution.

## 2. Implementation
- [x] 2.1 Implement `experiments/r7_unverified_feature_ablation.py`: reuse the R4 loader and the H2 metrics; build the five arms; run repeated nested CV on identical splits; run the paired group bootstrap; apply the classification; write the JSON output.
- [x] 2.2 Add synthetic tests (`tests/test_r7_unverified_feature_ablation.py`). Acceptance: they pass with no dataset read. Result: 21/21 pass.

## 3. Execution
- [x] 3.1 Run on the 242 development rows. Acceptance: 242 rows, 0 locked rows parsed, identical splits. Result: met (fold hash `f191e82d…`).
- [x] 3.2 Reproducibility. Acceptance: a second full run gives identical content, excluding runtime. Result: identical (`7931f88c…`).
- [x] 3.3 Production isolation. Acceptance: the integrity check passes and the contract is unchanged.

## 4. Reporting
- [x] 4.1 Write `reports/r7_unverified_feature_ablation.md`.

## 5. Reporting correction (post hoc, documented)
- [x] 5.1 R7-C1: restate the calibration-slope comparisons by |slope − 1| from the saved per-repeat results, with no rerun. Report signed slopes separately and flag crossings below 1. Preserve all original fields and labels (`experiments/r7_slope_reporting_correction.py`, `tests/test_r7_slope_reporting_correction.py`, report §7).

## Outcome
Under the pre-registered rule, removing `ca`, `thal` or all three shows `material_dependence`; the `thal` label is not robust to the Bonferroni correction. Removing `slope` is `inconclusive`, with a near-zero effect. H7.1 and H7.4 are supported. No clinical meaning is assigned, and production is unchanged.
