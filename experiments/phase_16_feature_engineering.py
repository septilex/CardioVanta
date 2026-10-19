"""
CardioVanta Phase 16: Feature Engineering & Robust Representation Research
==========================================================================
Research-only script for Phase 16 OpenSpec change.
Evaluates 4 explicitly frozen feature representations under duplicate-aware
Global Nested Cross-Validation with fold-local sigmoid calibration.

NEVER modifies production model artifacts or configurations.
Results are saved to experiments/results/ and reports/.
"""

import sys
import os
import json
import time
import hashlib
import subprocess
from pathlib import Path
from copy import deepcopy

import numpy as np
import pandas as pd
import sklearn
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, brier_score_loss,
    log_loss, confusion_matrix
)

# Project root setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import RAW_DATA_PATH, SCHEMA_PATH, BASE_DIR, RANDOM_SEED
from src.preprocessing.preprocessor import PreprocessingFactory

# Constants and Configuration
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TIE_TOLERANCE = 0.0001
EVAL_THRESHOLD = 0.5
ADOPTION_ACC_GAIN = 0.015  # +1.5 percentage points absolute
ADOPTION_MIN_RECALL = 0.85

CANDIDATE_NAMES = [
    "Candidate A (Baseline)",
    "Candidate B (Age x Thalach)",
    "Candidate C (Oldpeak Squared)",
    "Candidate D (Combined)"
]

SIMPLICITY_HIERARCHY = {
    "Candidate A (Baseline)": 1,
    "Candidate B (Age x Thalach)": 2,
    "Candidate C (Oldpeak Squared)": 3,
    "Candidate D (Combined)": 4
}


class Phase16FeatureAugmenter(BaseEstimator, TransformerMixin):
    """
    Fold-local feature engineering transformer.
    Takes the 27-column output of PreprocessingFactory('linear') and conditionally
    computes:
    - Interaction term: z_age * z_thalach (Column 0 * Column 3), then standardized.
    - Quadratic term: (z_oldpeak)^2 (Column 4 ** 2), then standardized.

    All means and standard deviations are fitted strictly within the training fold.
    Zero information from validation or test folds can participate in fitting.
    """
    def __init__(self, add_interaction: bool = False, add_oldpeak_sq: bool = False):
        self.add_interaction = add_interaction
        self.add_oldpeak_sq = add_oldpeak_sq
        self.mean_inter_ = None
        self.scale_inter_ = None
        self.mean_sq_ = None
        self.scale_sq_ = None

    def fit(self, X, y=None):
        X = np.asarray(X)
        if X.ndim != 2 or X.shape[1] < 5:
            raise ValueError(f"Input must have at least 5 continuous columns. Found shape {X.shape}")

        if self.add_interaction:
            # Column 0: num__age, Column 3: num__thalach
            u_inter = X[:, 0] * X[:, 3]
            self.mean_inter_ = float(np.mean(u_inter))
            s_inter = float(np.std(u_inter))
            self.scale_inter_ = s_inter if s_inter > 1e-12 else 1.0

        if self.add_oldpeak_sq:
            # Column 4: num__oldpeak
            u_sq = X[:, 4] ** 2
            self.mean_sq_ = float(np.mean(u_sq))
            s_sq = float(np.std(u_sq))
            self.scale_sq_ = s_sq if s_sq > 1e-12 else 1.0

        return self

    def transform(self, X):
        X = np.asarray(X)
        cols = [X]

        if self.add_interaction:
            if self.mean_inter_ is None or self.scale_inter_ is None:
                raise RuntimeError("Phase16FeatureAugmenter has not been fitted.")
            u_inter = X[:, 0] * X[:, 3]
            z_inter = (u_inter - self.mean_inter_) / self.scale_inter_
            cols.append(z_inter.reshape(-1, 1))

        if self.add_oldpeak_sq:
            if self.mean_sq_ is None or self.scale_sq_ is None:
                raise RuntimeError("Phase16FeatureAugmenter has not been fitted.")
            u_sq = X[:, 4] ** 2
            z_sq = (u_sq - self.mean_sq_) / self.scale_sq_
            cols.append(z_sq.reshape(-1, 1))

        return np.hstack(cols)


