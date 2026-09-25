import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix
import time

from src.config.config import RAW_DATA_PATH, load_schema, RANDOM_SEED, BASE_DIR
from src.data.split import get_train_test_split
from src.preprocessing.preprocessor import PreprocessingFactory

# Models
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

def specificity_score(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        return tn / (tn + fp) if (tn + fp) > 0 else 0.0
    return 0.0

def run_nested_cv_experiment():
    print("Starting Nested CV Experiment (Phase 2B)...")
    
    # 1. Load Data
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    
    # 2. Train/Test Split (LOCKED 20% test set is isolated)
    X_train, X_test, y_train, y_test = get_train_test_split(df, schema["target_column"])
    
    factory = PreprocessingFactory()
    
    # 3. Models and Search Spaces
    models_config = {
        "Logistic Regression": {
            "estimator": LogisticRegression(random_state=RANDOM_SEED),
            "family": "linear",
            "search": "GridSearchCV",
            "param_grid": {
                "model__C": [0.01, 0.1, 1, 10, 100],
                "model__solver": ["lbfgs"],
                "model__class_weight": [None, "balanced"]
            }
        },
        "KNN": {
            "estimator": KNeighborsClassifier(),
            "family": "distance",
            "search": "GridSearchCV",
            "param_grid": {
                "model__n_neighbors": [3, 5, 7, 9, 11, 15, 21],
                "model__weights": ["uniform", "distance"],
                "model__metric": ["euclidean", "manhattan"]
            }
        },
        "SVM": {
            "estimator": SVC(probability=True, random_state=RANDOM_SEED),
            "family": "svm",
            "search": "GridSearchCV",
            "param_grid": {
                "model__C": [0.1, 1, 10, 100],
                "model__kernel": ["rbf", "linear"],
                "model__gamma": ["scale", "auto"]
            }
        },
        "Random Forest": {
            "estimator": RandomForestClassifier(random_state=RANDOM_SEED),
            "family": "tree",
            "search": "RandomizedSearchCV",
            "n_iter": 20,
            "param_grid": {
                "model__n_estimators": [100, 250, 500],
                "model__max_depth": [None, 3, 5, 8, 12],
                "model__min_samples_split": [2, 5, 10],
                "model__min_samples_leaf": [1, 2, 4],
                "model__max_features": ["sqrt", "log2"]
            }
        }
    }
    
    if HAS_XGBOOST:
        models_config["XGBoost"] = {
            "estimator": XGBClassifier(random_state=RANDOM_SEED, eval_metric='logloss'),
            "family": "tree",
            "search": "GridSearchCV",
            "param_grid": {
                "model__n_estimators": [100, 200, 400],
                "model__max_depth": [2, 3, 4],
                "model__learning_rate": [0.01, 0.05, 0.1],
                "model__subsample": [0.8, 1.0],
                "model__colsample_bytree": [0.8, 1.0]
            }
        }
        
    # Outer and Inner CV
    outer_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    
    results = []
    selected_parameters_all = {}
    
    for name, config in models_config.items():
        print(f"\nEvaluating {name} using Nested CV...")
        start_time = time.time()
        
        preprocessor = factory.get_preprocessing_pipeline(config["family"])
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", config["estimator"])
        ])
        
        inner_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
        
        if config["search"] == "GridSearchCV":
            search_obj = GridSearchCV(
                pipeline, config["param_grid"], cv=inner_cv, 
                scoring="roc_auc", n_jobs=-1
            )
            combos = int(np.prod([len(v) for v in config["param_grid"].values()]))
        else:
            search_obj = RandomizedSearchCV(
                pipeline, config["param_grid"], n_iter=config["n_iter"], cv=inner_cv, 
                scoring="roc_auc", n_jobs=-1, random_state=RANDOM_SEED
            )
            combos = int(config["n_iter"])
            
        metrics_dict = {
            "accuracy": [], "precision": [], "recall": [], "specificity": [], "f1": [], "roc_auc": [], "pr_auc": []
        }
        
        oof_preds = np.zeros(len(y_train))
        oof_probs = np.zeros(len(y_train))
        selected_params = []
        
        for fold, (train_idx, val_idx) in enumerate(outer_cv.split(X_train, y_train), 1):
            X_fold_train, y_fold_train = X_train.iloc[train_idx], y_train.iloc[train_idx]
            X_fold_val, y_fold_val = X_train.iloc[val_idx], y_train.iloc[val_idx]
            
            # Inner CV tuning
            search_obj.fit(X_fold_train, y_fold_train)
            
            # Best parameters for this fold
            best_p = search_obj.best_params_
            selected_params.append({f"Fold {fold}": best_p})
            
            # Predict on outer fold
            best_model = search_obj.best_estimator_
            preds = best_model.predict(X_fold_val)
            probs = best_model.predict_proba(X_fold_val)[:, 1]
            
            oof_preds[val_idx] = preds
            oof_probs[val_idx] = probs
            
            metrics_dict["accuracy"].append(accuracy_score(y_fold_val, preds))
            metrics_dict["precision"].append(precision_score(y_fold_val, preds))
            metrics_dict["recall"].append(recall_score(y_fold_val, preds))
            metrics_dict["specificity"].append(specificity_score(y_fold_val, preds))
            metrics_dict["f1"].append(f1_score(y_fold_val, preds))
            metrics_dict["roc_auc"].append(roc_auc_score(y_fold_val, probs))
            metrics_dict["pr_auc"].append(average_precision_score(y_fold_val, probs))
            
        selected_parameters_all[name] = selected_params
        
        # Calculate OOF Aggregate Metrics
        oof_accuracy = accuracy_score(y_train, oof_preds)
        oof_precision = precision_score(y_train, oof_preds)
        oof_recall = recall_score(y_train, oof_preds)
        oof_specificity = specificity_score(y_train, oof_preds)
        oof_f1 = f1_score(y_train, oof_preds)
        oof_roc_auc = roc_auc_score(y_train, oof_probs)
        oof_pr_auc = average_precision_score(y_train, oof_probs)
        
        res_entry = {
            "model": name,
            "search_strategy": config["search"],
            "search_combinations": combos,
            "accuracy_mean": np.mean(metrics_dict["accuracy"]),
            "accuracy_std": np.std(metrics_dict["accuracy"]),
            "accuracy_min": np.min(metrics_dict["accuracy"]),
            "accuracy_max": np.max(metrics_dict["accuracy"]),
            "precision_mean": np.mean(metrics_dict["precision"]),
            "precision_std": np.std(metrics_dict["precision"]),
            "precision_min": np.min(metrics_dict["precision"]),
            "precision_max": np.max(metrics_dict["precision"]),
            "recall_mean": np.mean(metrics_dict["recall"]),
            "recall_std": np.std(metrics_dict["recall"]),
            "recall_min": np.min(metrics_dict["recall"]),
            "recall_max": np.max(metrics_dict["recall"]),
            "specificity_mean": np.mean(metrics_dict["specificity"]),
            "specificity_std": np.std(metrics_dict["specificity"]),
            "specificity_min": np.min(metrics_dict["specificity"]),
            "specificity_max": np.max(metrics_dict["specificity"]),
            "f1_mean": np.mean(metrics_dict["f1"]),
            "f1_std": np.std(metrics_dict["f1"]),
            "f1_min": np.min(metrics_dict["f1"]),
            "f1_max": np.max(metrics_dict["f1"]),
            "roc_auc_mean": np.mean(metrics_dict["roc_auc"]),
            "roc_auc_std": np.std(metrics_dict["roc_auc"]),
            "roc_auc_min": np.min(metrics_dict["roc_auc"]),
            "roc_auc_max": np.max(metrics_dict["roc_auc"]),
            "pr_auc_mean": np.mean(metrics_dict["pr_auc"]),
            "pr_auc_std": np.std(metrics_dict["pr_auc"]),
            "pr_auc_min": np.min(metrics_dict["pr_auc"]),
            "pr_auc_max": np.max(metrics_dict["pr_auc"]),
            "oof_accuracy": oof_accuracy,
            "oof_precision": oof_precision,
            "oof_recall": oof_recall,
            "oof_specificity": oof_specificity,
            "oof_f1": oof_f1,
            "oof_roc_auc": oof_roc_auc,
            "oof_pr_auc": oof_pr_auc
        }
        results.append(res_entry)
        print(f"Finished {name} in {time.time() - start_time:.2f} seconds.")
        
    # Save Artifacts
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    with open(reports_dir / "phase2b_selected_parameters.json", "w") as f:
        json.dump(selected_parameters_all, f, indent=4)
        
    with open(reports_dir / "phase2b_nested_cv_results.json", "w") as f:
        json.dump({
            "experiment_name": "Phase 2B Nested CV", 
            "random_seed": RANDOM_SEED,
            "outer_cv": "StratifiedKFold(n_splits=5)",
            "inner_cv": "StratifiedKFold(n_splits=5)",
            "results": results
        }, f, indent=4)
        
    df_results = pd.DataFrame(results)
    df_results.to_csv(reports_dir / "phase2b_nested_cv_results.csv", index=False)
    
    print("Experiment Complete. Results saved to reports/")

if __name__ == "__main__":
    run_nested_cv_experiment()
