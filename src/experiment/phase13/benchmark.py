import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import sklearn

from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedGroupKFold, GridSearchCV
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score, accuracy_score,
    precision_score, recall_score, f1_score, confusion_matrix,
    brier_score_loss, log_loss, roc_curve, precision_recall_curve
)
from sklearn.calibration import calibration_curve

from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

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
    
    models = {
        "Logistic Regression": {
            "family": "linear",
            "estimator": LogisticRegression(C=0.1, class_weight='balanced', solver='lbfgs', max_iter=1000, random_state=RANDOM_SEED),
            "param_grid": {} # Fixed baseline
        },
        "SVM": {
            "family": "svm",
            "estimator": SVC(probability=True, class_weight='balanced', random_state=RANDOM_SEED),
            "param_grid": {
                "model__C": [0.1, 1, 10],
                "model__kernel": ["linear", "rbf"]
            }
        },
        "Random Forest": {
            "family": "tree",
            "estimator": RandomForestClassifier(class_weight='balanced', random_state=RANDOM_SEED),
            "param_grid": {
                "model__n_estimators": [100, 200],
                "model__max_depth": [None, 5, 10]
            }
        },
        "XGBoost": {
            "family": "tree",
            "estimator": XGBClassifier(eval_metric='logloss', random_state=RANDOM_SEED),
            "param_grid": {
                "model__n_estimators": [100, 200],
                "model__max_depth": [3, 5],
                "model__learning_rate": [0.01, 0.1]
            }
        },
        "LightGBM": {
            "family": "tree",
            "estimator": LGBMClassifier(class_weight='balanced', random_state=RANDOM_SEED, verbose=-1),
            "param_grid": {
                "model__n_estimators": [100, 200],
                "model__max_depth": [3, 5],
                "model__learning_rate": [0.01, 0.1]
            }
        },
        "CatBoost": {
            "family": "tree",
            "estimator": CatBoostClassifier(verbose=0, random_state=RANDOM_SEED, allow_writing_files=False),
            "param_grid": {
                "model__iterations": [100, 200],
                "model__depth": [3, 5],
                "model__learning_rate": [0.01, 0.1]
            }
        }
    }
    
    cv_results = {}
    
    # Nested CV
    outer_cv = StratifiedGroupKFold(n_splits=5)
    
    for model_name, cfg in models.items():
        print(f"\n--- Evaluating {model_name} ---")
        preprocessor = factory.get_preprocessing_pipeline(cfg["family"])
        base_pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("model", cfg["estimator"])
        ])
        
        fold_metrics = []
        for fold, (train_idx, val_idx) in enumerate(outer_cv.split(X_dev, y_dev, groups=dev_groups)):
            X_tr, y_tr, groups_tr = X_dev.loc[train_idx], y_dev[train_idx], dev_groups[train_idx]
            X_val, y_val = X_dev.loc[val_idx], y_dev[val_idx]
            
            # Inner CV for tuning
            if cfg["param_grid"]:
                inner_cv = StratifiedGroupKFold(n_splits=5)
                search = GridSearchCV(base_pipe, cfg["param_grid"], cv=inner_cv, scoring="roc_auc", n_jobs=-1)
                search.fit(X_tr, y_tr, groups=groups_tr)
                best_params = search.best_params_
                
                cal_base = Pipeline([
                    ("preprocessor", factory.get_preprocessing_pipeline(cfg["family"])),
                    ("model", sklearn.base.clone(cfg["estimator"]).set_params(**{k.replace('model__',''): v for k,v in best_params.items()}))
                ])
            else:
                cal_base = base_pipe
                
            cal_cv_splits = list(StratifiedGroupKFold(n_splits=5).split(X_tr, y_tr, groups=groups_tr))
            cal_clf = CalibratedClassifierCV(estimator=cal_base, method='sigmoid', cv=cal_cv_splits)
            cal_clf.fit(X_tr, y_tr)
            
            y_prob = cal_clf.predict_proba(X_val)[:, 1]
            y_pred = (y_prob >= 0.5).astype(int)
            metrics = evaluate_predictions(y_val, y_pred, y_prob)
            fold_metrics.append(metrics)
            
        # Aggregate metrics
        avg_metrics = {k: np.mean([m[k] for m in fold_metrics]) for k in fold_metrics[0].keys()}
        std_metrics = {k: np.std([m[k] for m in fold_metrics]) for k in fold_metrics[0].keys()}
        
        cv_results[model_name] = {
            "mean": avg_metrics,
            "std": std_metrics
        }
        
        print(f"{model_name} CV ROC-AUC: {avg_metrics['ROC-AUC']:.4f} +/- {std_metrics['ROC-AUC']:.4f}")
        
    with open(EXP_DIR / "cv_results.json", "w") as f:
        json.dump(cv_results, f, indent=4)
        
    print("\n--- Final Model Training & Locked Test Set Evaluation ---")
    
    test_results = {}
    final_models = {}
    
    for model_name, cfg in models.items():
        print(f"Training final {model_name}...")
        preprocessor = factory.get_preprocessing_pipeline(cfg["family"])
        base_pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("model", cfg["estimator"])
        ])
        
        if cfg["param_grid"]:
            # Tune on full development set
            inner_cv = StratifiedGroupKFold(n_splits=5)
            search = GridSearchCV(base_pipe, cfg["param_grid"], cv=inner_cv, scoring="roc_auc", n_jobs=-1)
            search.fit(X_dev, y_dev, groups=dev_groups)
            best_params = search.best_params_
            
            cal_base = Pipeline([
                ("preprocessor", factory.get_preprocessing_pipeline(cfg["family"])),
                ("model", sklearn.base.clone(cfg["estimator"]).set_params(**{k.replace('model__',''): v for k,v in best_params.items()}))
            ])
            print(f"  Best params: {best_params}")
            cv_results[model_name]["best_params_on_full_dev"] = best_params
        else:
            cal_base = base_pipe
            
        cal_cv_splits = list(StratifiedGroupKFold(n_splits=5).split(X_dev, y_dev, groups=dev_groups))
        cal_clf = CalibratedClassifierCV(estimator=cal_base, method='sigmoid', cv=cal_cv_splits)
        cal_clf.fit(X_dev, y_dev)
        
        y_prob = cal_clf.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)
        
        metrics = evaluate_predictions(y_test, y_pred, y_prob)
        test_results[model_name] = metrics
        
        # Save plots
        plt.figure()
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        plt.plot(fpr, tpr, label=f"AUC = {metrics['ROC-AUC']:.4f}")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title(f"{model_name} ROC Curve")
        plt.legend()
        plt.savefig(REPORTS_DIR / f"{model_name.replace(' ', '_')}_roc.png")
        plt.close()
        
        plt.figure()
        precision, recall, _ = precision_recall_curve(y_test, y_prob)
        plt.plot(recall, precision, label=f"Avg Prec = {metrics['Average Precision']:.4f}")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title(f"{model_name} PR Curve")
        plt.legend()
        plt.savefig(REPORTS_DIR / f"{model_name.replace(' ', '_')}_pr.png")
        plt.close()
        
        plt.figure()
        prob_true, prob_pred = calibration_curve(y_test, y_prob, n_bins=10)
        plt.plot(prob_pred, prob_true, marker='o', label=f"Brier = {metrics['Brier Score']:.4f}")
        plt.plot([0, 1], [0, 1], linestyle='--')
        plt.xlabel("Mean Predicted Probability")
        plt.ylabel("Fraction of Positives")
        plt.title(f"{model_name} Calibration Curve")
        plt.legend()
        plt.savefig(REPORTS_DIR / f"{model_name.replace(' ', '_')}_calib.png")
        plt.close()
        
        plt.figure()
        sns.heatmap(confusion_matrix(y_test, y_pred), annot=True, fmt='d', cmap='Blues')
        plt.title(f"{model_name} Confusion Matrix")
        plt.savefig(REPORTS_DIR / f"{model_name.replace(' ', '_')}_cm.png")
        plt.close()
        
    with open(EXP_DIR / "test_results.json", "w") as f:
        json.dump(test_results, f, indent=4)
        
    # Re-save updated cv_results with best_params_on_full_dev
    with open(EXP_DIR / "cv_results.json", "w") as f:
        json.dump(cv_results, f, indent=4)
        
    print("Benchmark complete. Results saved in reports/phase13 and experiments/phase13")

if __name__ == "__main__":
    main()