def build_candidate_pipeline(candidate_name: str) -> Pipeline:
    """
    Constructs an sklearn Pipeline for one of the four frozen representations.
    """
    factory = PreprocessingFactory()
    base_preprocessor = factory.get_preprocessing_pipeline("linear")
    base_lr = LogisticRegression(
        C=0.1,
        class_weight="balanced",
        solver="lbfgs",
        random_state=RANDOM_SEED,
        max_iter=1000
    )

    if candidate_name == "Candidate A (Baseline)":
        augmenter = Phase16FeatureAugmenter(add_interaction=False, add_oldpeak_sq=False)
    elif candidate_name == "Candidate B (Age x Thalach)":
        augmenter = Phase16FeatureAugmenter(add_interaction=True, add_oldpeak_sq=False)
    elif candidate_name == "Candidate C (Oldpeak Squared)":
        augmenter = Phase16FeatureAugmenter(add_interaction=False, add_oldpeak_sq=True)
    elif candidate_name == "Candidate D (Combined)":
        augmenter = Phase16FeatureAugmenter(add_interaction=True, add_oldpeak_sq=True)
    else:
        raise ValueError(f"Unknown candidate representation: {candidate_name}")

    return Pipeline([
        ("preprocessor", base_preprocessor),
        ("augmenter", augmenter),
        ("model", base_lr)
    ])


def select_candidate_by_rule(cand_aucs: dict[str, float], tolerance: float = TIE_TOLERANCE) -> tuple[str, float, list[str]]:
    """
    Inner-CV candidate selection rule:
    1. Highest ROC-AUC.
    2. Any candidate with (best_auc - auc) <= tolerance is tied.
    3. Choose the tied candidate with the lowest simplicity rank (simplest).
    """
    best_auc = max(cand_aucs.values())
    tied_candidates = [
        cand for cand, auc in cand_aucs.items()
        if (best_auc - auc) <= tolerance + 1e-12
    ]
    selected_candidate = min(tied_candidates, key=lambda c: SIMPLICITY_HIERARCHY[c])
    return selected_candidate, best_auc, tied_candidates


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    """
    Computes comprehensive binary classification and probabilistic metrics.
    """
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "avg_precision": float(average_precision_score(y_true, y_prob)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": spec,
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob)),
        "confusion_matrix": {
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)
        }
    }


def load_development_data():
    """
    Loads development dataset strictly isolated from locked test data.
    """
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]

    with open(BASE_DIR / "data" / "processed" / "dev_indices.json") as f:
        dev_idx = json.load(f)

    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    target_col = schema["target_column"]
    X_full = df.drop(columns=[target_col])
    y_full = df[target_col].to_numpy()

    X_dev = X_full.loc[dev_idx].reset_index(drop=True)
    y_dev = y_full[dev_idx]
    dev_groups = X_dev.groupby(list(X_dev.columns)).ngroup().values

    with open(RAW_DATA_PATH, "rb") as f:
        raw_hash = hashlib.sha256(f.read()).hexdigest()

    return X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, raw_hash


def load_locked_test_data(df, X_full, y_full, dev_idx):
    """
    Loads the 61-sample locked test data strictly for retrospective assessment.
    """
    test_idx = [i for i in df.index if i not in dev_idx]
    X_test = X_full.loc[test_idx].reset_index(drop=True)
    y_test = y_full[test_idx]
    return X_test, y_test, test_idx


