import os
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import sklearn
import psutil
import torch

from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score, accuracy_score,
    precision_score, recall_score, f1_score, confusion_matrix,
    brier_score_loss, log_loss, roc_curve, precision_recall_curve
)
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression

# Try to import TabICL
try:
    from tabicl import TabICLClassifier
except ImportError:
    print("tabicl package not found, please install it.")
    sys.exit(1)

from src.config.config import RAW_DATA_PATH, SCHEMA_PATH, RANDOM_SEED, BASE_DIR
from src.preprocessing.preprocessor import PreprocessingFactory

# Ensure output dirs
REPORTS_DIR = BASE_DIR / "reports" / "phase13"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
EXP_DIR = BASE_DIR / "experiments" / "phase13"
EXP_DIR.mkdir(parents=True, exist_ok=True)

def specificity_score(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return tn / (tn + fp) if (tn + fp) > 0 else 0.0

def evaluate_predictions(y_true, y_pred, y_prob):
    return {
        "ROC-AUC": roc_auc_score(y_true, y_prob),
        "Average Precision": average_precision_score(y_true, y_prob),
        "Accuracy": accuracy_score(y_true, y_pred),
        "Precision": precision_score(y_true, y_pred, zero_division=0),
        "Recall": recall_score(y_true, y_pred, zero_division=0),
        "Specificity": specificity_score(y_true, y_pred),
        "F1": f1_score(y_true, y_pred, zero_division=0),
        "Brier Score": brier_score_loss(y_true, y_prob),
        "Log Loss": log_loss(y_true, y_prob)
    }

def main():
    print("Loading data...")
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    
    with open(SCHEMA_PATH, "r") as f:
        schema = json.load(f)
        
    target_col = schema["target_column"]
    X_full = df.drop(columns=[target_col])
    y_full = df[target_col].to_numpy()
    
    test_idx = [i for i in df.index if i not in dev_idx]
    
    X_dev = X_full.loc[dev_idx].reset_index(drop=True)
    y_dev = y_full[dev_idx]
    
    X_test = X_full.loc[test_idx].reset_index(drop=True)
    y_test = y_full[test_idx]
    
    dev_groups = X_dev.groupby(list(X_dev.columns)).ngroup().values
    
    factory = PreprocessingFactory()
    
    # Track metrics
    cv_results = {}
    runtimes = {}
    vram_peaks = {}
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
        
    models = {
        "Logistic Regression Baseline": {
            "type": "baseline",
            "estimator": Pipeline([
                ("preprocessor", factory.get_preprocessing_pipeline("linear")),
                ("model", LogisticRegression(C=0.1, class_weight='balanced', solver='lbfgs', max_iter=1000, random_state=RANDOM_SEED))
            ])
        },
        "TabICLv2 Native": {
            "type": "tabicl",
            "estimator": TabICLClassifier(device=device)
        },
        "TabICLv2 Calibrated": {
            "type": "tabicl_calibrated",
            "estimator": TabICLClassifier(device=device)
        }
    }
    
    outer_cv = StratifiedGroupKFold(n_splits=5)
    
    for model_name, cfg in models.items():
        print(f"\n--- Evaluating {model_name} ---")
        t_start_cv = time.time()
        
        fold_metrics = []
        fold_times = []
        
        for fold, (train_idx, val_idx) in enumerate(outer_cv.split(X_dev, y_dev, groups=dev_groups)):
            t_fold_start = time.time()
            X_tr, y_tr, groups_tr = X_dev.loc[train_idx], y_dev[train_idx], dev_groups[train_idx]
            X_val, y_val = X_dev.loc[val_idx], y_dev[val_idx]
            
            if cfg["type"] == "baseline":
                cal_cv_splits = list(StratifiedGroupKFold(n_splits=5).split(X_tr, y_tr, groups=groups_tr))
                clf = CalibratedClassifierCV(estimator=cfg["estimator"], method='sigmoid', cv=cal_cv_splits)
                clf.fit(X_tr, y_tr)
                
            elif cfg["type"] == "tabicl":
                clf = sklearn.base.clone(cfg["estimator"])
                # Note: For TabICL, preprocessor is NOT needed natively. It handles raw inputs (numerical, categorical if specified).
                # Wait! The dataset has mixed types. TabICLClassifier handles tabular data but might need string encoding if not natively supported?
                # The feasibility test successfully ran directly on raw numpy values. 
                # Feasibility test dropped the target column and did .values on raw CSV. So it works.
                # Here X_tr is a DataFrame. We should convert to .values
                X_tr_val = X_tr.values
                X_val_val = X_val.values
                
                clf.fit(X_tr_val, y_tr)
                
            elif cfg["type"] == "tabicl_calibrated":
                # Calibrated TabICL
                cal_cv_splits = list(StratifiedGroupKFold(n_splits=5).split(X_tr, y_tr, groups=groups_tr))
                # For CalibratedClassifierCV, we pass the cloned TabICL
                base_clf = sklearn.base.clone(cfg["estimator"])
                clf = CalibratedClassifierCV(estimator=base_clf, method='sigmoid', cv=cal_cv_splits)
                
                X_tr_val = X_tr.values
                X_val_val = X_val.values
                clf.fit(X_tr_val, y_tr)
                
            # Predict
            if cfg["type"] == "baseline":
                y_prob = clf.predict_proba(X_val)[:, 1]
            else:
                y_prob = clf.predict_proba(X_val_val)[:, 1]
                
            y_pred = (y_prob >= 0.5).astype(int)
            metrics = evaluate_predictions(y_val, y_pred, y_prob)
            fold_metrics.append(metrics)
            
            fold_time = time.time() - t_fold_start
            fold_times.append(fold_time)
            
        t_end_cv = time.time()
        
        avg_metrics = {k: np.mean([m[k] for m in fold_metrics]) for k in fold_metrics[0].keys()}
        std_metrics = {k: np.std([m[k] for m in fold_metrics]) for k in fold_metrics[0].keys()}
        
        cv_results[model_name] = {
            "mean": avg_metrics,
            "std": std_metrics,
            "fold_times": fold_times,
            "total_cv_time": t_end_cv - t_start_cv
        }
        
        print(f"{model_name} CV ROC-AUC: {avg_metrics['ROC-AUC']:.4f} +/- {std_metrics['ROC-AUC']:.4f}")
        print(f"Total CV Time: {t_end_cv - t_start_cv:.2f}s")
        
        if device == "cuda":
            peak_vram = torch.cuda.max_memory_allocated() / (1024 * 1024)
            vram_peaks[model_name] = peak_vram
            print(f"Peak VRAM: {peak_vram:.2f} MB")
            torch.cuda.reset_peak_memory_stats()
            
    with open(EXP_DIR / "tabicl_cv_results.json", "w") as f:
        json.dump(cv_results, f, indent=4)
        
    print("\n--- Final Model Training & Locked Test Set Evaluation ---")
    
    test_results = {}
    
    for model_name, cfg in models.items():
        print(f"Training final {model_name}...")
        t_start = time.time()
        
        if cfg["type"] == "baseline":
            cal_cv_splits = list(StratifiedGroupKFold(n_splits=5).split(X_dev, y_dev, groups=dev_groups))
            clf = CalibratedClassifierCV(estimator=cfg["estimator"], method='sigmoid', cv=cal_cv_splits)
            clf.fit(X_dev, y_dev)
            
            y_prob = clf.predict_proba(X_test)[:, 1]
            
        elif cfg["type"] == "tabicl":
            clf = sklearn.base.clone(cfg["estimator"])
            X_dev_val = X_dev.values
            X_test_val = X_test.values
            clf.fit(X_dev_val, y_dev)
            
            y_prob = clf.predict_proba(X_test_val)[:, 1]
            
        elif cfg["type"] == "tabicl_calibrated":
            cal_cv_splits = list(StratifiedGroupKFold(n_splits=5).split(X_dev, y_dev, groups=dev_groups))
            base_clf = sklearn.base.clone(cfg["estimator"])
            clf = CalibratedClassifierCV(estimator=base_clf, method='sigmoid', cv=cal_cv_splits)
            
            X_dev_val = X_dev.values
            X_test_val = X_test.values
            clf.fit(X_dev_val, y_dev)
            
            y_prob = clf.predict_proba(X_test_val)[:, 1]
            
        t_end = time.time()
        
        y_pred = (y_prob >= 0.5).astype(int)
        
        metrics = evaluate_predictions(y_test, y_pred, y_prob)
        metrics['final_train_eval_time'] = t_end - t_start
        test_results[model_name] = metrics
        
        # Save plots
        plt.figure()
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        plt.plot(fpr, tpr, label=f"AUC = {metrics['ROC-AUC']:.4f}")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title(f"{model_name} ROC Curve")
        plt.legend()
        plt.savefig(REPORTS_DIR / f"tabicl_{model_name.replace(' ', '_')}_roc.png")
        plt.close()
        
        plt.figure()
        precision, recall, _ = precision_recall_curve(y_test, y_prob)
        plt.plot(recall, precision, label=f"Avg Prec = {metrics['Average Precision']:.4f}")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title(f"{model_name} PR Curve")
        plt.legend()
        plt.savefig(REPORTS_DIR / f"tabicl_{model_name.replace(' ', '_')}_pr.png")
        plt.close()
        
        plt.figure()
        prob_true, prob_pred = calibration_curve(y_test, y_prob, n_bins=10)
        plt.plot(prob_pred, prob_true, marker='o', label=f"Brier = {metrics['Brier Score']:.4f}")
        plt.plot([0, 1], [0, 1], linestyle='--')
        plt.xlabel("Mean Predicted Probability")
        plt.ylabel("Fraction of Positives")
        plt.title(f"{model_name} Calibration Curve")
        plt.legend()
        plt.savefig(REPORTS_DIR / f"tabicl_{model_name.replace(' ', '_')}_calib.png")
        plt.close()
        
        plt.figure()
        sns.heatmap(confusion_matrix(y_test, y_pred), annot=True, fmt='d', cmap='Blues')
        plt.title(f"{model_name} Confusion Matrix")
        plt.savefig(REPORTS_DIR / f"tabicl_{model_name.replace(' ', '_')}_cm.png")
        plt.close()
        
    with open(EXP_DIR / "tabicl_test_results.json", "w") as f:
        json.dump(test_results, f, indent=4)
        
    print("Benchmark complete. Results saved in reports/phase13 and experiments/phase13")

if __name__ == "__main__":
    main()
