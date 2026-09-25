import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, precision_recall_curve, auc, balanced_accuracy_score, average_precision_score
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression

from src.config.config import RAW_DATA_PATH, load_schema, RANDOM_SEED, BASE_DIR
from src.preprocessing.preprocessor import PreprocessingFactory

CALIBRATION_CV = 5

def get_calibration_method():
    cal_file = BASE_DIR / "reports" / "phase3_calibration_results.json"
    if not cal_file.exists():
        raise FileNotFoundError("Phase 3 calibration report missing. Cannot proceed.")
    with open(cal_file, "r") as f:
        data = json.load(f)
    return data["selected_method"]

def calculate_metrics_for_threshold(y_true, y_prob, threshold):
    y_pred = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    else:
        tn, fp, fn, tp = 0, 0, 0, 0 # handle edge cases safely
        if len(np.unique(y_true)) == 1:
            if y_true[0] == 0:
                tn = sum(y_pred == 0)
                fp = sum(y_pred == 1)
            else:
                fn = sum(y_pred == 0)
                tp = sum(y_pred == 1)
                
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
    balanced_accuracy = (recall + specificity) / 2
    youden_j = recall + specificity - 1
    
    return {
        "threshold": float(np.round(threshold, 2)),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "specificity": float(specificity),
        "f1": float(f1),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "fpr": float(fpr),
        "fnr": float(fnr),
        "balanced_accuracy": float(balanced_accuracy),
        "youden_j": float(youden_j)
    }

def get_base_pipeline():
    factory = PreprocessingFactory()
    base_params = {'C': 0.1, 'class_weight': 'balanced', 'solver': 'lbfgs', 'random_state': RANDOM_SEED}
    return Pipeline([
        ('preprocessor', factory.get_preprocessing_pipeline('linear')),
        ('model', LogisticRegression(**base_params))
    ])

def train_and_predict(X_train, y_train, X_val, calibration_method):
    base_pipe = get_base_pipeline()
    if calibration_method == 'uncalibrated':
        base_pipe.fit(X_train, y_train)
        return base_pipe.predict_proba(X_val)[:, 1]
    else:
        # Use cv=5 to match the exact final calibrated model from Phase 3
        cal_clf = CalibratedClassifierCV(estimator=base_pipe, method=calibration_method, cv=CALIBRATION_CV)
        cal_clf.fit(X_train, y_train)
        return cal_clf.predict_proba(X_val)[:, 1]

def select_threshold_candidates(metrics_list):
    candidates = {}
    
    # 1. Default (0.50)
    default_m = next((m for m in metrics_list if np.isclose(m['threshold'], 0.50)), metrics_list[0])
    candidates['default'] = default_m
    
    # 2. Youden's J
    max_youden = max([m['youden_j'] for m in metrics_list])
    # Tie breaking: pick the one closest to 0.5 if tied
    youden_ties = [m for m in metrics_list if np.isclose(m['youden_j'], max_youden)]
    youden_best = min(youden_ties, key=lambda x: abs(x['threshold'] - 0.5))
    candidates['youden_j'] = youden_best
    
    # 3. Maximum F1
    max_f1 = max([m['f1'] for m in metrics_list])
    f1_ties = [m for m in metrics_list if np.isclose(m['f1'], max_f1)]
    f1_best = min(f1_ties, key=lambda x: abs(x['threshold'] - 0.5))
    candidates['max_f1'] = f1_best
    
    return candidates

def get_error_type(y_true, y_prob, threshold):
    y_pred = int(y_prob >= threshold)
    if y_true == 1 and y_pred == 1:
        return 'TP'
    elif y_true == 0 and y_pred == 0:
        return 'TN'
    elif y_true == 0 and y_pred == 1:
        return 'FP'
    elif y_true == 1 and y_pred == 0:
        return 'FN'
        
