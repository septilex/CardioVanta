import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.pipeline import Pipeline
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
except ImportError:
    pass

def specificity_score(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        return tn / (tn + fp) if (tn + fp) > 0 else 0.0
    return 0.0

def run_phase2c_evaluation():
    print("Starting Phase 2C: Final Model Evaluation...")
    reports_dir = BASE_DIR / "reports"
    
    # 1. Load Phase 2B Results
    df_results = pd.read_csv(reports_dir / "phase2b_nested_cv_results.csv")
    
    # 2. Select Candidate based on highest ROC-AUC mean
    # Sort by roc_auc_mean DESC, then pr_auc_mean DESC, roc_auc_std ASC
    df_results = df_results.sort_values(
        by=['roc_auc_mean', 'pr_auc_mean', 'roc_auc_std', 'f1_mean', 'recall_mean'],
        ascending=[False, False, True, False, False]
    )
    
    best_row = df_results.iloc[0]
    selected_model_name = best_row['model']
    
    print(f"Selected Candidate: {selected_model_name}")
    print(f"Selection criteria: Highest OUTER-CV ROC-AUC ({best_row['roc_auc_mean']:.3f})")
    
    # 3. Load Selected Parameters and find the most common configuration
    with open(reports_dir / "phase2b_selected_parameters.json", "r") as f:
        selected_params = json.load(f)
        
    model_params_list = selected_params[selected_model_name]
    # Extract just the parameter dicts
    param_dicts = [list(fold_dict.values())[0] for fold_dict in model_params_list]
    
    # Simple majority vote by hashing JSON representation
    param_counts = {}
    for p in param_dicts:
        # Convert dict to string for hashable counting
        p_str = json.dumps(p, sort_keys=True)
        param_counts[p_str] = param_counts.get(p_str, 0) + 1
        
    best_p_str = max(param_counts, key=param_counts.get)
    final_params = json.loads(best_p_str)
    
    # Clean keys (remove 'model__' prefix)
    clean_params = {k.replace('model__', ''): v for k, v in final_params.items()}
    
    # Instantiate the estimator
    if selected_model_name == "Logistic Regression":
        estimator = LogisticRegression(random_state=RANDOM_SEED, **clean_params)
        family = "linear"
    elif selected_model_name == "KNN":
        estimator = KNeighborsClassifier(**clean_params)
        family = "distance"
    elif selected_model_name == "SVM":
        estimator = SVC(probability=True, random_state=RANDOM_SEED, **clean_params)
        family = "svm"
    elif selected_model_name == "Random Forest":
        estimator = RandomForestClassifier(random_state=RANDOM_SEED, **clean_params)
        family = "tree"
    elif selected_model_name == "XGBoost":
        estimator = XGBClassifier(random_state=RANDOM_SEED, eval_metric='logloss', **clean_params)
        family = "tree"
    else:
        raise ValueError(f"Unknown model: {selected_model_name}")
        
    # 4. Final Training Pipeline
    # Load Data
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    
    # Get Split
    X_train, X_test, y_train, y_test = get_train_test_split(df, schema["target_column"])
    
    factory = PreprocessingFactory()
    preprocessor = factory.get_preprocessing_pipeline(family)
    
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("model", estimator)
    ])
    
    # 5. Fit on ALL 80% development data
    print("Fitting model on full 80% development dataset...")
    pipeline.fit(X_train, y_train)
    
    # 6. Locked Final Test Evaluation (Only run ONCE)
    print("Evaluating on locked 20% test set...")
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    
    test_metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "specificity": specificity_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_prob),
        "pr_auc": average_precision_score(y_test, y_prob)
    }
    
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    test_cm_list = cm.tolist()
    
    # 7. Compare Performance Gap
    # Compare against OOF from Phase 2B
    gap_metrics = {}
    for met, val in test_metrics.items():
        oof_key = f"oof_{met}"
        gap_metrics[f"gap_{met}"] = val - best_row[oof_key]
        
    # 9. Final Artifacts
    evaluation_doc = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selected_model": selected_model_name,
        "selection_rule": "Highest mean OUTER-CV ROC-AUC from Phase 2B. Tie breakers: PR-AUC, ROC-AUC Std, F1, Recall",
        "phase2b_evidence": {
            "roc_auc_mean": best_row['roc_auc_mean'],
            "roc_auc_std": best_row['roc_auc_std'],
            "oof_roc_auc": best_row['oof_roc_auc'],
            "oof_f1": best_row['oof_f1']
        },
        "final_parameter_configuration": final_params,
        "preprocessing_profile": family,
        "development_dataset_size": len(X_train),
        "final_test_dataset_size": len(X_test),
        "test_dataset_positives": int(y_test.sum()),
        "test_dataset_negatives": int(len(y_test) - y_test.sum()),
        "test_metrics": test_metrics,
        "performance_gap": gap_metrics,
        "confusion_matrix": test_cm_list
    }
    
    with open(reports_dir / "phase2c_model_selection.json", "w") as f:
        json.dump({"selected_model": selected_model_name, "final_parameters": final_params}, f, indent=4)
        
    with open(reports_dir / "phase2c_final_evaluation.json", "w") as f:
        json.dump(evaluation_doc, f, indent=4)
        
    # Also save as flat CSV for easy inspection
    flat_record = {
        "selected_model": selected_model_name,
        "test_roc_auc": test_metrics["roc_auc"],
        "test_f1": test_metrics["f1"],
        "test_accuracy": test_metrics["accuracy"],
        "gap_roc_auc": gap_metrics["gap_roc_auc"],
        "gap_f1": gap_metrics["gap_f1"]
    }
    pd.DataFrame([flat_record]).to_csv(reports_dir / "phase2c_final_evaluation.csv", index=False)
    
    print("Phase 2C Complete. Test Evaluation artifacts saved.")

if __name__ == "__main__":
    run_phase2c_evaluation()
