import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
import sklearn
import joblib
import torch

from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score, accuracy_score,
    precision_score, recall_score, f1_score, confusion_matrix,
    brier_score_loss, log_loss
)

try:
    from tabicl import TabICLClassifier
except ImportError:
    pass

from src.config.config import RAW_DATA_PATH, SCHEMA_PATH, RANDOM_SEED, BASE_DIR
from src.preprocessing.preprocessor import PreprocessingFactory

def specificity_score(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
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

def paired_bootstrap(y_true, y_prob_1, y_prob_2, y_pred_1, y_pred_2, n_iterations=10000, random_seed=RANDOM_SEED):
    np.random.seed(random_seed)
    n_samples = len(y_true)
    metrics_diff = {
        'ROC-AUC': [],
        'Average Precision': [],
        'Brier Score': [],
        'Log Loss': [],
        'F1': [],
        'Recall': [],
        'Specificity': []
    }
    for _ in range(n_iterations):
        indices = np.random.randint(0, n_samples, n_samples)
        yt = y_true[indices]
        
        if len(np.unique(yt)) < 2:
            continue
            
        yp1 = y_prob_1[indices]
        yp2 = y_prob_2[indices]
        yd1 = y_pred_1[indices]
        yd2 = y_pred_2[indices]
        
        m1 = evaluate_predictions(yt, yd1, yp1)
        m2 = evaluate_predictions(yt, yd2, yp2)
        
        metrics_diff['ROC-AUC'].append(m1['ROC-AUC'] - m2['ROC-AUC'])
        metrics_diff['Average Precision'].append(m1['Average Precision'] - m2['Average Precision'])
        metrics_diff['Brier Score'].append(m1['Brier Score'] - m2['Brier Score'])
        metrics_diff['Log Loss'].append(m1['Log Loss'] - m2['Log Loss'])
        metrics_diff['F1'].append(m1['F1'] - m2['F1'])
        metrics_diff['Recall'].append(m1['Recall'] - m2['Recall'])
        metrics_diff['Specificity'].append(m1['Specificity'] - m2['Specificity'])
        
    intervals = {}
    for k, v in metrics_diff.items():
        intervals[k] = {
            'mean': np.mean(v),
            'lower_95': np.percentile(v, 2.5),
            'upper_95': np.percentile(v, 97.5)
        }
    return intervals

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
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print("1. Loading Production LR (from artifacts)")
    prod_model_path = BASE_DIR / "artifacts" / "model" / "model.joblib"
    prod_lr = joblib.load(prod_model_path)
    
    print("2. Re-training Phase 13 LR (max_iter=1000)")
    p13_base_pipe = Pipeline([
        ("preprocessor", factory.get_preprocessing_pipeline("linear")),
        ("model", LogisticRegression(C=0.1, class_weight='balanced', solver='lbfgs', max_iter=1000, random_state=RANDOM_SEED))
    ])
    cal_cv_splits = list(StratifiedGroupKFold(n_splits=5).split(X_dev, y_dev, groups=dev_groups))
    p13_lr = CalibratedClassifierCV(estimator=p13_base_pipe, method='sigmoid', cv=cal_cv_splits)
    p13_lr.fit(X_dev, y_dev)
    
    print("3. Training TabICLv2 Native")
    tabicl_native = TabICLClassifier(device=device)
    tabicl_native.fit(X_dev.values, y_dev)
    
    print("4. Training TabICLv2 Calibrated")
    tabicl_calibrated = CalibratedClassifierCV(estimator=TabICLClassifier(device=device), method='sigmoid', cv=cal_cv_splits)
    tabicl_calibrated.fit(X_dev.values, y_dev)
    
    models = {
        "Production LR": (prod_lr, X_test),
        "Phase 13 LR": (p13_lr, X_test),
        "TabICLv2 Native": (tabicl_native, X_test.values),
        "TabICLv2 Calibrated": (tabicl_calibrated, X_test.values)
    }
    
    results = {}
    for name, (model, X) in models.items():
        y_prob = model.predict_proba(X)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)
        metrics = evaluate_predictions(y_test, y_pred, y_prob)
        results[name] = {
            "metrics": metrics,
            "predictions": y_pred.tolist(),
            "probabilities": y_prob.tolist()
        }
        
    print("\nMetrics:")
    for name, res in results.items():
        print(f"{name}: ROC-AUC={res['metrics']['ROC-AUC']:.4f}, Brier={res['metrics']['Brier Score']:.4f}")
        
    print("\nRunning Paired Bootstrap Analysis (TabICLv2 Native vs Production LR)...")
    y_prob_tabicl = np.array(results["TabICLv2 Native"]["probabilities"])
    y_pred_tabicl = np.array(results["TabICLv2 Native"]["predictions"])
    y_prob_prod = np.array(results["Production LR"]["probabilities"])
    y_pred_prod = np.array(results["Production LR"]["predictions"])
    
    bootstrap_intervals = paired_bootstrap(
        y_test, 
        y_prob_tabicl, 
        y_prob_prod, 
        y_pred_tabicl, 
        y_pred_prod,
        n_iterations=10000
    )
    
    results["Bootstrap Analysis (TabICLv2 Native - Production LR)"] = bootstrap_intervals
    
    for k, v in bootstrap_intervals.items():
        print(f"{k} Diff: {v['mean']:.4f} (95% CI: [{v['lower_95']:.4f}, {v['upper_95']:.4f}])")
        
    out_path = BASE_DIR / "experiments" / "phase13" / "tabicl_statistical_audit.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\nSaved results to {out_path}")

if __name__ == "__main__":
    main()
