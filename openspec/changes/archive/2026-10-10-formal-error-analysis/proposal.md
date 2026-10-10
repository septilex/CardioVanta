# Proposal: Formal Error Analysis

## Problem
The global nested-CV model selection phase is complete, and the LR_production (C=0.1, class_weight='balanced') candidate was selected. The 95% accuracy target was not achieved. We need to systematically understand the remaining errors to form hypotheses for future improvements without modifying the frozen model or searching for new models.

## Proposed Solution
Perform a formal, diagnostic error analysis. The analysis will categorize and dissect false positives and false negatives, examine borderline probability distributions, and isolate feature-level patterns associated with errors. 

## Scope
- Write a Python script to perform the diagnostic error analysis.
- Produce `reports/error_analysis.md` mapping all diagnostic findings.
- Ensure strict separation between development-set out-of-fold diagnostic evidence and locked-test post-hoc descriptions.
- No model tuning, hyperparameter updates, or threshold optimizations will be performed.
