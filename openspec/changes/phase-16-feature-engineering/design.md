# Design

## Context

The evaluated baseline model achieved 86.89% accuracy on the existing 61-observation locked test (TN=22, FP=6, FN=2, TP=31). The current experiments do not establish a theoretical accuracy ceiling or determine whether 95% accuracy is achievable. Formal error analysis (Phase 15) identified that the model struggles to correctly identify heart disease in patients with lower maximum heart rates (False Negatives), suggesting that adjusting `thalach` by `age` could be an informative exploratory hypothesis. It also struggles with `oldpeak` non-linearities. The current preprocessing uses simple standard scaling and one-hot encoding. We must maintain duplicate-aware grouping, fold-local calibration, and strict isolation of the locked test set.

## Goals / Non-Goals

**Goals:**
- **Research Question 1**: Determine if a nonlinear representation of `thalach` or an `age` × `thalach` interaction improves performance.
- **Research Question 2**: Determine if a nonlinear representation (binning/polynomials) of `oldpeak` improves performance.
- Maintain leakage prevention controls via fold-local preprocessing and duplicate-aware grouping, requiring implementation and tests to demonstrate that those controls are correctly enforced.
- Acknowledge that previously observed locked-test error patterns are exploratory hypotheses, not independent confirmation. Development-set nested cross-validation is the primary basis for Phase 16 candidate comparison. Candidate definitions and selection rules are frozen before the final locked-test assessment, which is strictly retrospective with its prior inspection disclosed.
- Ensure the locked test set remains excluded from candidate selection and feature tuning. Stronger independent generalization claims will require genuinely independent external validation.

**Non-Goals:**
- Implementing these changes into production artifacts.
- Tuning the baseline production model thresholds on the test set.
- Unrestricted automated feature generation or uncontrolled feature explosion.

## Decisions

- **Controlled Experiment Space**: We will evaluate a small, explicit set of pipelines:
  1. Frozen Production Reference (Current preprocessing + LR, where `cp` is inherently one-hot encoded).
  2. Interaction Representation: `thalach` × `age` interaction (baseline handles remaining preprocessing).
  3. Non-linear Representation: `oldpeak` squared (baseline handles remaining).
  4. Combined Representation: Both interaction and non-linear terms simultaneously, to test if addressing both identified error mechanisms works synergistically.
- **Evaluation Methodology**:
  1. Define the 4-candidate space and selection procedure prior to running experiments.
  2. In each outer fold, conduct candidate selection using only the outer-training data `(X_tr, y_tr, g_tr)` via inner 5-fold `StratifiedGroupKFold`.
  3. Fit the inner-selected pipeline on `(X_tr, y_tr)` and calibrate its probabilities fold-locally using sigmoid calibration with duplicate-aware splits (`StratifiedGroupKFold(5)` on `g_tr`). Outer validation observations `(X_val, y_val)` are strictly excluded from calibration fitting.
  4. In parallel, fit and calibrate the frozen baseline pipeline on the identical outer-training data `(X_tr, y_tr)` using the identical duplicate-aware calibration split procedure.
  5. Evaluate both the selected procedure and the baseline on the isolated outer validation fold `X_val` once, generating calibrated probabilities and class predictions using the predefined threshold policy (`prob >= 0.5`).
  6. Aggregate outer validation fold predictions across all N=242 development samples to evaluate the complete selection procedure against the baseline on identical outer splits.
  7. After the selection procedure is evaluated across all outer folds, determine the single final candidate by executing the established selection rule on the complete development dataset `(X_dev, y_dev, dev_groups)`, then fit and calibrate that final pipeline on the full development set.
  8. Perform a single retrospective locked-test evaluation on the 61-row test set using this frozen final model, acknowledging prior inspection during Phase 15 formal error analysis.

- **Separation of Evaluation Stages**:
  - **A. Candidate Ranking (Inner CV)**: Candidate selection within each inner cross-validation loop is explicitly defined using raw (uncalibrated) inner out-of-fold ROC-AUC. While a single strictly increasing monotonic transformation preserves the rank order of individual predictions, fold-specific `CalibratedClassifierCV` models fit separate sigmoids across folds and average them, which does not mathematically guarantee identical pooled out-of-fold rankings. Defining candidate selection explicitly on raw inner-CV ROC-AUC decouples representation ranking from calibration fitting, maintains a simple and reproducible ranking criterion, and avoids redundant nested calibration during model selection.
  - **B. Probability Calibration**: Sigmoid probability calibration is fitted *after* candidate selection at the outer-training level, using only the applicable outer-training partition `(X_tr, y_tr, g_tr)`. Calibrators are fitted using `CalibratedClassifierCV(estimator=selected_pipe, method='sigmoid', cv=cal_splits)` where `cal_splits` is explicitly constructed via `StratifiedGroupKFold(5)` on outer-training groups `g_tr` to guarantee duplicate-aware grouping and training-fold isolation. Scikit-learn default integer `cv=5` must NEVER be used (as it ignores groups and leaks duplicate rows across calibration folds). The frozen baseline pipeline is fitted and calibrated fold-locally using the identical procedure and splits on the same outer-training partition. No outer-validation observations participate in calibration fitting, and the production model artifact `artifacts/model/model.joblib` must never be reused for validation folds (as it was trained on the entire development dataset).
  - **C. Threshold Policy**: Class predictions are determined using a fixed, predefined mathematical threshold of `0.5` applied to the calibrated probability (`P(y=1) >= 0.5`), consistent with `test_optional_threshold_application` and `metadata.json`. This threshold is an experimental mathematical evaluation threshold, not a clinically validated production threshold. No threshold is tuned on outer validation folds or on the locked test set.
  - **D. Outer-Fold Evaluation**: Predictions on outer validation folds evaluate the generalizability of the entire selection-and-calibration procedure. Outer folds are never used as a leaderboard to pick individual candidates.
  - **E. Final Locked-Test Evaluation**: Evaluated exactly once on the final selected model after freezing the selection procedure and pipeline. Because the locked-test set was previously inspected during Phase 15 formal error analysis and those observations motivated the Phase 16 hypotheses, this evaluation is retrospective rather than independent confirmation, and the test set is not described as pristine or strictly confirmatory. Development-set nested CV remains the primary basis for candidate comparison, and independent external data are required for stronger independent generalization claims.