def run_global_nested_cv(X_dev, y_dev, dev_groups, n_splits=5):
    """
    Executes true 5x5 Global Nested Cross-Validation with duplicate-aware grouping
    and fold-local sigmoid probability calibration.
    """
    outer_cv = StratifiedGroupKFold(n_splits=n_splits)

    n_samples = len(y_dev)
    oof_sel_probs = np.full(n_samples, np.nan, dtype=float)
    oof_sel_preds = np.full(n_samples, -1, dtype=int)
    oof_base_probs = np.full(n_samples, np.nan, dtype=float)
    oof_base_preds = np.full(n_samples, -1, dtype=int)

    outer_fold_records = []

    print("\n" + "=" * 76)
    print("PHASE 16: RUNNING GLOBAL NESTED CROSS-VALIDATION (5x5)")
    print("=" * 76)

    for outer_i, (train_idx, val_idx) in enumerate(outer_cv.split(X_dev, y_dev, groups=dev_groups)):
        t0 = time.time()
        print(f"\n--- Outer Fold {outer_i + 1}/{n_splits} ---")

        # Partition outer fold
        X_tr, y_tr = X_dev.iloc[train_idx].reset_index(drop=True), y_dev[train_idx]
        g_tr = dev_groups[train_idx]
        X_val, y_val = X_dev.iloc[val_idx].reset_index(drop=True), y_dev[val_idx]
        g_val = dev_groups[val_idx]

        # Verify zero group leakage between outer train and outer val
        group_overlap = set(g_tr).intersection(set(g_val))
        if len(group_overlap) > 0:
            raise RuntimeError(f"Outer fold {outer_i + 1} has group leakage: {group_overlap}")

        # -------------------------------------------------------------
        # Stage A: Inner CV Candidate Ranking (Raw ROC-AUC)
        # -------------------------------------------------------------
        inner_cv = StratifiedGroupKFold(n_splits=n_splits)
        cand_inner_aucs = {}

        for cand_name in CANDIDATE_NAMES:
            inner_oof_probs = np.full(len(y_tr), np.nan, dtype=float)

            for i_tr_idx, i_val_idx in inner_cv.split(X_tr, y_tr, groups=g_tr):
                # Verify inner train vs val group isolation
                i_overlap = set(g_tr[i_tr_idx]).intersection(set(g_tr[i_val_idx]))
                if len(i_overlap) > 0:
                    raise RuntimeError("Inner fold group overlap detected!")

                # Fit uncalibrated candidate pipeline
                pipe = build_candidate_pipeline(cand_name)
                pipe.fit(X_tr.iloc[i_tr_idx], y_tr[i_tr_idx])
                inner_oof_probs[i_val_idx] = pipe.predict_proba(X_tr.iloc[i_val_idx])[:, 1]

            cand_auc = float(roc_auc_score(y_tr, inner_oof_probs))
            cand_inner_aucs[cand_name] = cand_auc
            print(f"  Inner AUC - {cand_name}: {cand_auc:.4f}")

        # Apply frozen selection rule
        selected_cand_name, best_inner_auc, tied_cands = select_candidate_by_rule(cand_inner_aucs)
        print(f"  -> Selected: '{selected_cand_name}' (Best AUC: {best_inner_auc:.4f}, Tied: {tied_cands})")

        # -------------------------------------------------------------
        # Stage B: Fold-Local Calibration Fitting on Outer-Training Only
        # -------------------------------------------------------------
        cal_splits = list(StratifiedGroupKFold(n_splits=n_splits).split(X_tr, y_tr, groups=g_tr))

        # 1. Selected Procedure: Fit calibrator on outer training
        selected_pipe = build_candidate_pipeline(selected_cand_name)
        cal_selected = CalibratedClassifierCV(estimator=selected_pipe, method="sigmoid", cv=cal_splits)
        cal_selected.fit(X_tr, y_tr)

        # 2. Baseline Procedure: Fit calibrator on identical outer training
        baseline_pipe = build_candidate_pipeline("Candidate A (Baseline)")
        cal_baseline = CalibratedClassifierCV(estimator=baseline_pipe, method="sigmoid", cv=cal_splits)
        cal_baseline.fit(X_tr, y_tr)

        # -------------------------------------------------------------
        # Stage C & D: Outer Validation Evaluation (Threshold 0.5)
        # -------------------------------------------------------------
        sel_val_prob = cal_selected.predict_proba(X_val)[:, 1]
        sel_val_pred = (sel_val_prob >= EVAL_THRESHOLD).astype(int)

        base_val_prob = cal_baseline.predict_proba(X_val)[:, 1]
        base_val_pred = (base_val_prob >= EVAL_THRESHOLD).astype(int)

        oof_sel_probs[val_idx] = sel_val_prob
        oof_sel_preds[val_idx] = sel_val_pred
        oof_base_probs[val_idx] = base_val_prob
        oof_base_preds[val_idx] = base_val_pred

        sel_fold_metrics = compute_metrics(y_val, sel_val_pred, sel_val_prob)
        base_fold_metrics = compute_metrics(y_val, base_val_pred, base_val_prob)

        elapsed = time.time() - t0
        print(f"  Fold {outer_i + 1} Outer Metrics:")
        print(f"    Baseline Acc: {base_fold_metrics['accuracy']:.4f}, Recall: {base_fold_metrics['recall']:.4f}, Brier: {base_fold_metrics['brier']:.4f}")
        print(f"    Selected Acc: {sel_fold_metrics['accuracy']:.4f}, Recall: {sel_fold_metrics['recall']:.4f}, Brier: {sel_fold_metrics['brier']:.4f}")

        outer_fold_records.append({
            "fold": outer_i + 1,
            "train_samples": int(len(train_idx)),
            "val_samples": int(len(val_idx)),
            "inner_aucs": cand_inner_aucs,
            "tied_candidates": tied_cands,
            "selected_candidate": selected_cand_name,
            "baseline_metrics": base_fold_metrics,
            "selected_metrics": sel_fold_metrics,
            "elapsed_seconds": float(elapsed)
        })

    # Aggregate Out-of-Fold Metrics across all 242 dev samples
    oof_selected_aggregate = compute_metrics(y_dev, oof_sel_preds, oof_sel_probs)
    oof_baseline_aggregate = compute_metrics(y_dev, oof_base_preds, oof_base_probs)

    # Fold-wise Means and Standard Deviations
    fold_sel_accs = [r["selected_metrics"]["accuracy"] for r in outer_fold_records]
    fold_base_accs = [r["baseline_metrics"]["accuracy"] for r in outer_fold_records]
    fold_sel_recalls = [r["selected_metrics"]["recall"] for r in outer_fold_records]
    fold_base_recalls = [r["baseline_metrics"]["recall"] for r in outer_fold_records]

    return {
        "outer_fold_records": outer_fold_records,
        "oof_selected_aggregate": oof_selected_aggregate,
        "oof_baseline_aggregate": oof_baseline_aggregate,
        "fold_summary": {
            "selected": {
                "acc_mean": float(np.mean(fold_sel_accs)),
                "acc_std": float(np.std(fold_sel_accs)),
                "recall_mean": float(np.mean(fold_sel_recalls)),
                "recall_std": float(np.std(fold_sel_recalls))
            },
            "baseline": {
                "acc_mean": float(np.mean(fold_base_accs)),
                "acc_std": float(np.std(fold_base_accs)),
                "recall_mean": float(np.mean(fold_base_recalls)),
                "recall_std": float(np.std(fold_base_recalls))
            }
        }
    }


