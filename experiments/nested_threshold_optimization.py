"""
CardioVanta — Nested Threshold Optimisation Investigation
=========================================================
Research-only script evaluating whether tuning the decision threshold
for the authoritative production Logistic Regression baseline improves
nested out-of-fold accuracy beyond the fixed 0.50 threshold while maintaining
recall above 85%.

Protocol:
- Uses ONLY the 242 development samples (dev_indices.json).
- Never loads, evaluates, or participates in the 61-sample locked test set.
- Duplicate-aware 5x5 StratifiedGroupKFold nested cross-validation (241 unique groups).
- Inner folds select threshold t* ∈ [0.35, 0.65] maximising inner accuracy s.t. recall >= 0.85.
- Tie-break: chooses the candidate threshold closest to 0.50.
- Preprocessing and probability calibration fitted strictly within training partitions.
- Output written to experiments/results/nested_threshold_optimization.json.
- Production artifacts remain 100% untouched.
"""

import sys
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, recall_score, precision_score, roc_auc_score,
    f1_score, brier_score_loss, log_loss, confusion_matrix
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import clone

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.advanced_model_search import load_dev_data
from experiments.next_research_phase_90pct import build_candidates

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Bounded threshold grid (31 candidate cutoffs spaced by 0.01)
THRESHOLD_GRID = np.round(np.arange(0.35, 0.655, 0.01), 2)


def compute_metrics(y_true, y_pred, y_prob):
    """
    Computes standard diagnostic classification metrics.
    """
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = [int(v) for v in cm.ravel()]
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "correct_samples": int(np.sum(y_true == y_pred)),
        "total_samples": len(y_true),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": spec,
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob)),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp}
    }


def select_best_threshold(y_true, in_probs, grid=THRESHOLD_GRID, min_recall=0.85):
    """
    Selects the threshold that maximises ordinary accuracy subject to recall >= min_recall.
    Tie-breaking rule: prefers the candidate threshold closest to 0.50, then higher recall, then lower threshold.
    """
    candidates = []
    for t in grid:
        preds = (in_probs >= t).astype(int)
        acc = float(accuracy_score(y_true, preds))
        rec = float(recall_score(y_true, preds, zero_division=0))
        prec = float(precision_score(y_true, preds, zero_division=0))
        dist_to_half = float(abs(t - 0.50))
        candidates.append({
            "threshold": float(t),
            "accuracy": acc,
            "recall": rec,
            "precision": prec,
            "dist_to_0.50": dist_to_half,
            "meets_recall_constraint": rec >= min_recall
        })

    # Filter by recall constraint
    feasible = [c for c in candidates if c["meets_recall_constraint"]]
    if not feasible:
        # Fallback to candidate that maximizes recall
        feasible = sorted(candidates, key=lambda x: x["recall"], reverse=True)

    # Sort key: accuracy DESC, distance to 0.50 ASC, recall DESC, threshold ASC
    feasible.sort(key=lambda x: (-x["accuracy"], x["dist_to_0.50"], -x["recall"], x["threshold"]))
    winner = feasible[0]
    return winner, candidates


