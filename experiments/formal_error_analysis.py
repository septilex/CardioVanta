"""
CardioVanta Formal Error Analysis
=================================
Diagnostic script to understand errors made by the frozen baseline model.
Does not modify any production artifacts or tune any parameters.
"""

import json
import time
import warnings
import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import RANDOM_SEED, BASE_DIR
from src.preprocessing.preprocessor import PreprocessingFactory
from experiments.advanced_model_search import load_dev_data, load_locked_test

warnings.filterwarnings("ignore")

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def analyze_errors(X, y, preds, probs, name="dev_oof"):
    df_eval = X.copy()
    df_eval["y_true"] = y
    df_eval["y_pred"] = preds
    df_eval["prob"] = probs
    
    # Classify errors
    df_eval["error_type"] = "Unknown"
    df_eval.loc[(df_eval["y_true"] == 1) & (df_eval["y_pred"] == 1), "error_type"] = "TP"
    df_eval.loc[(df_eval["y_true"] == 0) & (df_eval["y_pred"] == 0), "error_type"] = "TN"
    df_eval.loc[(df_eval["y_true"] == 0) & (df_eval["y_pred"] == 1), "error_type"] = "FP"
    df_eval.loc[(df_eval["y_true"] == 1) & (df_eval["y_pred"] == 0), "error_type"] = "FN"
    
    counts = df_eval["error_type"].value_counts().to_dict()
    
    # Borderline cases
    df_eval["dist_to_0.5"] = np.abs(df_eval["prob"] - 0.5)
    borderline = df_eval.sort_values("dist_to_0.5").head(10)
    
    # High confidence errors
    errors = df_eval[df_eval["error_type"].isin(["FP", "FN"])]
    if len(errors) > 0:
        errors["confidence"] = np.where(errors["error_type"] == "FP", errors["prob"], 1 - errors["prob"])
        high_conf_errors = errors.sort_values("confidence", ascending=False).head(5)
    else:
        high_conf_errors = pd.DataFrame()
        
    # Low confidence correct
    correct = df_eval[df_eval["error_type"].isin(["TP", "TN"])]
    if len(correct) > 0:
        correct["confidence"] = np.where(correct["error_type"] == "TP", correct["prob"], 1 - correct["prob"])
        low_conf_correct = correct.sort_values("confidence", ascending=True).head(5)
    else:
        low_conf_correct = pd.DataFrame()
        
    return df_eval, counts, borderline, high_conf_errors, low_conf_correct

def extract_feature_stats(df_eval):
    numeric_cols = ["age", "trestbps", "chol", "thalach", "oldpeak"]
    cat_cols = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]
    
    stats = {}
    for col in numeric_cols:
        if col in df_eval.columns:
            stats[col] = df_eval.groupby("error_type")[col].median().to_dict()
    for col in cat_cols:
        if col in df_eval.columns:
            # Get the mode for categorical
            stats[col] = df_eval.groupby("error_type")[col].apply(lambda x: x.mode()[0] if not x.empty else None).to_dict()
            
    return stats

def main():
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, df_hash = load_dev_data()
    X_test, y_test = load_locked_test(df, X_full, y_full, dev_idx)
    
    factory = PreprocessingFactory()
    
    baseline_pipe = Pipeline([
        ("preprocessor", factory.get_preprocessing_pipeline("linear")),
        ("model", LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=RANDOM_SEED, max_iter=1000))
    ])
    
    cal_splits = list(StratifiedGroupKFold(n_splits=5).split(X_dev, y_dev, groups=dev_groups))
    cal_baseline = CalibratedClassifierCV(estimator=baseline_pipe, method="sigmoid", cv=cal_splits)
    
    # Dev OOF predictions (from calibration cross-validation)
    # The CalibratedClassifierCV fits on the cv folds, but doesn't easily return OOF preds for the whole set directly in a single array.
    # Actually, we can just do OOF manually to inspect the errors.
    
    oof_preds = np.zeros(len(y_dev), dtype=int)
    oof_probs = np.zeros(len(y_dev), dtype=float)
    
    for tr_idx, val_idx in cal_splits:
        X_tr, y_tr = X_dev.iloc[tr_idx], y_dev[tr_idx]
        X_val, y_val = X_dev.iloc[val_idx], y_dev[val_idx]
        
        # Fit baseline to calibrate
        baseline_pipe.fit(X_tr, y_tr)
        
        # Fit sigmoid on val set? CalibratedClassifierCV with cv=cal_splits will train (K-1) and calibrate on 1, then ensemble.
        # But for simple OOF diagnostic, we just use the raw LR probabilities to understand the model's feature space
        # since selection used raw probabilities!
        probs = baseline_pipe.predict_proba(X_val)[:, 1]
        preds = baseline_pipe.predict(X_val)
        
        oof_probs[val_idx] = probs
        oof_preds[val_idx] = preds
        
    df_dev, counts_dev, border_dev, hc_err_dev, lc_corr_dev = analyze_errors(X_dev, y_dev, oof_preds, oof_probs, "dev_oof")
    dev_f_stats = extract_feature_stats(df_dev)
    
    # Now Locked test Post-Hoc Analysis
    # We train the final Calibrated model on full dev
    cal_baseline.fit(X_dev, y_dev)
    test_probs = cal_baseline.predict_proba(X_test)[:, 1]
    test_preds = cal_baseline.predict(X_test)
    
    df_test, counts_test, border_test, hc_err_test, lc_corr_test = analyze_errors(X_test, y_test, test_preds, test_probs, "locked_test")
    test_f_stats = extract_feature_stats(df_test)
    
    # Feature importances/Contributions
    baseline_pipe.fit(X_dev, y_dev)
    clf = baseline_pipe.named_steps["model"]
    
    # Create the report data
    report_data = {
        "dev_counts": counts_dev,
        "test_counts": counts_test,
        "dev_high_conf_errors": hc_err_dev.to_dict(orient="records"),
        "test_high_conf_errors": hc_err_test.to_dict(orient="records"),
        "dev_low_conf_correct": lc_corr_dev.to_dict(orient="records"),
        "test_low_conf_correct": lc_corr_test.to_dict(orient="records"),
        "dev_feature_stats": dev_f_stats,
        "test_feature_stats": test_f_stats,
        "model_coefficients_magnitude_order": [] # We could extract names if needed, but not required strictly
    }
    
    with open(RESULTS_DIR / "error_analysis.json", "w") as f:
        json.dump(report_data, f, indent=2, default=str)
        
    print("Error analysis completed and saved to experiments/results/error_analysis.json")

if __name__ == "__main__":
    main()