def evaluate_adoption_gate(oof_selected: dict, oof_baseline: dict) -> dict:
    """
    Evaluates whether the selection procedure passes the predefined adoption gate:
    1. Absolute aggregate accuracy improvement >= 1.5 percentage points (+0.015).
    2. Aggregate recall > 0.85.
    """
    acc_diff = oof_selected["accuracy"] - oof_baseline["accuracy"]
    rec = oof_selected["recall"]

    gate_1_passed = bool(acc_diff >= ADOPTION_ACC_GAIN)
    gate_2_passed = bool(rec > ADOPTION_MIN_RECALL)
    adoption_passed = bool(gate_1_passed and gate_2_passed)

    return {
        "baseline_accuracy": oof_baseline["accuracy"],
        "selected_accuracy": oof_selected["accuracy"],
        "absolute_accuracy_diff": float(acc_diff),
        "required_accuracy_diff": ADOPTION_ACC_GAIN,
        "gate_1_accuracy_passed": gate_1_passed,
        "selected_recall": rec,
        "required_recall": ADOPTION_MIN_RECALL,
        "gate_2_recall_passed": gate_2_passed,
        "adoption_gate_passed": adoption_passed,
        "decision": "ACCEPT" if adoption_passed else "REJECT"
    }


def select_final_candidate_full_dev(X_dev, y_dev, dev_groups, n_splits=5):
    """
    Applies the inner-selection rule to the complete development set.
    """
    print("\n" + "=" * 76)
    print("FINAL CANDIDATE SELECTION ON FULL DEVELOPMENT SET (N=242)")
    print("=" * 76)

    cv = StratifiedGroupKFold(n_splits=n_splits)
    cand_aucs = {}

    for cand_name in CANDIDATE_NAMES:
        oof_probs = np.full(len(y_dev), np.nan, dtype=float)
        for tr_idx, val_idx in cv.split(X_dev, y_dev, groups=dev_groups):
            pipe = build_candidate_pipeline(cand_name)
            pipe.fit(X_dev.iloc[tr_idx], y_dev[tr_idx])
            oof_probs[val_idx] = pipe.predict_proba(X_dev.iloc[val_idx])[:, 1]

        auc = float(roc_auc_score(y_dev, oof_probs))
        cand_aucs[cand_name] = auc
        print(f"  Full Dev Inner AUC - {cand_name}: {auc:.4f}")

    selected_cand_name, best_auc, tied_cands = select_candidate_by_rule(cand_aucs)
    print(f"\nFinal Selected Candidate: '{selected_cand_name}' (AUC: {best_auc:.4f}, Tied: {tied_cands})")

    return selected_cand_name, cand_aucs, tied_cands


