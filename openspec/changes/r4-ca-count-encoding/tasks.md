# Tasks

## 1. Pre-registration
- [x] 1.1 Record the hypothesis, arms, metrics and decision rule (`design.md`) before running the experiment.

## 2. Implementation
- [x] 2.1 Implement `experiments/r4_ca_count_encoding.py`: a development-only line-filtered loader, the two arms, repeated nested CV, metrics, the paired bootstrap and JSON output.
- [x] 2.2 Add synthetic regression tests (`tests/test_r4_ca_count_encoding.py`). Acceptance: the tests pass without reading any dataset. Result: 18/18 pass.

## 3. Execution
- [x] 3.1 Run the experiment. Acceptance: exactly 242 rows are used and no locked line is parsed. Result: 242 rows, 241 duplicate groups.
- [x] 3.2 Verify reproducibility. Acceptance: a second run gives identical result content. Result: identical (`495c4496…`).
- [x] 3.3 Verify production isolation. Acceptance: the artifact integrity check passes after the runs. Result: passes.

## 4. Reporting
- [x] 4.1 Write `reports/r4_ca_count_encoding.md`, covering the verdict under the pre-registered rule, uncertainty and limitations.

## Outcome
H1 was not supported under the pre-registered rule (primary and secondary analyses), so the production encoding is retained. The proposed next hypothesis (H2, calibration of the production recipe) is in the report, §9.
