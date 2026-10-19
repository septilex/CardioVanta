"""
CardioVanta — Advanced Research Phase: High-Accuracy Investigation
==================================================================
Research-only script investigating novel representations, nonlinear basis
expansions, clinical domain features, and regularized ensembles on the 242-patient
development set.

Strict Protocol:
- Uses ONLY the 242 development samples (dev_indices.json).
- Never loads, evaluates, or participates in the 61-sample locked test set.
- Enforces duplicate-aware StratifiedGroupKFold cross-validation (241 unique groups).
- All scaling, transformations, and calibrations are fitted strictly fold-locally.
- Never modifies production model artifacts. Output written to experiments/results/.
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
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import VotingClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder, SplineTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import BaseEstimator, TransformerMixin

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.advanced_model_search import load_dev_data

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Standard feature groupings
CONTINUOUS_COLS = ["age", "trestbps", "chol", "thalach", "oldpeak"]
BINARY_COLS = ["sex", "fbs", "exang"]
CATEGORICAL_COLS = ["cp", "restecg", "slope", "ca", "thal"]


class ClinicalDomainTransformer(BaseEstimator, TransformerMixin):
    """
    Cardiology Domain Feature Augmenter:
    - Rate Pressure Product (RPP = trestbps * thalach / 100): surrogate for myocardial oxygen consumption.
    - Heart Rate Reserve % (thalach / (220 - age)): marker for chronotropic incompetence.
    - ST-Angina Index (oldpeak * (1 + exang)): exercise ST depression compounded by exertional angina.
    - Multi-Vessel Disease Flag (ca > 0): fluoroscopy calcification in major coronary vessels.
    - Chol/Age Ratio: lipid risk normalized for chronological exposure.
    """
    def __init__(self, add_rpp=True, add_hr_reserve=True, add_st_angina=True, add_multi_vessel=True, add_chol_age=True):
        self.add_rpp = add_rpp
        self.add_hr_reserve = add_hr_reserve
        self.add_st_angina = add_st_angina
        self.add_multi_vessel = add_multi_vessel
        self.add_chol_age = add_chol_age

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        age = X["age"].values
        thalach = X["thalach"].values
        trestbps = X["trestbps"].values
        oldpeak = X["oldpeak"].values
        exang = X["exang"].values
        ca = X["ca"].values
        chol = X["chol"].values

        new_cols = {}
        if self.add_rpp:
            new_cols["rpp"] = (trestbps * thalach) / 100.0
        if self.add_hr_reserve:
            new_cols["hr_pct_pred"] = thalach / np.maximum(220.0 - age, 1.0)
        if self.add_st_angina:
            new_cols["st_angina_index"] = oldpeak * (1.0 + exang)
        if self.add_multi_vessel:
            new_cols["multi_vessel"] = (ca > 0).astype(float)
        if self.add_chol_age:
            new_cols["chol_age_ratio"] = chol / np.maximum(age, 1.0)

        return pd.concat([X, pd.DataFrame(new_cols, index=X.index)], axis=1)


class OldpeakQuadraticTransformer(BaseEstimator, TransformerMixin):
    """
    Fold-local quadratic expansion for oldpeak ST depression.
    Fitted strictly within the training partition.
    """
    def __init__(self):
        self.mean_ = None
        self.std_ = None

    def fit(self, X, y=None):
        X = np.asarray(X)
        u_sq = X[:, 4] ** 2  # Column 4 corresponds to oldpeak
        self.mean_ = float(np.mean(u_sq))
        std = float(np.std(u_sq))
        self.std_ = std if std > 1e-12 else 1.0
        return self

    def transform(self, X):
        X = np.asarray(X)
        u_sq_norm = (X[:, 4] ** 2 - self.mean_) / self.std_
        return np.hstack([X, u_sq_norm.reshape(-1, 1)])


def build_candidates():
    """
    Constructs the 6 research candidate architectures.
    """
    candidates = {}

    # Candidate 1: Production Frozen Baseline
    prep_base = ColumnTransformer([
        ("num", StandardScaler(), CONTINUOUS_COLS),
        ("bin", "passthrough", BINARY_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)
    ])
    clf_base = LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=42, max_iter=1000)
    candidates["Candidate 1: Frozen Baseline (StandardScaler + LR C=0.1 balanced)"] = {
        "pipeline": Pipeline([("prep", prep_base), ("clf", clf_base)]),
        "description": "Authoritative production baseline: standardized continuous, OHE categorical, balanced L2 Logistic Regression."
    }

    # Candidate 2: Clinical Domain Feature Engineering
    ext_continuous = CONTINUOUS_COLS + ["rpp", "hr_pct_pred", "st_angina_index", "chol_age_ratio"]
    ext_binary = BINARY_COLS + ["multi_vessel"]
    prep_clinical = ColumnTransformer([
        ("num", StandardScaler(), ext_continuous),
        ("bin", "passthrough", ext_binary),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)
    ])
    clf_clinical = LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=42, max_iter=1000)
    candidates["Candidate 2: Clinical Domain Features + Balanced LR"] = {
        "pipeline": Pipeline([
            ("feat", ClinicalDomainTransformer()),
            ("prep", prep_clinical),
            ("clf", clf_clinical)
        ]),
        "description": "Cardiology domain indicators (rate-pressure product, HR reserve, ST-angina interaction, multi-vessel indicator)."
    }

    # Candidate 3: Nonlinear Continuous B-Splines
    prep_splines = ColumnTransformer([
        ("spline", SplineTransformer(n_knots=4, degree=3, include_bias=False), CONTINUOUS_COLS),
        ("bin", "passthrough", BINARY_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)
    ])
    clf_splines = LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=42, max_iter=1000)
    candidates["Candidate 3: B-Splines (Nonlinear Basis) + LR C=0.1"] = {
        "pipeline": Pipeline([("prep", prep_splines), ("clf", clf_splines)]),
        "description": "Cubic B-splines over continuous physiological variables to capture smooth nonlinear thresholds."
    }

    # Candidate 4: Oldpeak Quadratic Representation with Optimized Convex Regularization
    prep_quad = ColumnTransformer([
        ("num", StandardScaler(), CONTINUOUS_COLS),
        ("bin", "passthrough", BINARY_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)
    ])
    clf_quad = LogisticRegression(C=0.2, class_weight=None, solver="lbfgs", random_state=42, max_iter=1000)
    candidates["Candidate 4: Oldpeak Quadratic + Tuned Regularization (C=0.2)"] = {
        "pipeline": Pipeline([
            ("prep", prep_quad),
            ("aug", OldpeakQuadraticTransformer()),
            ("clf", clf_quad)
        ]),
        "description": "Standardized (oldpeak)^2 quadratic term paired with unweighted C=0.2 L2 regularization."
    }

    # Candidate 5: ElasticNet (L1 + L2 Sparse Regularization)
    prep_enet = ColumnTransformer([
        ("num", StandardScaler(), CONTINUOUS_COLS),
        ("bin", "passthrough", BINARY_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)
    ])
    clf_enet = LogisticRegression(C=0.2, l1_ratio=0.5, penalty="elasticnet", solver="saga", random_state=42, max_iter=2500, class_weight="balanced")
    candidates["Candidate 5: ElasticNet (L1/L2 Sparsity, SAGA)"] = {
        "pipeline": Pipeline([("prep", prep_enet), ("clf", clf_enet)]),
        "description": "ElasticNet penalization encouraging feature sparsity to eliminate noisy sparse one-hot dummy columns."
    }

    # Candidate 6: Tri-Model Soft Voting Ensemble
    prep_ensemble = ColumnTransformer([
        ("num", StandardScaler(), CONTINUOUS_COLS),
        ("bin", "passthrough", BINARY_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)
    ])
    m_lr = LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=42, max_iter=1000)
    m_enet = LogisticRegression(C=0.2, l1_ratio=0.3, penalty="elasticnet", solver="saga", random_state=42, max_iter=2000, class_weight="balanced")
    m_svm = SVC(kernel="linear", C=0.05, class_weight="balanced", random_state=42, probability=True)
    vote = VotingClassifier(
        estimators=[("lr", m_lr), ("enet", m_enet), ("svm", m_svm)],
        voting="soft"
    )
    candidates["Candidate 6: Tri-Model Soft Voting Ensemble (LR + ElasticNet + Linear SVM)"] = {
        "pipeline": Pipeline([("prep", prep_ensemble), ("vote", vote)]),
        "description": "Variance-reduction ensemble averaging posterior probabilities from three complementary linear/convex classifiers."
    }

    return candidates


def evaluate_all(candidates, X_dev, y_dev, dev_groups, n_splits=5):
    """
    Executes identical 5-fold StratifiedGroupKFold cross-validation across all candidates (exploratory benchmark).
    """
    from sklearn.base import clone
    cv = StratifiedGroupKFold(n_splits=n_splits)
    evaluation_records = {}

    for cand_name, cand_info in candidates.items():
        t0 = time.time()
        pipeline = cand_info["pipeline"]
        description = cand_info["description"]

        oof_preds = np.zeros(len(y_dev), dtype=int)
        oof_probs = np.zeros(len(y_dev), dtype=float)
        fold_metrics = []

        for fold_i, (tr_idx, val_idx) in enumerate(cv.split(X_dev, y_dev, groups=dev_groups)):
            X_tr, y_tr, g_tr = X_dev.iloc[tr_idx].reset_index(drop=True), y_dev[tr_idx], dev_groups[tr_idx]
            X_val, y_val = X_dev.iloc[val_idx].reset_index(drop=True), y_dev[val_idx]

            cal_splits = list(StratifiedGroupKFold(n_splits=5).split(X_tr, y_tr, groups=g_tr))
            calibrator = CalibratedClassifierCV(estimator=clone(pipeline), method="sigmoid", cv=cal_splits)
            calibrator.fit(X_tr, y_tr)

            probs = calibrator.predict_proba(X_val)[:, 1]
            preds = (probs >= 0.5).astype(int)

            oof_probs[val_idx] = probs
            oof_preds[val_idx] = preds

            fold_acc = float(accuracy_score(y_val, preds))
            fold_rec = float(recall_score(y_val, preds, zero_division=0))
            fold_metrics.append({"fold": fold_i + 1, "accuracy": fold_acc, "recall": fold_rec})

        elapsed = time.time() - t0
        metrics = compute_metrics(y_dev, oof_preds, oof_probs)
        fold_accs = [f["accuracy"] for f in fold_metrics]

        record = {
            "name": cand_name,
            "description": description,
            "accuracy": metrics["accuracy"],
            "correct_samples": metrics["correct_samples"],
            "total_samples": metrics["total_samples"],
            "recall": metrics["recall"],
            "specificity": metrics["specificity"],
            "precision": metrics["precision"],
            "f1_score": metrics["f1_score"],
            "roc_auc": metrics["roc_auc"],
            "brier_score": metrics["brier_score"],
            "log_loss": metrics["log_loss"],
            "confusion_matrix": metrics["confusion_matrix"],
            "fold_accuracies": fold_accs,
            "fold_accuracy_std": float(np.std(fold_accs)),
            "elapsed_seconds": round(elapsed, 2)
        }
        evaluation_records[cand_name] = record

    return evaluation_records


SIMPLICITY_RANKS = {
    "Candidate 1: Frozen Baseline (StandardScaler + LR C=0.1 balanced)": 1,
    "Candidate 4: Oldpeak Quadratic + Tuned Regularization (C=0.2)": 2,
    "Candidate 2: Clinical Domain Features + Balanced LR": 3,
    "Candidate 3: B-Splines (Nonlinear Basis) + LR C=0.1": 4,
    "Candidate 5: ElasticNet (L1/L2 Sparsity, SAGA)": 5,
    "Candidate 6: Tri-Model Soft Voting Ensemble (LR + ElasticNet + Linear SVM)": 6,
}



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


def evaluate_nested_cv(candidates, X_dev, y_dev, dev_groups, n_outer_splits=5, n_inner_splits=5):
    """
    Executes true duplicate-aware 5x5 Nested Cross-Validation.
    
    Outer Loop (5 folds):
      - Evaluates the generalization performance of the entire model-selection procedure.
      - Never participates in model selection, feature preprocessing, or threshold/probability calibration.
      - Guarantees zero patient group overlap between outer train and outer validation partitions.
      
    Inner Loop (5 folds per outer fold):
      - Evaluates the 6 frozen candidates on the outer training partition.
      - All preprocessing, basis expansions, and sigmoid calibrations are fitted fold-locally.
      - Selects the winning candidate based on frozen criteria:
          1. Highest Inner OOF Accuracy
          2. Tie-breaker 1: Highest Inner OOF ROC-AUC
          3. Tie-breaker 2: Lowest Simplicity Rank (Frozen simplicity hierarchy)
          
    Baseline Comparison:
      - Evaluates the authoritative frozen production baseline on the EXACT same outer folds.
    """
    from sklearn.base import clone

    print("=" * 80)
    print("CARDIOVANTA NESTED CROSS-VALIDATION: 90%+ TARGET INVESTIGATION")
    print("=" * 80)
    print(f"Development Set Size: N={len(X_dev)} (Locked Test Set Strictly Excluded)")
    print(f"Unique Patient Groups: {len(np.unique(dev_groups))}")
    print(f"Outer Splits: {n_outer_splits} | Inner Splits: {n_inner_splits}")
    print("Selection Hierarchy: 1. Inner Accuracy -> 2. Inner ROC-AUC -> 3. Simplicity Rank\n")

    outer_cv = StratifiedGroupKFold(n_splits=n_outer_splits)

    nested_oof_preds = np.zeros(len(y_dev), dtype=int)
    nested_oof_probs = np.zeros(len(y_dev), dtype=float)

    baseline_name = "Candidate 1: Frozen Baseline (StandardScaler + LR C=0.1 balanced)"
    base_oof_preds = np.zeros(len(y_dev), dtype=int)
    base_oof_probs = np.zeros(len(y_dev), dtype=float)

    outer_fold_records = []
    base_fold_records = []

    t_start = time.time()

    for fold_i, (tr_idx, val_idx) in enumerate(outer_cv.split(X_dev, y_dev, groups=dev_groups)):
        t_fold = time.time()
        # Verify strict outer partition group isolation
        outer_overlap = set(dev_groups[tr_idx]).intersection(set(dev_groups[val_idx]))
        assert len(outer_overlap) == 0, f"Outer Fold {fold_i} group leakage detected: {outer_overlap}"

        X_tr = X_dev.iloc[tr_idx].reset_index(drop=True)
        y_tr = y_dev[tr_idx]
        g_tr = dev_groups[tr_idx]

        X_val = X_dev.iloc[val_idx].reset_index(drop=True)
        y_val = y_dev[val_idx]

        print(f"--- Outer Fold {fold_i + 1}/{n_outer_splits} (Train N={len(X_tr)}, Val N={len(X_val)}) ---")

        # Inner Loop: evaluate all 6 frozen candidates
        inner_cv = StratifiedGroupKFold(n_splits=n_inner_splits)
        inner_candidate_results = []

        for cand_name, cand_info in candidates.items():
            in_preds = np.zeros(len(y_tr), dtype=int)
            in_probs = np.zeros(len(y_tr), dtype=float)

            for in_tr_idx, in_val_idx in inner_cv.split(X_tr, y_tr, groups=g_tr):
                # Verify strict inner partition group isolation
                in_overlap = set(g_tr[in_tr_idx]).intersection(set(g_tr[in_val_idx]))
                assert len(in_overlap) == 0, f"Inner fold group leakage: {in_overlap}"

                X_in_tr = X_tr.iloc[in_tr_idx].reset_index(drop=True)
                y_in_tr = y_tr[in_tr_idx]
                g_in_tr = g_tr[in_tr_idx]

                X_in_val = X_tr.iloc[in_val_idx].reset_index(drop=True)

                # Calibrator fitted strictly on inner training split
                cal_splits = list(StratifiedGroupKFold(n_splits=n_inner_splits).split(X_in_tr, y_in_tr, groups=g_in_tr))
                calibrator = CalibratedClassifierCV(estimator=clone(cand_info["pipeline"]), method="sigmoid", cv=cal_splits)
                calibrator.fit(X_in_tr, y_in_tr)

                p = calibrator.predict_proba(X_in_val)[:, 1]
                in_probs[in_val_idx] = p
                in_preds[in_val_idx] = (p >= 0.5).astype(int)

            in_metrics = compute_metrics(y_tr, in_preds, in_probs)
            rank = SIMPLICITY_RANKS[cand_name]
            inner_candidate_results.append({
                "name": cand_name,
                "inner_accuracy": in_metrics["accuracy"],
                "inner_roc_auc": in_metrics["roc_auc"],
                "inner_recall": in_metrics["recall"],
                "inner_specificity": in_metrics["specificity"],
                "inner_brier": in_metrics["brier_score"],
                "simplicity_rank": rank
            })

        # Selection Rule: Primary: inner_accuracy DESC, Secondary: inner_roc_auc DESC, Tertiary: simplicity_rank ASC
        inner_candidate_results.sort(
            key=lambda x: (x["inner_accuracy"], x["inner_roc_auc"], -x["simplicity_rank"]),
            reverse=True
        )
        winner = inner_candidate_results[0]
        winner_name = winner["name"]
        print(f"  Selected Winner: {winner_name}")
        print(f"    Inner OOF Acc: {winner['inner_accuracy']:.4f} | Inner ROC-AUC: {winner['inner_roc_auc']:.4f} | Simplicity Rank: {winner['simplicity_rank']}")

        # Retrain winning candidate on entire outer training set with fold-local calibration
        cal_splits_outer = list(StratifiedGroupKFold(n_splits=n_outer_splits).split(X_tr, y_tr, groups=g_tr))
        outer_calibrator = CalibratedClassifierCV(
            estimator=clone(candidates[winner_name]["pipeline"]),
            method="sigmoid",
            cv=cal_splits_outer
        )
        outer_calibrator.fit(X_tr, y_tr)

        val_probs = outer_calibrator.predict_proba(X_val)[:, 1]
        val_preds = (val_probs >= 0.5).astype(int)

        nested_oof_probs[val_idx] = val_probs
        nested_oof_preds[val_idx] = val_preds

        fold_outer_metrics = compute_metrics(y_val, val_preds, val_probs)

        # Baseline evaluation on exact same outer fold
        base_calibrator = CalibratedClassifierCV(
            estimator=clone(candidates[baseline_name]["pipeline"]),
            method="sigmoid",
            cv=cal_splits_outer
        )
        base_calibrator.fit(X_tr, y_tr)

        val_base_probs = base_calibrator.predict_proba(X_val)[:, 1]
        val_base_preds = (val_base_probs >= 0.5).astype(int)

        base_oof_probs[val_idx] = val_base_probs
        base_oof_preds[val_idx] = val_base_preds

        fold_base_metrics = compute_metrics(y_val, val_base_preds, val_base_probs)

        elapsed_fold = time.time() - t_fold
        print(f"  Outer Test Acc:  {fold_outer_metrics['accuracy']:.4f} | Recall: {fold_outer_metrics['recall']:.4f} | ROC-AUC: {fold_outer_metrics['roc_auc']:.4f}")
        print(f"  Baseline Acc:    {fold_base_metrics['accuracy']:.4f} | Recall: {fold_base_metrics['recall']:.4f} | ROC-AUC: {fold_base_metrics['roc_auc']:.4f}")
        print(f"  Fold Time:       {elapsed_fold:.2f}s\n")

        outer_fold_records.append({
            "fold": fold_i + 1,
            "test_samples": len(y_val),
            "selected_candidate": winner_name,
            "inner_selection_metrics": winner,
            "all_inner_candidates": inner_candidate_results,
            "outer_metrics": fold_outer_metrics,
            "elapsed_seconds": round(elapsed_fold, 2)
        })
        base_fold_records.append({
            "fold": fold_i + 1,
            "outer_metrics": fold_base_metrics
        })

    total_elapsed = time.time() - t_start

    # Pooled outer out-of-fold metrics across entire 242-patient dev set
    pooled_nested = compute_metrics(y_dev, nested_oof_preds, nested_oof_probs)
    pooled_base = compute_metrics(y_dev, base_oof_preds, base_oof_probs)

    # Fold variability calculations
    def summarize_fold_variability(fold_records):
        metrics_keys = ["accuracy", "recall", "specificity", "precision", "f1_score", "roc_auc", "brier_score", "log_loss"]
        variability = {}
        for k in metrics_keys:
            vals = [f["outer_metrics"][k] for f in fold_records]
            variability[k] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "fold_values": [float(v) for v in vals]
            }
        return variability

    nested_variability = summarize_fold_variability(outer_fold_records)
    base_variability = summarize_fold_variability(base_fold_records)

    # Comparison metrics
    comparison = {
        "accuracy_diff": pooled_nested["accuracy"] - pooled_base["accuracy"],
        "correct_samples_diff": pooled_nested["correct_samples"] - pooled_base["correct_samples"],
        "recall_diff": pooled_nested["recall"] - pooled_base["recall"],
        "specificity_diff": pooled_nested["specificity"] - pooled_base["specificity"],
        "precision_diff": pooled_nested["precision"] - pooled_base["precision"],
        "f1_score_diff": pooled_nested["f1_score"] - pooled_base["f1_score"],
        "roc_auc_diff": pooled_nested["roc_auc"] - pooled_base["roc_auc"],
        "brier_score_diff": pooled_nested["brier_score"] - pooled_base["brier_score"],
        "log_loss_diff": pooled_nested["log_loss"] - pooled_base["log_loss"]
    }

    selected_distribution = {}
    for f in outer_fold_records:
        cand = f["selected_candidate"]
        selected_distribution[cand] = selected_distribution.get(cand, 0) + 1

    return {
        "nested_selection_procedure": {
            "pooled_outer_metrics": pooled_nested,
            "fold_variability": nested_variability,
            "selected_candidates_distribution": selected_distribution,
            "outer_folds": outer_fold_records
        },
        "authoritative_baseline": {
            "pooled_outer_metrics": pooled_base,
            "fold_variability": base_variability,
            "outer_folds": base_fold_records
        },
        "comparison_vs_baseline": comparison,
        "total_elapsed_seconds": round(total_elapsed, 2)
    }


def run_diagnostics(X_dev, y_dev):
    """
    Computes dataset-level Bayes error diagnostics and categorical ambiguity.
    """
    conflict_indices = []
    cat_cols = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]
    for i in range(len(X_dev)):
        match = (X_dev[cat_cols].values == X_dev[cat_cols].values[i]).all(axis=1)
        diff_label = (y_dev != y_dev[i]) & match
        if diff_label.any():
            conflict_indices.append(i)

    return {
        "total_samples": len(X_dev),
        "contradictory_categorical_samples": len(conflict_indices),
        "contradictory_percentage": round(len(conflict_indices) / len(X_dev) * 100, 2)
    }


def main():
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, file_hash = load_dev_data()

    candidates = build_candidates()
    nested_results = evaluate_nested_cv(candidates, X_dev, y_dev, dev_groups)
    diagnostics = run_diagnostics(X_dev, y_dev)

    pooled_nested = nested_results["nested_selection_procedure"]["pooled_outer_metrics"]
    pooled_base = nested_results["authoritative_baseline"]["pooled_outer_metrics"]
    comp = nested_results["comparison_vs_baseline"]

    target_accuracy = 0.90
    target_recall = 0.85
    target_reached = (pooled_nested["accuracy"] >= target_accuracy) and (pooled_nested["recall"] >= target_recall)

    summary_output = {
        "experiment_title": "CardioVanta 5x5 Nested Cross-Validation: High-Accuracy Investigation",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_hash": file_hash,
        "dev_samples": len(X_dev),
        "locked_test_samples_used": 0,
        "target_accuracy": target_accuracy,
        "target_recall": target_recall,
        "target_reached": target_reached,
        "nested_pooled_accuracy": pooled_nested["accuracy"],
        "nested_correct_samples": pooled_nested["correct_samples"],
        "nested_pooled_recall": pooled_nested["recall"],
        "baseline_pooled_accuracy": pooled_base["accuracy"],
        "baseline_correct_samples": pooled_base["correct_samples"],
        "baseline_pooled_recall": pooled_base["recall"],
        "accuracy_gain_over_baseline": comp["accuracy_diff"],
        "research_history_limitation": (
            "The candidate shortlist was informed by previous exploratory experiments on this 242-patient "
            "development partition. Therefore, this nested cross-validation evaluates the generalization of the "
            "selection procedure across outer cross-validation folds, but does NOT constitute fully independent "
            "external confirmation."
        ),
        "diagnostics": diagnostics,
        "nested_evaluation": nested_results
    }

    results_file = RESULTS_DIR / "nested_cv_90pct_results.json"
    with open(results_file, "w") as f:
        json.dump(summary_output, f, indent=2)

    print("=" * 80)
    print("NESTED EVALUATION SUMMARY & VERDICT")
    print("=" * 80)
    print(f"Target 90%+ Accuracy Reached: {target_reached}")
    print(f"Nested Selection Procedure Pooled Accuracy: {pooled_nested['accuracy']:.4f} ({pooled_nested['correct_samples']}/{pooled_nested['total_samples']})")
    print(f"Authoritative Baseline Pooled Accuracy:    {pooled_base['accuracy']:.4f} ({pooled_base['correct_samples']}/{pooled_base['total_samples']})")
    print(f"Accuracy Gain Over Baseline:                {comp['accuracy_diff']:+.4f} ({comp['correct_samples_diff']:+d} samples)")
    print(f"Nested Pooled Recall:                       {pooled_nested['recall']:.4f} (Base: {pooled_base['recall']:.4f})")
    print(f"Nested Pooled Specificity:                  {pooled_nested['specificity']:.4f} (Base: {pooled_base['specificity']:.4f})")
    print(f"Nested Pooled ROC-AUC:                      {pooled_nested['roc_auc']:.4f} (Base: {pooled_base['roc_auc']:.4f})")
    print(f"Selected Candidate Distribution across 5 Outer Folds: {nested_results['nested_selection_procedure']['selected_candidates_distribution']}")
    print(f"Results serialized to: {results_file}\n")


if __name__ == "__main__":
    main()