def run_retrospective_locked_test(selected_cand_name, X_dev, y_dev, dev_groups, X_test, y_test):
    """
    Performs exactly ONE retrospective evaluation on the 61-sample locked test set.
    Fits and calibrates both the selected final pipeline and the baseline pipeline
    on the full development set using StratifiedGroupKFold(5) calibration splits.
    """
    print("\n" + "=" * 76)
    print("RETROSPECTIVE LOCKED-TEST EVALUATION (N=61)")
    print("=" * 76)

    cal_splits = list(StratifiedGroupKFold(n_splits=5).split(X_dev, y_dev, groups=dev_groups))

    # 1. Final Selected Candidate
    final_pipe = build_candidate_pipeline(selected_cand_name)
    cal_final = CalibratedClassifierCV(estimator=final_pipe, method="sigmoid", cv=cal_splits)
    cal_final.fit(X_dev, y_dev)

    test_prob_sel = cal_final.predict_proba(X_test)[:, 1]
    test_pred_sel = (test_prob_sel >= EVAL_THRESHOLD).astype(int)
    test_metrics_sel = compute_metrics(y_test, test_pred_sel, test_prob_sel)

    # 2. Frozen Baseline for Exact Comparison
    base_pipe = build_candidate_pipeline("Candidate A (Baseline)")
    cal_base = CalibratedClassifierCV(estimator=base_pipe, method="sigmoid", cv=cal_splits)
    cal_base.fit(X_dev, y_dev)

    test_prob_base = cal_base.predict_proba(X_test)[:, 1]
    test_pred_base = (test_prob_base >= EVAL_THRESHOLD).astype(int)
    test_metrics_base = compute_metrics(y_test, test_pred_base, test_prob_base)

    print("Locked Test Baseline Metrics:")
    print(f"  Accuracy: {test_metrics_base['accuracy']:.4f}, Recall: {test_metrics_base['recall']:.4f}, ROC-AUC: {test_metrics_base['roc_auc']:.4f}")
    print(f"  Confusion: {test_metrics_base['confusion_matrix']}")

    print(f"\nLocked Test Selected Candidate ({selected_cand_name}) Metrics:")
    print(f"  Accuracy: {test_metrics_sel['accuracy']:.4f}, Recall: {test_metrics_sel['recall']:.4f}, ROC-AUC: {test_metrics_sel['roc_auc']:.4f}")
    print(f"  Confusion: {test_metrics_sel['confusion_matrix']}")

    return test_metrics_sel, test_metrics_base


