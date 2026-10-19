# Tasks

## 1. Baseline Experiment Setup

- [x] 1.1 Create `experiments/phase_16_feature_engineering.py` and verify it successfully loads the dev data and groups without locked-test leakage.
- [x] 1.2 Implement the 4 explicitly enumerated preprocessing pipelines (Baseline, Interaction (`thalach` × `age`), Non-linear (`oldpeak` squared), Combined) as sklearn `Pipeline` objects and verify they can fit on a subset of data.

## 2. Evaluation Methodology

- [x] 2.1 Implement the Global Nested-CV loop using `StratifiedGroupKFold` for the 4 pipelines: rank candidates in inner CV via uncalibrated ROC-AUC using the predefined 0.0001 tie tolerance and simplicity hierarchy, calibrate the selected pipeline and baseline fold-locally using sigmoid scaling with duplicate-aware group splits on outer-training data, apply the fixed 0.5 threshold policy, and implement verification tests to demonstrate that calibration isolation controls are correctly enforced.
- [x] 2.2 Record outer-fold metrics (calibrated Brier score, log loss, ROC-AUC, avg precision, and threshold-0.5 accuracy, precision, recall, specificity, F1) for both the selected procedure and the baseline on identical outer splits, saving results to JSON.

## 3. Results Analysis & Acceptance

- [x] 3.1 Aggregate outer-fold results across all 242 development samples to evaluate the complete selection procedure. Verify that aggregate accuracy (requiring at least a +1.5 pp absolute gain) and aggregate recall (> 0.85) are compared against the calibrated baseline on identical outer splits.
- [x] 3.2 Determine the single final candidate by applying the inner-selection rule to the complete dev set. Fit and calibrate this final pipeline on full dev data with group-aware calibration splits, evaluate retrospectively on the 61-row locked test set exactly once, disclose the Phase 15 inspection history (clarifying that this is not independent confirmation), and save metrics to `experiments/results/phase_16_results.json`.
- [x] 3.3 Create a markdown report detailing the findings, limitations, baseline comparability, provenance of the experiment, and report all negative as well as positive results. Verify it does not make unsupported clinical validity claims, theoretical accuracy-ceiling claims, or assertions that 95% accuracy is either achievable or impossible.
