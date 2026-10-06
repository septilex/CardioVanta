"""
CardioVanta Advanced ML Performance Investigation
==================================================
Research-only script. NEVER modifies production artifacts.
All output goes to experiments/results/.
"""

import json
import time
import warnings
import sys
import os
from pathlib import Path
import hashlib

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy import stats

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, PolynomialFeatures
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, brier_score_loss,
    log_loss, confusion_matrix
)
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
import xgboost
from xgboost import XGBClassifier
import lightgbm
from lightgbm import LGBMClassifier
import catboost
from catboost import CatBoostClassifier

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import RAW_DATA_PATH, RANDOM_SEED, BASE_DIR
from src.preprocessing.preprocessor import PreprocessingFactory

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def specificity_score(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    return tn / (tn + fp) if (tn + fp) > 0 else 0.0


def full_metrics(y_true, y_pred, y_prob):
    return {
        "accuracy":  float(accuracy_score(y_true, y_pred)),
        "roc_auc":   float(roc_auc_score(y_true, y_prob)),
        "avg_prec":  float(average_precision_score(y_true, y_prob)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(specificity_score(y_true, y_pred)),
        "f1":        float(f1_score(y_true, y_pred, zero_division=0)),
        "brier":     float(brier_score_loss(y_true, y_prob)),
        "log_loss":  float(log_loss(y_true, y_prob)),
    }


def global_nested_cv_evaluate(all_candidates_dict, X, y, groups, n_splits=5):
    """
    Run TRUE Global Nested CV over the entire candidate space.
    Outer loop evaluates generalization of the selection process.
    Inner loop selects best configuration out of ALL candidates.
    """
    outer_cv = StratifiedGroupKFold(n_splits=n_splits)
    oof_preds = np.full(len(y), -1, dtype=int)
    oof_probs = np.full(len(y), np.nan, dtype=float)
    
    selected_configs = []
    outer_fold_results = []
    
    for fold_i, (train_idx, val_idx) in enumerate(outer_cv.split(X, y, groups=groups)):
        t_fold = time.time()
        print(f"Outer Fold {fold_i + 1}/{n_splits} started...")
        X_tr, y_tr = X.iloc[train_idx], y[train_idx]
        g_tr = groups[train_idx]
        X_val, y_val = X.iloc[val_idx], y[val_idx]
        
        inner_cv = StratifiedGroupKFold(n_splits=n_splits)
        
        # We will collect inner OOF ROC-AUC and Accuracy for tie-breaking
        best_cand_name = None
        best_cand_pipe = None
        best_inner_auc = -1.0
        best_inner_acc = -1.0
        
        for cand_name, pipe in all_candidates_dict.items():
            inner_oof_probs = np.full(len(y_tr), np.nan, dtype=float)
            inner_oof_preds = np.full(len(y_tr), -1, dtype=int)
            
            for i_tr_idx, i_val_idx in inner_cv.split(X_tr, y_tr, groups=g_tr):
                pipe.fit(X_tr.iloc[i_tr_idx], y_tr[i_tr_idx])
                inner_oof_probs[i_val_idx] = pipe.predict_proba(X_tr.iloc[i_val_idx])[:, 1]
                inner_oof_preds[i_val_idx] = pipe.predict(X_tr.iloc[i_val_idx])
                
            inner_auc = roc_auc_score(y_tr, inner_oof_probs)
            inner_acc = accuracy_score(y_tr, inner_oof_preds)
            
            # Selection Rule: ROC-AUC primary, Accuracy secondary tie-breaker
            if inner_auc > best_inner_auc or (inner_auc == best_inner_auc and inner_acc > best_inner_acc):
                best_inner_auc = inner_auc
                best_inner_acc = inner_acc
                best_cand_name = cand_name
                best_cand_pipe = pipe
                
        print(f"  Selected config: {best_cand_name} (Inner AUC: {best_inner_auc:.4f})")
        selected_configs.append(best_cand_name)
        
        # Train selected configuration on full outer train set
        best_cand_pipe.fit(X_tr, y_tr)
        preds = best_cand_pipe.predict(X_val)
        probs = best_cand_pipe.predict_proba(X_val)[:, 1]
        
        oof_preds[val_idx] = preds
        oof_probs[val_idx] = probs
        
        fold_metrics = full_metrics(y_val, preds, probs)
        outer_fold_results.append({
            "fold": fold_i + 1,
            "selected_candidate": best_cand_name,
            "inner_auc": float(best_inner_auc),
            "outer_metrics": fold_metrics,
            "elapsed_s": time.time() - t_fold
        })
        
    oof_aggregate = full_metrics(y, oof_preds, oof_probs)
    return {
        "oof": oof_aggregate,
        "selected_configs_per_fold": selected_configs,
        "outer_fold_results": outer_fold_results
    }


def load_dev_data():
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    with open(BASE_DIR / "data" / "processed" / "dev_indices.json") as f:
        dev_idx = json.load(f)
    schema = json.load(open(BASE_DIR / "configs" / "feature_schema.json"))
    X_full = df.drop(columns=[schema["target_column"]])
    y_full = df[schema["target_column"]].to_numpy()
    X_dev = X_full.loc[dev_idx].reset_index(drop=True)
    y_dev = y_full[dev_idx]
    dev_groups = X_dev.groupby(list(X_dev.columns)).ngroup().values
    
    # Calculate SHA256 of raw dataset file bytes
    with open(RAW_DATA_PATH, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    return X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, file_hash


def load_locked_test(df, X_full, y_full, dev_idx):
    all_idx = set(range(len(df)))
    test_idx = sorted(all_idx - set(dev_idx))
    X_test = X_full.loc[test_idx].reset_index(drop=True)
    y_test = y_full[test_idx]
    return X_test, y_test


def get_all_candidates(factory):
    cands = {}
    
    # 1. Current Production Baseline
    cands["LR_production (C=0.1, balanced)"] = Pipeline([
        ("preprocessor", factory.get_preprocessing_pipeline("linear")),
        ("model", LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=RANDOM_SEED, max_iter=1000))
    ])
    
    # 2. Logistic Regression
    for C in [0.01, 0.05, 0.5, 1.0, 5.0, 10.0]:
        for cw in [None, "balanced"]:
            cands[f"LR (C={C}, cw={cw})"] = Pipeline([
                ("preprocessor", factory.get_preprocessing_pipeline("linear")),
                ("model", LogisticRegression(C=C, class_weight=cw, solver="lbfgs", random_state=RANDOM_SEED, max_iter=1000))
            ])
            
    # 3. SVM
    for C in [0.1, 1.0, 10.0]:
        for kernel in ["rbf", "linear"]:
            cands[f"SVM (C={C}, {kernel})"] = Pipeline([
                ("preprocessor", factory.get_preprocessing_pipeline("svm")),
                ("model", SVC(C=C, kernel=kernel, probability=True, gamma="scale", random_state=RANDOM_SEED, class_weight="balanced"))
            ])
            
    # 4. Random Forest
    for n_est in [200, 500]:
        for depth in [None, 5, 8]:
            for min_leaf in [1, 2]:
                cands[f"RF (n={n_est}, d={depth}, ml={min_leaf})"] = Pipeline([
                    ("preprocessor", factory.get_preprocessing_pipeline("tree")),
                    ("model", RandomForestClassifier(n_estimators=n_est, max_depth=depth, min_samples_leaf=min_leaf, max_features="sqrt", random_state=RANDOM_SEED, class_weight="balanced", n_jobs=-1))
                ])
                
    # 5. Gradient Boosting
    for n_est in [100, 200, 300]:
        for depth in [2, 3, 4]:
            for lr in [0.05, 0.1]:
                cands[f"GBM (n={n_est}, d={depth}, lr={lr})"] = Pipeline([
                    ("preprocessor", factory.get_preprocessing_pipeline("tree")),
                    ("model", GradientBoostingClassifier(n_estimators=n_est, max_depth=depth, learning_rate=lr, subsample=0.8, random_state=RANDOM_SEED))
                ])
                
    # 6. XGBoost
    for n_est in [100, 200, 400]:
        for depth in [2, 3, 4]:
            for lr in [0.05, 0.1]:
                cands[f"XGB (n={n_est}, d={depth}, lr={lr})"] = Pipeline([
                    ("preprocessor", factory.get_preprocessing_pipeline("tree")),
                    ("model", XGBClassifier(n_estimators=n_est, max_depth=depth, learning_rate=lr, subsample=0.8, colsample_bytree=0.8, random_state=RANDOM_SEED, eval_metric="logloss", verbosity=0))
                ])
                
    # 7. LightGBM
    for n_est in [100, 200, 400]:
        for n_leaves in [15, 31, 63]:
            for lr in [0.05, 0.1]:
                cands[f"LGBM (n={n_est}, lv={n_leaves}, lr={lr})"] = Pipeline([
                    ("preprocessor", factory.get_preprocessing_pipeline("tree")),
                    ("model", LGBMClassifier(n_estimators=n_est, num_leaves=n_leaves, learning_rate=lr, subsample=0.8, colsample_bytree=0.8, random_state=RANDOM_SEED, verbose=-1, is_unbalance=True))
                ])
                
    # 8. CatBoost
    for n_est in [200, 400]:
        for depth in [3, 4, 6]:
            for lr in [0.05, 0.1]:
                cands[f"CatBoost (n={n_est}, d={depth}, lr={lr})"] = Pipeline([
                    ("preprocessor", factory.get_preprocessing_pipeline("tree")),
                    ("model", CatBoostClassifier(iterations=n_est, depth=depth, learning_rate=lr, random_seed=RANDOM_SEED, verbose=0, auto_class_weights="Balanced"))
                ])
                
    return cands


def main():
    print("=" * 72)
    print("CARDIOVANTA — ADVANCED ML PERFORMANCE INVESTIGATION")
    print("=" * 72)
    
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, df_hash = load_dev_data()
    print(f"Development set: {len(X_dev)} samples")
    print(f"Raw dataset file SHA256: {df_hash}")
    
    factory = PreprocessingFactory()
    all_cands = get_all_candidates(factory)
    
    print(f"\nTotal candidate configurations: {len(all_cands)}")
    print("Stacking and Voting ensembles have been excluded to prevent duplicate-row leakage.")
    
    t0 = time.time()
    
    print("\nStarting Global Nested CV Evaluation...")
    global_result = global_nested_cv_evaluate(all_cands, X_dev, y_dev, dev_groups)
    
    print(f"\nGlobal Nested CV completed in {time.time() - t0:.1f}s")
    
    print("\n" + "=" * 72)
    print("GLOBAL NESTED CV RESULTS (OOF ESTIMATE OF SELECTION PROCESS)")
    print("=" * 72)
    print(f"  OOF Accuracy:  {global_result['oof']['accuracy']:.4f}")
    print(f"  OOF ROC-AUC:   {global_result['oof']['roc_auc']:.4f}")
    print(f"  OOF Avg Prec:  {global_result['oof']['avg_prec']:.4f}")
    print(f"  OOF F1:        {global_result['oof']['f1']:.4f}")
    
    for outer in global_result["outer_fold_results"]:
        print(f"  Outer Fold {outer['fold']} -> Selected: {outer['selected_candidate']}")
        
    print("\n" + "=" * 72)
    print("FINAL GLOBAL CANDIDATE SELECTION (ON FULL DEV SET)")
    print("=" * 72)
    
    # We run the selection rule across all dev data to get the final single candidate to deploy/test
    best_inner_auc = -1.0
    best_inner_acc = -1.0
    best_cand_pipe = None
    best_cand_name = None
    
    print("Running final cross-validation over full dev set to select final candidate...")
    for cand_name, pipe in all_cands.items():
        inner_oof_probs = np.full(len(y_dev), np.nan, dtype=float)
        inner_oof_preds = np.full(len(y_dev), -1, dtype=int)
        inner_cv = StratifiedGroupKFold(n_splits=5)
        for i_tr_idx, i_val_idx in inner_cv.split(X_dev, y_dev, groups=dev_groups):
            pipe.fit(X_dev.iloc[i_tr_idx], y_dev[i_tr_idx])
            inner_oof_probs[i_val_idx] = pipe.predict_proba(X_dev.iloc[i_val_idx])[:, 1]
            inner_oof_preds[i_val_idx] = pipe.predict(X_dev.iloc[i_val_idx])
            
        auc = roc_auc_score(y_dev, inner_oof_probs)
        acc = accuracy_score(y_dev, inner_oof_preds)
        
        if auc > best_inner_auc or (auc == best_inner_auc and acc > best_inner_acc):
            best_inner_auc = auc
            best_inner_acc = acc
            best_cand_pipe = pipe
            best_cand_name = cand_name
            
    print(f"Final selected candidate: {best_cand_name}")
    
    print("\n" + "=" * 72)
    print("PHASE 9 — LOCKED TEST EVALUATION")
    print("=" * 72)
    
    X_test, y_test = load_locked_test(df, X_full, y_full, dev_idx)
    
    # Evaluate Baseline
    baseline_pipe = all_cands["LR_production (C=0.1, balanced)"]
    cal_splits = list(StratifiedGroupKFold(n_splits=5).split(X_dev, y_dev, groups=dev_groups))
    cal_baseline = CalibratedClassifierCV(estimator=baseline_pipe, method="sigmoid", cv=cal_splits)
    cal_baseline.fit(X_dev, y_dev)
    bl_metrics = full_metrics(y_test, cal_baseline.predict(X_test), cal_baseline.predict_proba(X_test)[:, 1])
    
    print("\nCURRENT PRODUCTION MODEL (Calibrated LR):")
    for k, v in bl_metrics.items():
        print(f"  {k:15s}: {v:.4f}")
        
    # Evaluate Best Final Candidate
    cal_best = CalibratedClassifierCV(estimator=best_cand_pipe, method="sigmoid", cv=cal_splits)
    cal_best.fit(X_dev, y_dev)
    cand_metrics = full_metrics(y_test, cal_best.predict(X_test), cal_best.predict_proba(X_test)[:, 1])
    
    print(f"\nBEST CANDIDATE ({best_cand_name}):")
    for k, v in cand_metrics.items():
        print(f"  {k:15s}: {v:.4f}")
        
    # Decision
    best_dev_acc = global_result["oof"]["accuracy"]
    best_test_acc = cand_metrics["accuracy"]
    
    if best_dev_acc >= 0.95 and best_test_acc >= 0.95:
        decision = "A"
        decision_text = "95% achieved with valid methodology"
    elif best_dev_acc > bl_metrics["accuracy"] or best_test_acc > bl_metrics["accuracy"]:
        if best_dev_acc >= 0.95:
            decision = "B"
            decision_text = "Improvement achieved, but 95% not reached"
        else:
            decision = "B"
            decision_text = "Improvement achieved, but 95% not reached"
    else:
        decision = "C"
        decision_text = "Logistic Regression remains best"
        
    print(f"\nDecision: {decision}")
    print(f"Rationale: {decision_text}")
    print(f"  Dev OOF accuracy (best): {best_dev_acc:.4f}")
    print(f"  Test accuracy (baseline): {bl_metrics['accuracy']:.4f}")
    print(f"  Test accuracy (best):     {best_test_acc:.4f}")
    
    dependencies = {
        "python": sys.version.split(" ")[0],
        "scikit-learn": sklearn.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
        "xgboost": xgboost.__version__,
        "lightgbm": lightgbm.__version__,
        "catboost": catboost.__version__
    }
    
    with open(RESULTS_DIR / "candidate_comparison.json", "w") as f:
        json.dump({
            "experiment": "Advanced ML Performance Investigation (Global Nested CV Corrected)",
            "random_seed": RANDOM_SEED,
            "dev_samples": len(X_dev),
            "test_samples": len(y_test),
            "total_candidates": len(all_cands),
            "baseline_label": "LR_production",
            "best_candidate_selected": best_cand_name,
            "baseline_test_metrics": bl_metrics,
            "best_test_metrics": cand_metrics,
            "decision": decision,
            "decision_text": decision_text,
            "dependencies": dependencies,
            "dataset_sha256": df_hash,
            "global_nested_cv_results": global_result
        }, f, indent=2, default=str)
        
    print(f"\nResults saved to {RESULTS_DIR / 'candidate_comparison.json'}")
    
if __name__ == "__main__":
    main()