def main():
    t_start = time.time()

    # Provenance tracking
    try:
        git_head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        git_head = "unknown"

    # 1. Load Development Data (Locked test protected)
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, raw_hash = load_development_data()
    print(f"Loaded Development Set: N={len(X_dev)} samples, {len(np.unique(dev_groups))} unique duplicate groups.")

    # 2. Run Global Nested CV
    nested_cv_results = run_global_nested_cv(X_dev, y_dev, dev_groups, n_splits=5)

    # 3. Evaluate Adoption Gate
    adoption_eval = evaluate_adoption_gate(
        nested_cv_results["oof_selected_aggregate"],
        nested_cv_results["oof_baseline_aggregate"]
    )
    print("\n" + "=" * 76)
    print("PREDEFINED ADOPTION GATE EVALUATION")
    print("=" * 76)
    print(f"  Baseline OOF Accuracy: {adoption_eval['baseline_accuracy']:.4f}")
    print(f"  Selected OOF Accuracy: {adoption_eval['selected_accuracy']:.4f}")
    print(f"  Absolute Difference:   {adoption_eval['absolute_accuracy_diff']:+.4f} (Required: >={ADOPTION_ACC_GAIN}) -> Passed: {adoption_eval['gate_1_accuracy_passed']}")
    print(f"  Selected OOF Recall:   {adoption_eval['selected_recall']:.4f} (Required: >{ADOPTION_MIN_RECALL}) -> Passed: {adoption_eval['gate_2_recall_passed']}")
    print(f"  Overall Gate Decision: {adoption_eval['decision']}")

    # 4. Final Candidate Selection on Full Development Set
    final_cand_name, full_dev_aucs, tied_cands = select_final_candidate_full_dev(X_dev, y_dev, dev_groups, n_splits=5)

    # 5. Retrospective Locked Test Evaluation
    X_test, y_test, test_idx = load_locked_test_data(df, X_full, y_full, dev_idx)
    test_metrics_sel, test_metrics_base = run_retrospective_locked_test(
        final_cand_name, X_dev, y_dev, dev_groups, X_test, y_test
    )

    # Compile Complete Provenance Record
    results_payload = {
        "provenance": {
            "git_head": git_head,
            "python_version": sys.version.split(" ")[0],
            "sklearn_version": sklearn.__version__,
            "numpy_version": np.__version__,
            "pandas_version": pd.__version__,
            "raw_dataset_sha256": raw_hash,
            "random_seed": RANDOM_SEED,
            "n_dev_samples": len(X_dev),
            "n_locked_test_samples": len(X_test),
            "feature_order": schema["feature_order"],
            "candidates": CANDIDATE_NAMES,
            "simplicity_hierarchy": SIMPLICITY_HIERARCHY,
            "tie_tolerance": TIE_TOLERANCE,
            "evaluation_threshold": EVAL_THRESHOLD,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        },
        "nested_cv": nested_cv_results,
        "adoption_gate": adoption_eval,
        "final_selection": {
            "selected_candidate": final_cand_name,
            "full_dev_aucs": full_dev_aucs,
            "tied_candidates": tied_cands
        },
        "retrospective_locked_test": {
            "disclosure": "Retrospective assessment on previously inspected 61-sample locked test; exploratory, not independent confirmation.",
            "baseline_metrics": test_metrics_base,
            "selected_candidate_metrics": test_metrics_sel
        },
        "execution_time_seconds": float(time.time() - t_start)
    }

    # Save to both JSON destinations
    out_path_1 = RESULTS_DIR / "phase_16_results.json"
    out_path_2 = RESULTS_DIR / "phase16_feature_engineering.json"

    with open(out_path_1, "w") as f:
        json.dump(results_payload, f, indent=2)
    with open(out_path_2, "w") as f:
        json.dump(results_payload, f, indent=2)

    print(f"\nSaved structured experimental results to:\n  - {out_path_1}\n  - {out_path_2}")

    return results_payload


if __name__ == "__main__":
    main()
