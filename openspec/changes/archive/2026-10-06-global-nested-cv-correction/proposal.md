# Proposal

## Why

The current nested CV evaluates model families independently and selects the best family globally using their outer out-of-fold (OOF) scores. This is not fully nested, as the global model selection step relies on cross-validated scores, potentially causing selection bias.

## What Changes

- Complete candidate-space inner selection.
- Grouped outer CV and inner CV ensuring strict duplicate isolation.
- Locked test isolation.
- Deterministic reproducibility and dependency capture.
- Corrected reporting language.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- None

## Impact

- `experiments/advanced_model_search.py` will be rewritten to apply global nested CV.
- `reports/advanced_ml_performance_investigation.md` will be updated with global evaluation results.
