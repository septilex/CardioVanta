# Design

## Context
See proposal.md.

## Goals / Non-Goals
**Goals**:
- Implement global nested CV where candidate selection occurs over the complete valid search space within the inner CV.
- Exclude stacking unless group-safe (it isn't natively).

**Non-Goals**:
- No modifications to production model.
- No exhaustive search outside current predefined 97 candidates.

## Decisions
- Structure:
  OUTER StratifiedGroupKFold
  → For each outer training fold: evaluate all 97 configurations using INNER StratifiedGroupKFold.
  → Select the ONE best configuration based on Inner ROC-AUC (and Inner Accuracy as tiebreaker).
  → Fit selected config on full outer training fold.
  → Evaluate on untouched outer validation fold.
- Stacking is EXCLUDED since `StackingClassifier` lacks native support for strict group-safe CV across duplicate rows without complex hacks.

## Risks / Trade-offs
- Computationally expensive: 97 configs × 5 inner folds × 5 outer folds = 2,425 fits. We accept this cost for valid results.