def evaluate_nested_threshold(X_dev, y_dev, dev_groups, n_outer_splits=5, n_inner_splits=5):
    """
    Executes true duplicate-aware 5x5 Nested Cross-Validation for Threshold Optimization.
    """
    candidates = build_candidates()
    baseline_info = candidates["Candidate 1: Frozen Baseline (StandardScaler + LR C=0.1 balanced)"]
    pipeline = baseline_info["pipeline"]

    outer_cv = StratifiedGroupKFold(n_splits=n_outer_splits)

    tuned_oof_preds = np.zeros(len(y_dev), dtype=int)
    base_oof_preds = np.zeros(len(y_dev), dtype=int)
    oof_probs = np.zeros(len(y_dev), dtype=float)

    outer_fold_records = []
    base_fold_records = []

    t_start = time.time()

    print("=" * 80)
    print("CARDIOVANTA: NESTED THRESHOLD OPTIMISATION INVESTIGATION")
    print("=" * 80)
    print(f"Development Set Size: N={len(X_dev)} (Locked Test Set Strictly Excluded)")
    print(f"Unique Patient Groups: {len(np.unique(dev_groups))}")
    print(f"Threshold Grid: {len(THRESHOLD_GRID)} cutoffs in [{THRESHOLD_GRID[0]:.2f}, {THRESHOLD_GRID[-1]:.2f}]")
    print("Selection Rule: Maximize Inner Accuracy s.t. Recall >= 0.85 | Tie-break: Closest to 0.50\n")

    for fold_i, (tr_idx, val_idx) in enumerate(outer_cv.split(X_dev, y_dev, groups=dev_groups)):
        t_fold = time.time()

        # Strict outer group isolation check
        outer_overlap = set(dev_groups[tr_idx]).intersection(set(dev_groups[val_idx]))
        assert len(outer_overlap) == 0, f"Outer fold {fold_i} group leakage: {outer_overlap}"

        X_tr = X_dev.iloc[tr_idx].reset_index(drop=True)
        y_tr = y_dev[tr_idx]
        g_tr = dev_groups[tr_idx]

        X_val = X_dev.iloc[val_idx].reset_index(drop=True)
        y_val = y_dev[val_idx]

        # Inner Loop: evaluate baseline across 5 inner folds to obtain unbiased inner out-of-fold probabilities
        inner_cv = StratifiedGroupKFold(n_splits=n_inner_splits)
        in_probs = np.zeros(len(y_tr), dtype=float)

        for in_tr_idx, in_val_idx in inner_cv.split(X_tr, y_tr, groups=g_tr):
            # Strict inner group isolation check
            in_overlap = set(g_tr[in_tr_idx]).intersection(set(g_tr[in_val_idx]))
            assert len(in_overlap) == 0, f"Inner fold group leakage: {in_overlap}"

            X_in_tr = X_tr.iloc[in_tr_idx].reset_index(drop=True)
            y_in_tr = y_tr[in_tr_idx]
            g_in_tr = g_tr[in_tr_idx]

            X_in_val = X_tr.iloc[in_val_idx].reset_index(drop=True)

            cal_splits = list(StratifiedGroupKFold(n_splits=n_inner_splits).split(X_in_tr, y_in_tr, groups=g_in_tr))
            calibrator = CalibratedClassifierCV(estimator=clone(pipeline), method="sigmoid", cv=cal_splits)
            calibrator.fit(X_in_tr, y_in_tr)
            in_probs[in_val_idx] = calibrator.predict_proba(X_in_val)[:, 1]

        # Select threshold strictly from inner out-of-fold predictions
        winner_thresh, all_thresh_eval = select_best_threshold(y_tr, in_probs, grid=THRESHOLD_GRID, min_recall=0.85)
        selected_t = winner_thresh["threshold"]

        # Retrain baseline model and calibrator on the entire outer training partition
        cal_splits_outer = list(StratifiedGroupKFold(n_splits=n_outer_splits).split(X_tr, y_tr, groups=g_tr))
        outer_calibrator = CalibratedClassifierCV(estimator=clone(pipeline), method="sigmoid", cv=cal_splits_outer)
        outer_calibrator.fit(X_tr, y_tr)

        val_probs = outer_calibrator.predict_proba(X_val)[:, 1]
        oof_probs[val_idx] = val_probs

        val_tuned_preds = (val_probs >= selected_t).astype(int)
        val_base_preds = (val_probs >= 0.50).astype(int)

        tuned_oof_preds[val_idx] = val_tuned_preds
        base_oof_preds[val_idx] = val_base_preds

        fold_tuned_metrics = compute_metrics(y_val, val_tuned_preds, val_probs)
        fold_base_metrics = compute_metrics(y_val, val_base_preds, val_probs)

        elapsed_fold = time.time() - t_fold
        print(f"Outer Fold {fold_i + 1}/{n_outer_splits} (Train N={len(X_tr)}, Val N={len(X_val)}):")
        print(f"  Selected Threshold: t* = {selected_t:.2f} (Inner Acc: {winner_thresh['accuracy']:.4f}, Inner Rec: {winner_thresh['recall']:.4f})")
        print(f"  Outer Tuned Acc:   {fold_tuned_metrics['accuracy']:.4f} | Recall: {fold_tuned_metrics['recall']:.4f}")
        print(f"  Outer Base Acc:    {fold_base_metrics['accuracy']:.4f} | Recall: {fold_base_metrics['recall']:.4f}")
        print(f"  Fold Time:         {elapsed_fold:.2f}s\n")

        outer_fold_records.append({
            "fold": fold_i + 1,
            "test_samples": len(y_val),
            "selected_threshold": selected_t,
            "inner_selection_metrics": winner_thresh,
            "outer_tuned_metrics": fold_tuned_metrics,
            "outer_baseline_metrics": fold_base_metrics,
            "elapsed_seconds": round(elapsed_fold, 2)
        })
        base_fold_records.append({
            "fold": fold_i + 1,
            "outer_metrics": fold_base_metrics
        })

    total_elapsed = time.time() - t_start

    # Pooled outer out-of-fold metrics across entire 242-patient dev set
    pooled_tuned = compute_metrics(y_dev, tuned_oof_preds, oof_probs)
    pooled_base = compute_metrics(y_dev, base_oof_preds, oof_probs)

    # Summarize fold-level variability
    def summarize_fold_variability(fold_records, key="outer_tuned_metrics"):
        metrics_keys = ["accuracy", "recall", "specificity", "precision", "f1_score", "roc_auc", "brier_score", "log_loss"]
        variability = {}
        for k in metrics_keys:
            vals = [f[key][k] for f in fold_records]
            variability[k] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "fold_values": [float(v) for v in vals]
            }
        return variability

    tuned_variability = summarize_fold_variability(outer_fold_records, "outer_tuned_metrics")
    base_variability = summarize_fold_variability(outer_fold_records, "outer_baseline_metrics")

    comparison = {
        "accuracy_diff": pooled_tuned["accuracy"] - pooled_base["accuracy"],
        "correct_samples_diff": pooled_tuned["correct_samples"] - pooled_base["correct_samples"],
        "recall_diff": pooled_tuned["recall"] - pooled_base["recall"],
        "specificity_diff": pooled_tuned["specificity"] - pooled_base["specificity"],
        "precision_diff": pooled_tuned["precision"] - pooled_base["precision"],
        "f1_score_diff": pooled_tuned["f1_score"] - pooled_base["f1_score"],
        "roc_auc_diff": pooled_tuned["roc_auc"] - pooled_base["roc_auc"],
        "brier_score_diff": pooled_tuned["brier_score"] - pooled_base["brier_score"],
        "log_loss_diff": pooled_tuned["log_loss"] - pooled_base["log_loss"]
    }

    selected_thresholds = [f["selected_threshold"] for f in outer_fold_records]

    return {
        "threshold_tuned_procedure": {
            "pooled_outer_metrics": pooled_tuned,
            "fold_variability": tuned_variability,
            "selected_thresholds_per_fold": selected_thresholds,
            "outer_folds": outer_fold_records
        },
        "authoritative_baseline_fixed_0_50": {
            "pooled_outer_metrics": pooled_base,
            "fold_variability": base_variability
        },
        "comparison_vs_baseline": comparison,
        "total_elapsed_seconds": round(total_elapsed, 2)
    }


