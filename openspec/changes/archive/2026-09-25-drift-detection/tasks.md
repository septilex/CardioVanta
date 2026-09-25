# Tasks

## 1. Setup and Synthetic Data Generation

- [x] 1.1 Create synthetic data generator (e.g., `tests/test_drift_data_gen.py`) to produce controlled JSON log exports and verify it accurately outputs JSON log files matching the Phase 15A schema without containing raw 13-feature clinical inputs.

## 2. Drift Detection Script Implementation

- [x] 2.1 Create `scripts/detect_drift.py` with logic to establish the baseline distribution by loading the 242 development set prediction probabilities (protecting the 61 locked test samples), and verify the script isolates the baseline array.
- [x] 2.2 Implement a permutation or resampling-based Kolmogorov-Smirnov (KS) test in `scripts/detect_drift.py` to compare log inputs against the baseline while explicitly handling ties and constant probabilities deterministically, and verify the effect size and p-value calculate correctly.
- [x] 2.3 Implement the 50-observation minimum operational eligibility threshold and support-boundary violation rate check, and verify the script safely aborts and declares "insufficient evidence" when fewer than 50 valid prediction events are provided.
- [x] 2.4 Implement report generation logic to declare statistical drift only when eligibility, statistical evidence, and meaningful effect size are all met, outputting a disclaimer that concept drift/performance degradation cannot be measured, and verify the output format.

## 3. Testing and Validation

- [x] 3.1 Create `tests/test_drift_detection.py` covering all required scenarios against the offline script: no-drift synthetic control, clear synthetic drift, borderline drift, below-minimum window, exact minimum window, ties/constant probabilities, malformed telemetry, invalid-event filtering, deterministic output, locked-test protection, and repeated-monitoring behavior. Verify `pytest tests/test_drift_detection.py` passes 100%.