- **Metrics**: Primary: Accuracy (outer CV at threshold 0.5). Secondary: ROC-AUC, average precision, precision, recall, specificity, F1, Brier score, and log loss.
- **Selection Criterion and Tie-Break (Inner CV)**: Candidate selection within each inner fold is strictly frozen prior to experiment execution:
  - *Primary Criterion*: Highest inner out-of-fold ROC-AUC on raw (uncalibrated) candidate scores.
  - *Tie-Break Metric*: Simpler representation when ROC-AUC differences fall within a predefined numerical tolerance.
  - *Numerical Tolerance ($\epsilon$)*: $\Delta \text{ROC-AUC} \le 1\times 10^{-4}$ (0.0001). Any candidate whose inner ROC-AUC is within 0.0001 of the top score is considered tied.
  - *Simplicity Ordering (from simplest to most complex)*:
    1. Candidate 1: Frozen Production Reference (0 additional features).
    2. Candidate 2: Interaction `thalach` × `age` (1 additional feature).
    3. Candidate 3: Non-linear `oldpeak` squared (1 additional feature).
    4. Candidate 4: Combined interaction and non-linear terms (2 additional features).
    *(Between Candidates 2 and 3, which each introduce 1 additional term, Candidate 2 is preferred by predefined convention).*
  - *Decision*: Select the candidate with the lowest simplicity rank (simplest model) within the 0.0001 ROC-AUC tie tolerance of the best candidate. Classification accuracy is deliberately excluded as a tie-breaker because accuracy depends on an arbitrary threshold, whereas ROC-AUC measures discrimination across all thresholds.
- **Adoption Criterion (Outer CV)**: An adoption gate is applied to the complete selection procedure. It must improve aggregate outer out-of-fold accuracy over the calibrated baseline by at least 1.5 percentage points (absolute increase evaluated on identical outer splits) while maintaining aggregate recall above 0.85. Both procedures receive the exact same calibration and threshold treatment on identical splits. These thresholds represent practical engineering adoption criteria rather than proof of statistical significance. Outer CV is strictly an evaluation mechanism for the procedure, not a candidate selection leaderboard.
- **Leakage Prevention Controls**: The design specifies architectural controls intended to prevent data leakage:
  - All learned preprocessing and representations must be fitted fold-locally within outer-training partitions.
  - Probability calibration must be fitted using only outer-training data via precomputed `StratifiedGroupKFold(5)` splits on training groups $g_{\text{tr}}$.
  - The production model artifact (`artifacts/model/model.joblib`) must never be reused to generate outer-fold predictions.
  - Outer validation observations never participate in preprocessing, candidate selection, model fitting, or calibrator fitting.
  - Baseline and experimental procedures receive consistent calibration and threshold treatment.
  - Implementation code and dedicated tests must demonstrate that these controls are correctly enforced before treating the evaluation as verified leak-free.
  - The locked test set is used strictly for a single retrospective evaluation after candidate selection is frozen, without threshold tuning.

## Risks / Trade-offs

- **Small Dataset Size** -> *Mitigation*: The sample size is small (N=242 dev, 61 test). Any observed performance difference might be due to chance. We will report nested-CV variance and explicitly document this limitation. The adoption criteria (+1.5 pp accuracy gain, recall > 0.85) are practical decision heuristics, not proof of statistical significance. The current experiments do not establish a theoretical accuracy ceiling or determine whether 95% accuracy is achievable; we do not claim that 95% accuracy is achievable or impossible.
- **Feature Engineering Overfitting** -> *Mitigation*: Restrict to a heavily constrained, theoretically justified set of 3-4 feature hypotheses rather than automated combinations.
- **Reporting Bias / Adaptivity** -> *Mitigation*: We will transparently report both positive and negative results, and recognize that individual outer-fold scores are merely components of an unbiased estimate of the entire procedure. We will not use outer-fold results to choose which individual feature representation wins and then report those same outer results as an unbiased evaluation. Adapting the design after seeing the results invalidates the estimates.