def analyze_error_patterns(df_errors, feature_cols):
    patterns = {}
    for col in feature_cols:
        patterns[col] = {}
        is_numeric = pd.api.types.is_numeric_dtype(df_errors[col])
        unique_vals = df_errors[col].nunique()
        
        groups = ['TP', 'TN', 'FP', 'FN', 'overall']
        
        for g in groups:
            if g == 'overall':
                sub = df_errors
            else:
                sub = df_errors[df_errors['error_type'] == g]
                
            if len(sub) == 0:
                patterns[col][g] = {"count": 0}
                continue
                
            if is_numeric and unique_vals > 5:
                patterns[col][g] = {
                    "count": len(sub),
                    "mean": float(sub[col].mean()),
                    "std": float(sub[col].std()),
                    "median": float(sub[col].median()),
                    "min": float(sub[col].min()),
                    "max": float(sub[col].max())
                }
            else:
                counts = sub[col].value_counts(normalize=True).to_dict()
                patterns[col][g] = {
                    "count": len(sub),
                    "proportions": {str(k): float(v) for k, v in counts.items()}
                }
    return patterns

def run_phase4a():
    print("Starting Phase 4A: Decision Threshold + Error Analysis...")
    reports_dir = BASE_DIR / "reports"
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Lock the Data Boundary
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    if not dev_idx_path.exists():
        raise FileNotFoundError("Frozen development indices not found.")
        
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    
    X_full = df.drop(columns=[schema["target_column"]])
    y_full = df[schema["target_column"]].to_numpy()
    
    X_train = X_full.loc[dev_idx].reset_index(drop=True)
    y_train = y_full[dev_idx]
    
    original_dev_indices = np.array(dev_idx)
    
    # 2. Identify calibration method
    cal_method = get_calibration_method()
    print(f"Using calibration method from Phase 3: {cal_method}, cv={CALIBRATION_CV}")
    
    # 3. Generate Leakage-Safe Out-Of-Fold Development Predictions
    kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    
    oof_results = []
    
    for fold, (tr_idx, val_idx) in enumerate(kf.split(X_train, y_train)):
        X_tr, y_tr = X_train.iloc[tr_idx], y_train[tr_idx]
        X_val, y_val = X_train.iloc[val_idx], y_train[val_idx]
        
        y_prob = train_and_predict(X_tr, y_tr, X_val, cal_method)
        
        for i, prob, true_label in zip(val_idx, y_prob, y_val):
            oof_results.append({
                "dev_index": int(i),
                "original_sample_index": int(original_dev_indices[i]),
                "true_label": int(true_label),
                "predicted_probability": float(prob),
                "fold_id": int(fold + 1)
            })
            
    df_oof = pd.DataFrame(oof_results)
    df_oof = df_oof.sort_values('dev_index').reset_index(drop=True)
    df_oof.to_csv(reports_dir / "phase4a_oof_predictions.csv", index=False)
    
    # 4. Threshold Grid Analysis (0.05 to 0.95 inclusive, step 0.01)
    y_true_oof = df_oof['true_label'].values
    y_prob_oof = df_oof['predicted_probability'].values
    
    thresholds = np.round(np.arange(0.05, 0.96, 0.01), 2)
    grid_metrics = []
    
    for t in thresholds:
        grid_metrics.append(calculate_metrics_for_threshold(y_true_oof, y_prob_oof, t))
        
    df_grid = pd.DataFrame(grid_metrics)
    df_grid.to_csv(reports_dir / "phase4a_threshold_metrics.csv", index=False)
    
    # 5. Compare Important Operating Points
    candidates = select_threshold_candidates(grid_metrics)
    
    with open(reports_dir / "phase4a_threshold_analysis.json", "w") as f:
        json.dump({
            "note": "A statistically selected threshold is NOT automatically a clinically validated decision threshold. These are descriptive mathematical operating points on the pooled development dataset. Do not call 0.41 or 0.45 a production threshold.",
            "calibration_method": cal_method,
            "calibration_cv": CALIBRATION_CV,
            "candidates": candidates
        }, f, indent=4)
        
    # 6. Nested Threshold Selection (Stability)
    outer_kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED+1)
    
    stability_results = []
    
    for fold, (outer_tr_idx, outer_val_idx) in enumerate(outer_kf.split(X_train, y_train)):
        X_outer_tr, y_outer_tr = X_train.iloc[outer_tr_idx], y_train[outer_tr_idx]
        X_outer_val, y_outer_val = X_train.iloc[outer_val_idx], y_train[outer_val_idx]
        
        inner_kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED+2)
        inner_oof_probs = np.zeros(len(y_outer_tr))
        
        for inner_tr_idx, inner_val_idx in inner_kf.split(X_outer_tr, y_outer_tr):
            X_in_tr, y_in_tr = X_outer_tr.iloc[inner_tr_idx], y_outer_tr[inner_tr_idx]
            X_in_val, y_in_val = X_outer_tr.iloc[inner_val_idx], y_outer_tr[inner_val_idx]
            
            prob = train_and_predict(X_in_tr, y_in_tr, X_in_val, cal_method)
            inner_oof_probs[inner_val_idx] = prob
            
        # Grid search on inner OOF
        inner_metrics = []
        for t in thresholds:
            inner_metrics.append(calculate_metrics_for_threshold(y_outer_tr, inner_oof_probs, t))
        
        inner_candidates = select_threshold_candidates(inner_metrics)
        
        # Apply selected thresholds to outer val
        outer_prob = train_and_predict(X_outer_tr, y_outer_tr, X_outer_val, cal_method)
        
        fold_res = {"fold": fold + 1}
        for cand_name in ['youden_j', 'max_f1']:
            t_sel = inner_candidates[cand_name]['threshold']
            val_metrics = calculate_metrics_for_threshold(y_outer_val, outer_prob, t_sel)
            fold_res[f"{cand_name}_threshold"] = float(t_sel)
            for m in ['accuracy', 'precision', 'recall', 'specificity', 'f1', 'balanced_accuracy']:
                fold_res[f"{cand_name}_{m}"] = float(val_metrics[m])
                
        stability_results.append(fold_res)
        
    df_stab = pd.DataFrame(stability_results)
    stability_summary = {}
    for cand_name in ['youden_j', 'max_f1']:
        stability_summary[cand_name] = {
            "threshold_mean": float(df_stab[f"{cand_name}_threshold"].mean()),
            "threshold_std": float(df_stab[f"{cand_name}_threshold"].std()),
            "threshold_min": float(df_stab[f"{cand_name}_threshold"].min()),
            "threshold_max": float(df_stab[f"{cand_name}_threshold"].max()),
        }
        for m in ['accuracy', 'precision', 'recall', 'specificity', 'f1', 'balanced_accuracy']:
            stability_summary[cand_name][f"outer_fold_{m}_mean"] = float(df_stab[f"{cand_name}_{m}"].mean())
            stability_summary[cand_name][f"outer_fold_{m}_std"] = float(df_stab[f"{cand_name}_{m}"].std())
            
    with open(reports_dir / "phase4a_threshold_stability.json", "w") as f:
        json.dump({
            "note": "Estimated using Nested 5x5 Cross-Validation on Development Data. Explains threshold selection stability separately from pooled OOF threshold candidates.",
            "calibration_method": cal_method,
            "calibration_cv": CALIBRATION_CV,
            "outer_folds": stability_results,
            "summary": stability_summary
        }, f, indent=4)
        
    # 7. Error Analysis
    error_rows = []
    
    for i, row in df_oof.iterrows():
        dev_idx = int(row['dev_index'])
        orig_idx = int(row['original_sample_index'])
        prob = row['predicted_probability']
        yt = int(row['true_label'])
        
        for cand_name, cand_metrics in candidates.items():
            t = cand_metrics['threshold']
            e_type = get_error_type(yt, prob, t)
            
            feat_dict = X_train.iloc[dev_idx].to_dict()
            
            err_dict = {
                "development_sample_index": dev_idx,
                "original_sample_index": orig_idx,
                "true_label": yt,
                "predicted_probability": float(prob),
                "predicted_class": int(prob >= t),
                "candidate": cand_name,
                "threshold": float(t),
                "error_type": e_type
            }
            err_dict.update(feat_dict)
            error_rows.append(err_dict)
            
    df_err = pd.DataFrame(error_rows)
    df_err.to_csv(reports_dir / "phase4a_error_analysis.csv", index=False)
    
    # 8. Error Pattern Analysis
    error_patterns = {}
    for cand_name in candidates.keys():
        sub_err = df_err[df_err['candidate'] == cand_name]
        error_patterns[cand_name] = analyze_error_patterns(sub_err, list(X_train.columns))
        
    with open(reports_dir / "phase4a_error_patterns.json", "w") as f:
        json.dump({
            "note": "Descriptive patterns observed in the development sample. Represents observed association within the development sample and does not imply statistical significance or clinical meaning.",
            "patterns_by_candidate": error_patterns
        }, f, indent=4)
        
    # 9. ROC + Precision-Recall Visual Analysis
    fpr, tpr, _ = roc_curve(y_true_oof, y_prob_oof)
    roc_auc = auc(fpr, tpr)
    
    plt.figure()
    plt.plot(fpr, tpr, label=f'OOF ROC (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], linestyle='--', color='gray')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate (Sensitivity)')
    plt.title('ROC Curve (Development OOF)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures_dir / "phase4a_roc_curve.png")
    plt.close()
    
    precision_vals, recall_vals, _ = precision_recall_curve(y_true_oof, y_prob_oof)
    pr_auc = average_precision_score(y_true_oof, y_prob_oof)
    
    plt.figure()
    plt.plot(recall_vals, precision_vals, label=f'OOF PR (Avg Prec = {pr_auc:.3f})')
    plt.xlabel('Recall (Sensitivity)')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve (Development OOF)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures_dir / "phase4a_pr_curve.png")
    plt.close()
    
    plt.figure()
    plt.plot(df_grid['threshold'], df_grid['recall'], label='Sensitivity (Recall)')
    plt.plot(df_grid['threshold'], df_grid['specificity'], label='Specificity')
    plt.xlabel('Decision Threshold')
    plt.ylabel('Metric Value')
    plt.title('Threshold vs Sensitivity & Specificity (Development OOF)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_dir / "phase4a_threshold_sens_spec.png")
    plt.close()
    
    plt.figure()
    plt.plot(df_grid['threshold'], df_grid['precision'], label='Precision')
    plt.plot(df_grid['threshold'], df_grid['recall'], label='Recall')
    plt.plot(df_grid['threshold'], df_grid['f1'], label='F1 Score')
    plt.xlabel('Decision Threshold')
    plt.ylabel('Metric Value')
    plt.title('Threshold vs Precision / Recall / F1 (Development OOF)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_dir / "phase4a_threshold_prec_rec_f1.png")
    plt.close()
    
    import seaborn as sns
    for cand_name, cand_metrics in candidates.items():
        cm = confusion_matrix(df_err[(df_err['candidate'] == cand_name)]['true_label'], df_err[(df_err['candidate'] == cand_name)]['predicted_class'])
        plt.figure()
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.xlabel('Predicted')
        plt.ylabel('True')
        plt.title(f'Confusion Matrix ({cand_name}) Threshold {cand_metrics["threshold"]:.2f}')
        plt.tight_layout()
        plt.savefig(figures_dir / f"phase4a_cm_{cand_name}.png")
        plt.close()

    print("Phase 4A Verified.")

if __name__ == "__main__":
    run_phase4a()
