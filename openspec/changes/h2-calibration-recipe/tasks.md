# Tasks

## 1. Pre-registration
- [x] 1.1 Record the arms, endpoints, uncertainty method and decision rule (`design.md`) before any execution.

## 2. Implementation
- [x] 2.1 Implement `experiments/h2_calibration_recipe.py`: reuse the R4 development-only loader; build the four arms; run repeated nested CV with identical outer splits; compute metrics, including a non-deprecated calibration slope and the calibration intercept; run the repeat-level paired bootstrap; write the JSON output.
- [x] 2.2 Add synthetic regression tests (`tests/test_h2_calibration_recipe.py`). Acceptance: the tests pass with no dataset read and no deprecation warning from the slope estimator. Result: 17/17 pass.

## 3. Execution
- [x] 3.1 Run the experiment on the 242 development rows. Acceptance: exactly 242 rows are used. Result: 242 rows, 241 groups, exit 0.
- [x] 3.2 Verify reproducibility. Acceptance: a second full run gives identical result content. Result: identical (`0c8b7588…`).
- [x] 3.3 Verify production isolation. Acceptance: the artifact integrity check passes. Result: passes.

## 4. Reporting
- [x] 4.1 Write `reports/h2_calibration_recipe.md`, covering the per-arm verdicts under the pre-registered rule, uncertainty and limitations.

## Outcome
No arm met the pre-registered rule, so H2 is not supported as stated. Descriptively, pooled OOF calibration (arms C and D) moved the calibration slope from 1.29 to 1.02 in 10/10 repeats (signed Δslope 95% CI [−0.335, −0.217]) at no AUC cost, while class weighting had no effect. A confirmatory study is proposed in the report, §9.
