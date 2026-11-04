# Tasks

## 1. Design
- [x] 1.1 Specify the profiles, perturbations, metrics and analytical expectations (`design.md`) before execution.

## 2. Implementation
- [x] 2.1 Implement `experiments/r5_explanation_stability.py`: registry loading, the profile generator, perturbations, metrics and the JSON output.
- [x] 2.2 Add synthetic regression tests (`tests/test_r5_explanation_stability.py`). Acceptance: the tests pass with no dataset read. Result: 8/8 pass.

## 3. Execution
- [x] 3.1 Run the experiment. Acceptance: exit 0 and 100 profiles evaluated. Result: 3,562 perturbations.
- [x] 3.2 Run it a second time. Acceptance: identical result content, excluding runtime. Result: identical (`94c30837…`).
- [x] 3.3 Verify artifact integrity. Acceptance: `scripts/verify_artifact_integrity.py` passes.

## 4. Reporting
- [x] 4.1 Write `reports/r5_explanation_stability.md`, covering the findings, the checked expectations and limitations.
