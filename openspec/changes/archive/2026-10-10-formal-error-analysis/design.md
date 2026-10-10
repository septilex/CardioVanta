# Design: Formal Error Analysis

## Architecture
- `experiments/formal_error_analysis.py`: Python script utilizing `pandas`, `sklearn`, and the existing `load_dev_data` and `load_locked_test_data` utilities to generate error diagnostics for the selected `LR_production` model configuration.
- `reports/error_analysis.md`: Detailed markdown report systematically breaking down errors per the specified criteria, segregating FACT, OBSERVATION, INTERPRETATION, and LIMITATION.
- `tests/test_error_analysis.py`: Validates the isolation and determinism of the error analysis script.

## Technical Details
- The analysis script will train the baseline LR on out-of-fold data and extract feature coefficients, test probabilities, and confusion matrices.
- The 13 clinical features will be individually assessed against the error types (FP/FN) to identify subpopulation discrepancies or overlapping distributions.
- No dataset mutations or production file edits will be performed.
