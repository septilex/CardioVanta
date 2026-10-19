"""
CardioVanta — Nested Evaluation of Shrinkage LDA
===============================================
Research-only script evaluating whether regularized Linear Discriminant Analysis
(LDA) with Ledoit-Wolf covariance shrinkage improves upon the authoritative
calibrated Logistic Regression baseline on the 242-patient Cleveland development set.

Compares three fixed candidates:
1. Candidate 1: Calibrated Logistic Regression baseline (C=0.1, class_weight='balanced', threshold 0.50).
2. Candidate 2: Empirical LDA (solver='lsqr', shrinkage=None).
3. Candidate 3: Shrinkage LDA (solver='lsqr', shrinkage='auto').

Protocol:
- Uses ONLY the 242 development samples (dev_indices.json).
- Never loads, evaluates, or participates in the 61-sample locked test set.
- Duplicate-aware 5x5 StratifiedGroupKFold nested cross-validation (241 unique groups).
- All candidates calibrated using Platt sigmoid scaling fitted strictly fold-locally.
- Candidate selection decided strictly by inner out-of-fold accuracy (tie-break: ROC-AUC, then simplicity rank).
- Outer holdout folds evaluate the complete model selection procedure against the baseline.
- Production model artifacts remain 100% untouched.
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
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.base import clone

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.advanced_model_search import load_dev_data

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CONTINUOUS_COLS = ["age", "trestbps", "chol", "thalach", "oldpeak"]
BINARY_COLS = ["sex", "fbs", "exang"]
CATEGORICAL_COLS = ["cp", "restecg", "slope", "ca", "thal"]


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


def build_lda_candidates():
    """
    Constructs the three candidate pipelines using identical linear preprocessing.
    """
    prep = ColumnTransformer([
        ("num", StandardScaler(), CONTINUOUS_COLS),
        ("bin", "passthrough", BINARY_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)
    ])

    cands = {
        "Candidate 1: Calibrated Logistic Regression (Baseline)": {
            "pipeline": Pipeline([
                ("prep", prep),
                ("clf", LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=42, max_iter=1000))
            ]),
            "description": "Production baseline: L2 regularized logistic regression (C=0.1, balanced weights).",
            "simplicity_rank": 1
        },
        "Candidate 2: Empirical LDA (shrinkage=None)": {
            "pipeline": Pipeline([
                ("prep", prep),
                ("clf", LinearDiscriminantAnalysis(solver="lsqr", shrinkage=None))
            ]),
            "description": "Empirical Linear Discriminant Analysis with unregularized sample covariance.",
            "simplicity_rank": 3
        },
        "Candidate 3: Shrinkage LDA (shrinkage=auto)": {
            "pipeline": Pipeline([
                ("prep", prep),
                ("clf", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))
            ]),
            "description": "Regularized Linear Discriminant Analysis with Ledoit-Wolf automatic covariance shrinkage.",
            "simplicity_rank": 2
        }
    }
    return cands


def evaluate_nested_lda(X_dev, y_dev, dev_groups, n_outer_splits=5, n_inner_splits=5):
    """
    Executes duplicate-aware 5x5 Nested Cross-Validation comparing LDA candidates vs Baseline.
    """
    candidates = build_lda_candidates()
    baseline_key = "Candidate 1: Calibrated Logistic Regression (Baseline)"
    shrk_key = "Candidate 3: Shrinkage LDA (shrinkage=auto)"
    emp_key = "Candidate 2: Empirical LDA (shrinkage=None)"

    outer_cv = StratifiedGroupKFold(n_splits=n_outer_splits)

    sel_oof_preds = np.zeros(len(y_dev), dtype=int)
    sel_oof_probs = np.zeros(len(y_dev), dtype=float)

    base_oof_preds = np.zeros(len(y_dev), dtype=int)
    base_oof_probs = np.zeros(len(y_dev), dtype=float)

    shrk_oof_preds = np.zeros(len(y_dev), dtype=int)
    shrk_oof_probs = np.zeros(len(y_dev), dtype=float)

    emp_oof_preds = np.zeros(len(y_dev), dtype=int)
    emp_oof_probs = np.zeros(len(y_dev), dtype=float)

    outer_fold_records = []
    base_fold_records = []
    shrk_fold_records = []
    emp_fold_records = []

    t_start = time.time()

    print("=" * 80)
    print("CARDIOVANTA: NESTED EVALUATION OF SHRINKAGE LDA")
    print("=" * 80)
    print(f"Development Set Size: N={len(X_dev)} (Locked Test Set Strictly Excluded)")
    print(f"Unique Patient Groups: {len(np.unique(dev_groups))}")
    print(f"Outer Splits: {n_outer_splits} | Inner Splits: {n_inner_splits}")
    print("Selection Rule: Inner Accuracy DESC -> Inner ROC-AUC DESC -> Simplicity Rank ASC\n")

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

        # Inner Loop: evaluate all candidates to obtain unbiased inner selection scores
        inner_cv = StratifiedGroupKFold(n_splits=n_inner_splits)
        inner_scores = []

        for name, cand_info in candidates.items():
            pipe = cand_info["pipeline"]
            rank = cand_info["simplicity_rank"]

            in_preds = np.zeros(len(y_tr), dtype=int)
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
                calibrator = CalibratedClassifierCV(estimator=clone(pipe), method="sigmoid", cv=cal_splits)
                calibrator.fit(X_in_tr, y_in_tr)

                p = calibrator.predict_proba(X_in_val)[:, 1]
                in_probs[in_val_idx] = p
                in_preds[in_val_idx] = (p >= 0.50).astype(int)

            in_acc = float(accuracy_score(y_tr, in_preds))
            in_rec = float(recall_score(y_tr, in_preds, zero_division=0))
            in_auc = float(roc_auc_score(y_tr, in_probs))
            in_brier = float(brier_score_loss(y_tr, in_probs))

            inner_scores.append({
                "name": name,
                "inner_accuracy": in_acc,
                "inner_recall": in_rec,
                "inner_roc_auc": in_auc,
                "inner_brier": in_brier,
                "simplicity_rank": rank
            })

        # Predefined selection rule: Accuracy DESC, ROC-AUC DESC, Simplicity Rank ASC
        inner_scores.sort(
            key=lambda x: (x["inner_accuracy"], x["inner_roc_auc"], -x["simplicity_rank"]),
            reverse=True
        )
        winner = inner_scores[0]
        winner_name = winner["name"]
        winner_pipe = candidates[winner_name]["pipeline"]

        # Retrain selected candidate and all individual candidates on full outer training partition
        cal_splits_outer = list(StratifiedGroupKFold(n_splits=n_outer_splits).split(X_tr, y_tr, groups=g_tr))

        # Selected model
        outer_cal = CalibratedClassifierCV(estimator=clone(winner_pipe), method="sigmoid", cv=cal_splits_outer)
        outer_cal.fit(X_tr, y_tr)
        p_sel = outer_cal.predict_proba(X_val)[:, 1]
        preds_sel = (p_sel >= 0.50).astype(int)
        sel_oof_probs[val_idx] = p_sel
        sel_oof_preds[val_idx] = preds_sel
        fold_sel_metrics = compute_metrics(y_val, preds_sel, p_sel)

        # Baseline model
        base_cal = CalibratedClassifierCV(estimator=clone(candidates[baseline_key]["pipeline"]), method="sigmoid", cv=cal_splits_outer)
        base_cal.fit(X_tr, y_tr)
        p_base = base_cal.predict_proba(X_val)[:, 1]
        preds_base = (p_base >= 0.50).astype(int)
        base_oof_probs[val_idx] = p_base
        base_oof_preds[val_idx] = preds_base
        fold_base_metrics = compute_metrics(y_val, preds_base, p_base)

        # Shrinkage LDA model
        shrk_cal = CalibratedClassifierCV(estimator=clone(candidates[shrk_key]["pipeline"]), method="sigmoid", cv=cal_splits_outer)
        shrk_cal.fit(X_tr, y_tr)
        p_shrk = shrk_cal.predict_proba(X_val)[:, 1]
        preds_shrk = (p_shrk >= 0.50).astype(int)
        shrk_oof_probs[val_idx] = p_shrk
        shrk_oof_preds[val_idx] = preds_shrk
        fold_shrk_metrics = compute_metrics(y_val, preds_shrk, p_shrk)

        # Empirical LDA model
        emp_cal = CalibratedClassifierCV(estimator=clone(candidates[emp_key]["pipeline"]), method="sigmoid", cv=cal_splits_outer)
        emp_cal.fit(X_tr, y_tr)
        p_emp = emp_cal.predict_proba(X_val)[:, 1]
        preds_emp = (p_emp >= 0.50).astype(int)
        emp_oof_probs[val_idx] = p_emp
        emp_oof_preds[val_idx] = preds_emp
        fold_emp_metrics = compute_metrics(y_val, preds_emp, p_emp)

        elapsed_fold = time.time() - t_fold
        print(f"Outer Fold {fold_i + 1}/{n_outer_splits} (Train N={len(X_tr)}, Val N={len(X_val)}):")
        print(f"  Selected Winner: {winner_name[:35]}")
        print(f"    Inner Acc: {winner['inner_accuracy']:.4f} | Inner AUC: {winner['inner_roc_auc']:.4f}")
        print(f"  Outer Metrics -> Selected: {fold_sel_metrics['accuracy']:.4f} | Base: {fold_base_metrics['accuracy']:.4f} | Shrk LDA: {fold_shrk_metrics['accuracy']:.4f} | Emp LDA: {fold_emp_metrics['accuracy']:.4f}")
        print(f"  Fold Time:       {elapsed_fold:.2f}s\n")

        outer_fold_records.append({
            "fold": fold_i + 1,
            "test_samples": len(y_val),
            "selected_candidate": winner_name,
            "inner_selection_metrics": winner,
            "all_inner_candidates": inner_scores,
            "outer_metrics": fold_sel_metrics,
            "elapsed_seconds": round(elapsed_fold, 2)
        })
        base_fold_records.append({"fold": fold_i + 1, "outer_metrics": fold_base_metrics})
        shrk_fold_records.append({"fold": fold_i + 1, "outer_metrics": fold_shrk_metrics})
        emp_fold_records.append({"fold": fold_i + 1, "outer_metrics": fold_emp_metrics})

    total_elapsed = time.time() - t_start

    # Pooled outer out-of-fold metrics across entire 242-patient dev set
    pooled_sel = compute_metrics(y_dev, sel_oof_preds, sel_oof_probs)
    pooled_base = compute_metrics(y_dev, base_oof_preds, base_oof_probs)
    pooled_shrk = compute_metrics(y_dev, shrk_oof_preds, shrk_oof_probs)
    pooled_emp = compute_metrics(y_dev, emp_oof_preds, emp_oof_probs)

    # Summarize fold-level variability
    def summarize_fold_variability(records):
        metrics_keys = ["accuracy", "recall", "specificity", "precision", "f1_score", "roc_auc", "brier_score", "log_loss"]
        variability = {}
        for k in metrics_keys:
            vals = [f["outer_metrics"][k] for f in records]
            variability[k] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "fold_values": [float(v) for v in vals]
            }
        return variability

    sel_variability = summarize_fold_variability(outer_fold_records)
    base_variability = summarize_fold_variability(base_fold_records)
    shrk_variability = summarize_fold_variability(shrk_fold_records)
    emp_variability = summarize_fold_variability(emp_fold_records)

    comparison_vs_baseline = {
        "nested_selection_procedure": {
            "accuracy_diff": pooled_sel["accuracy"] - pooled_base["accuracy"],
            "correct_samples_diff": pooled_sel["correct_samples"] - pooled_base["correct_samples"],
            "recall_diff": pooled_sel["recall"] - pooled_base["recall"],
            "brier_diff": pooled_sel["brier_score"] - pooled_base["brier_score"],
            "log_loss_diff": pooled_sel["log_loss"] - pooled_base["log_loss"],
        },
        "shrinkage_lda_fixed_arm": {
            "accuracy_diff": pooled_shrk["accuracy"] - pooled_base["accuracy"],
            "correct_samples_diff": pooled_shrk["correct_samples"] - pooled_base["correct_samples"],
            "recall_diff": pooled_shrk["recall"] - pooled_base["recall"],
            "brier_diff": pooled_shrk["brier_score"] - pooled_base["brier_score"],
            "log_loss_diff": pooled_shrk["log_loss"] - pooled_base["log_loss"],
        },
        "empirical_lda_fixed_arm": {
            "accuracy_diff": pooled_emp["accuracy"] - pooled_base["accuracy"],
            "correct_samples_diff": pooled_emp["correct_samples"] - pooled_base["correct_samples"],
            "recall_diff": pooled_emp["recall"] - pooled_base["recall"],
            "brier_diff": pooled_emp["brier_score"] - pooled_base["brier_score"],
            "log_loss_diff": pooled_emp["log_loss"] - pooled_base["log_loss"],
        }
    }

    selected_distribution = {}
    for f in outer_fold_records:
        cand = f["selected_candidate"]
        selected_distribution[cand] = selected_distribution.get(cand, 0) + 1

    return {
        "nested_selection_procedure": {
            "pooled_outer_metrics": pooled_sel,
            "fold_variability": sel_variability,
            "selected_candidates_distribution": selected_distribution,
            "outer_folds": outer_fold_records
        },
        "authoritative_baseline_lr": {
            "pooled_outer_metrics": pooled_base,
            "fold_variability": base_variability
        },
        "shrinkage_lda_fixed_arm": {
            "pooled_outer_metrics": pooled_shrk,
            "fold_variability": shrk_variability
        },
        "empirical_lda_fixed_arm": {
            "pooled_outer_metrics": pooled_emp,
            "fold_variability": emp_variability
        },
        "comparison_vs_baseline": comparison_vs_baseline,
        "total_elapsed_seconds": round(total_elapsed, 2)
    }


def main():
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, file_hash = load_dev_data()

    results = evaluate_nested_lda(X_dev, y_dev, dev_groups)

    pooled_sel = results["nested_selection_procedure"]["pooled_outer_metrics"]
    pooled_base = results["authoritative_baseline_lr"]["pooled_outer_metrics"]
    pooled_shrk = results["shrinkage_lda_fixed_arm"]["pooled_outer_metrics"]
    pooled_emp = results["empirical_lda_fixed_arm"]["pooled_outer_metrics"]

    target_accuracy = 0.90
    target_recall = 0.85
    target_reached = (pooled_sel["accuracy"] >= target_accuracy) and (pooled_sel["recall"] >= target_recall)

    summary = {
        "experiment_title": "CardioVanta Nested Evaluation of Shrinkage LDA",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_hash": file_hash,
        "dev_samples": len(X_dev),
        "locked_test_samples_used": 0,
        "target_accuracy": target_accuracy,
        "target_recall": target_recall,
        "target_reached": target_reached,
        "nested_pooled_accuracy": pooled_sel["accuracy"],
        "nested_correct_samples": pooled_sel["correct_samples"],
        "nested_pooled_recall": pooled_sel["recall"],
        "baseline_pooled_accuracy": pooled_base["accuracy"],
        "baseline_correct_samples": pooled_base["correct_samples"],
        "baseline_pooled_recall": pooled_base["recall"],
        "shrinkage_lda_accuracy": pooled_shrk["accuracy"],
        "shrinkage_lda_correct_samples": pooled_shrk["correct_samples"],
        "shrinkage_lda_recall": pooled_shrk["recall"],
        "shrinkage_lda_brier": pooled_shrk["brier_score"],
        "empirical_lda_accuracy": pooled_emp["accuracy"],
        "empirical_lda_correct_samples": pooled_emp["correct_samples"],
        "empirical_lda_recall": pooled_emp["recall"],
        "selected_candidates_distribution": results["nested_selection_procedure"]["selected_candidates_distribution"],
        "research_history_limitation": (
            "The choice to evaluate Shrinkage LDA was informed by previous model search findings demonstrating "
            "that linear decision boundaries dominate tree ensembles on this 242-patient dataset. Therefore, this "
            "evaluation evaluates the out-of-fold generalization of shrinkage LDA within this development partition, "
            "but does NOT constitute independent external validation on a separate clinical cohort."
        ),
        "evaluation_results": results
    }

    out_file = RESULTS_DIR / "nested_lda_evaluation.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("=" * 80)
    print("NESTED LDA EVALUATION SUMMARY & VERDICT")
    print("=" * 80)
    print(f"Target 90%+ Accuracy Reached:           {target_reached}")
    print(f"Nested Selection Procedure Accuracy:   {pooled_sel['accuracy']:.4f} ({pooled_sel['correct_samples']}/242) [Recall: {pooled_sel['recall']:.4f}]")
    print(f"Authoritative Baseline (LR) Accuracy:  {pooled_base['accuracy']:.4f} ({pooled_base['correct_samples']}/242) [Recall: {pooled_base['recall']:.4f}]")
    print(f"Shrinkage LDA (Fixed Arm) Accuracy:    {pooled_shrk['accuracy']:.4f} ({pooled_shrk['correct_samples']}/242) [Recall: {pooled_shrk['recall']:.4f}]")
    print(f"Empirical LDA (Fixed Arm) Accuracy:    {pooled_emp['accuracy']:.4f} ({pooled_emp['correct_samples']}/242) [Recall: {pooled_emp['recall']:.4f}]")
    print(f"Brier Scores: Shrk LDA={pooled_shrk['brier_score']:.4f} vs Baseline LR={pooled_base['brier_score']:.4f}")
    print(f"Selected Distribution across Outer Folds: {results['nested_selection_procedure']['selected_candidates_distribution']}")
    print(f"Results serialized to: {out_file}\n")


if __name__ == "__main__":
    main()
