import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix

from src.config.config import RAW_DATA_PATH, load_schema, RANDOM_SEED, BASE_DIR
from src.data.split import get_train_test_split
from src.preprocessing.preprocessor import PreprocessingFactory

# Models
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

def run_baseline_experiment():
    print("Starting Baseline Experiment (Phase 2A)...")
    
    # 1. Load Data
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    
    # 2. Get Train/Test Split
    # CRITICAL: We only use X_train and y_train for Phase 2A.
    X_train, X_test, y_train, y_test = get_train_test_split(df, schema["target_column"])
    
    factory = PreprocessingFactory()
    
    # 3. Define Models and Parameters
    models = {
        "Logistic Regression": {
            "estimator": LogisticRegression(max_iter=1000, random_state=RANDOM_SEED),
            "family": "linear",
            "params": {"max_iter": 1000, "random_state": RANDOM_SEED}
        },
        "KNN": {
            "estimator": KNeighborsClassifier(n_neighbors=7),
            "family": "distance",
            "params": {"n_neighbors": 7}
        },
        "Decision Tree": {
            "estimator": DecisionTreeClassifier(random_state=RANDOM_SEED),
            "family": "tree",
            "params": {"random_state": RANDOM_SEED}
        },
        "Random Forest": {
            "estimator": RandomForestClassifier(n_estimators=100, random_state=RANDOM_SEED),
            "family": "tree",
            "params": {"n_estimators": 100, "random_state": RANDOM_SEED}
        },
        "SVM": {
            "estimator": SVC(probability=True, random_state=RANDOM_SEED),
            "family": "svm",
            "params": {"probability": True, "random_state": RANDOM_SEED}
        },
        "Gradient Boosting": {
            "estimator": GradientBoostingClassifier(random_state=RANDOM_SEED),
            "family": "tree",
            "params": {"random_state": RANDOM_SEED}
        }
    }
    
    if HAS_XGBOOST:
        models["XGBoost"] = {
            "estimator": XGBClassifier(random_state=RANDOM_SEED, eval_metric='logloss'),
            "family": "tree",
            "params": {"random_state": RANDOM_SEED, "eval_metric": 'logloss'}
        }
    
    # 4. CV Setup
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    
    results = []
    
    # 5. Evaluate
    for name, config in models.items():
        print(f"Evaluating {name}...")
        preprocessor = factory.get_preprocessing_pipeline(config["family"])
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", config["estimator"])
        ])
        
        metrics = {
            "accuracy": [], "precision": [], "recall": [], "f1": [], "roc_auc": [], "pr_auc": []
        }
        
        oof_preds = np.zeros(len(y_train))
        
        for train_idx, val_idx in cv.split(X_train, y_train):
            X_fold_train, y_fold_train = X_train.iloc[train_idx], y_train.iloc[train_idx]
            X_fold_val, y_fold_val = X_train.iloc[val_idx], y_train.iloc[val_idx]
            
            pipeline.fit(X_fold_train, y_fold_train)
            preds = pipeline.predict(X_fold_val)
            probs = pipeline.predict_proba(X_fold_val)[:, 1]
            
            oof_preds[val_idx] = preds
            
            metrics["accuracy"].append(accuracy_score(y_fold_val, preds))
            metrics["precision"].append(precision_score(y_fold_val, preds))
            metrics["recall"].append(recall_score(y_fold_val, preds))
            metrics["f1"].append(f1_score(y_fold_val, preds))
            metrics["roc_auc"].append(roc_auc_score(y_fold_val, probs))
            metrics["pr_auc"].append(average_precision_score(y_fold_val, probs))
            
        cm = confusion_matrix(y_train, oof_preds)
        
        results.append({
            "model": name,
            "family": config["family"],
            "params": config["params"],
            "accuracy_mean": np.mean(metrics["accuracy"]),
            "accuracy_std": np.std(metrics["accuracy"]),
            "precision_mean": np.mean(metrics["precision"]),
            "precision_std": np.std(metrics["precision"]),
            "recall_mean": np.mean(metrics["recall"]),
            "recall_std": np.std(metrics["recall"]),
            "f1_mean": np.mean(metrics["f1"]),
            "f1_std": np.std(metrics["f1"]),
            "roc_auc_mean": np.mean(metrics["roc_auc"]),
            "roc_auc_std": np.std(metrics["roc_auc"]),
            "pr_auc_mean": np.mean(metrics["pr_auc"]),
            "pr_auc_std": np.std(metrics["pr_auc"]),
            "confusion_matrix": cm.tolist()
        })
        
    # 6. Save Artifacts
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    with open(reports_dir / "model_baseline_results.json", "w") as f:
        json.dump({"experiment_name": "Phase 2A Baseline", "random_seed": RANDOM_SEED, "cv_folds": 5, "results": results}, f, indent=4)
        
    df_results = pd.DataFrame([{k: v for k, v in r.items() if k not in ["params", "confusion_matrix"]} for r in results])
    df_results.to_csv(reports_dir / "model_baseline_results.csv", index=False)
    
    print("Experiment Complete. Results saved to reports/")

if __name__ == "__main__":
    run_baseline_experiment()