def main():
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, file_hash = load_dev_data()

    results = evaluate_nested_threshold(X_dev, y_dev, dev_groups)

    pooled_tuned = results["threshold_tuned_procedure"]["pooled_outer_metrics"]
    pooled_base = results["authoritative_baseline_fixed_0_50"]["pooled_outer_metrics"]
    comp = results["comparison_vs_baseline"]

    target_accuracy = 0.90
    target_recall = 0.85
    target_reached = (pooled_tuned["accuracy"] >= target_accuracy) and (pooled_tuned["recall"] >= target_recall)

    summary = {
        "experiment_title": "CardioVanta Nested Threshold Optimisation Investigation",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_hash": file_hash,
        "dev_samples": len(X_dev),
        "locked_test_samples_used": 0,
        "target_accuracy": target_accuracy,
        "target_recall": target_recall,
        "target_reached": target_reached,
        "threshold_grid_bounds": [float(THRESHOLD_GRID[0]), float(THRESHOLD_GRID[-1])],
        "threshold_grid_size": len(THRESHOLD_GRID),
        "tuned_pooled_accuracy": pooled_tuned["accuracy"],
        "tuned_correct_samples": pooled_tuned["correct_samples"],
        "tuned_pooled_recall": pooled_tuned["recall"],
        "baseline_pooled_accuracy": pooled_base["accuracy"],
        "baseline_correct_samples": pooled_base["correct_samples"],
        "baseline_pooled_recall": pooled_base["recall"],
        "accuracy_gain_over_baseline": comp["accuracy_diff"],
        "correct_samples_gain": comp["correct_samples_diff"],
        "selected_thresholds": results["threshold_tuned_procedure"]["selected_thresholds_per_fold"],
        "research_history_limitation": (
            "The threshold search strategy and grid bounds were informed by prior exploratory error analysis "
            "on this 242-patient development set. Therefore, this nested cross-validation evaluates the out-of-fold "
            "generalization of the threshold selection procedure within this cohort, but does NOT represent "
            "independent external validation on an unseen clinical site."
        ),
        "evaluation_results": results
    }

    out_file = RESULTS_DIR / "nested_threshold_optimization.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("=" * 80)
    print("NESTED THRESHOLD OPTIMISATION SUMMARY & VERDICT")
    print("=" * 80)
    print(f"Target 90%+ Accuracy Reached: {target_reached}")
    print(f"Selected Thresholds per Fold: {summary['selected_thresholds']}")
    print(f"Tuned Pooled Accuracy:        {pooled_tuned['accuracy']:.4f} ({pooled_tuned['correct_samples']}/{pooled_tuned['total_samples']})")
    print(f"Baseline (0.50) Accuracy:     {pooled_base['accuracy']:.4f} ({pooled_base['correct_samples']}/{pooled_base['total_samples']})")
    print(f"Accuracy Delta:               {comp['accuracy_diff']:+.4f} ({comp['correct_samples_diff']:+d} samples)")
    print(f"Tuned Pooled Recall:          {pooled_tuned['recall']:.4f} (Base: {pooled_base['recall']:.4f})")
    print(f"Tuned Pooled Specificity:     {pooled_tuned['specificity']:.4f} (Base: {pooled_base['specificity']:.4f})")
    print(f"Tuned Pooled Precision:       {pooled_tuned['precision']:.4f} (Base: {pooled_base['precision']:.4f})")
    print(f"Tuned Pooled F1:              {pooled_tuned['f1_score']:.4f} (Base: {pooled_base['f1_score']:.4f})")
    print(f"Results serialized to: {out_file}\n")


if __name__ == "__main__":
    main()
