import os
import json
import hashlib
import pandas as pd
import numpy as np
import sklearn
import joblib
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
import re

from src.config.config import RAW_DATA_PATH, SCHEMA_PATH, RANDOM_SEED, BASE_DIR
from src.preprocessing.preprocessor import PreprocessingFactory

def get_file_hash(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def verify_sklearn_version():
    req_path = BASE_DIR / "requirements.txt"
    # requirements.txt is utf-16le encoded
    try:
        with open(req_path, "r", encoding="utf-16le") as f:
            content = f.read()
    except Exception:
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()
    
    # Try finding scikit-learn version in requirements
    match = re.search(r'scikit-learn==([\d\.]+)', content)
    if not match:
        raise ValueError("Could not find exact scikit-learn==X.Y.Z in requirements.txt")
    
    req_version = match.group(1)
    if sklearn.__version__ != req_version:
        raise ValueError(f"Environment sklearn version {sklearn.__version__} does not match requirements.txt {req_version}")
    return req_version

def _build_calibration_splits(X, y, groups, cal_cv):
    sgkf = StratifiedGroupKFold(n_splits=cal_cv)
    return list(sgkf.split(X, y, groups=groups))

def build_production_package():
    print("Starting Phase 5: Final Model Packaging...")
    
    req_version = verify_sklearn_version()
    
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    
    with open(SCHEMA_PATH, "r") as f:
        schema = json.load(f)
        
    X_full = df.drop(columns=[schema["target_column"]])
    y_full = df[schema["target_column"]].to_numpy()
    
    X_train = X_full.loc[dev_idx].reset_index(drop=True)
    y_train = y_full[dev_idx]
    
    # Identify exact duplicate feature rows within development
    dev_groups = X_train.groupby(list(X_train.columns)).ngroup().values
    
    factory = PreprocessingFactory()
    base_params = {'C': 0.1, 'class_weight': 'balanced', 'solver': 'lbfgs', 'random_state': RANDOM_SEED}
    base_pipe = Pipeline([
        ('preprocessor', factory.get_preprocessing_pipeline('linear')),
        ('model', LogisticRegression(**base_params))
    ])
    
    splits = _build_calibration_splits(X_train, y_train, dev_groups, 5)
    cal_clf = CalibratedClassifierCV(estimator=base_pipe, method='sigmoid', cv=splits)
    
    print("Fitting final production model on full development set...")
    cal_clf.fit(X_train, y_train)
    
    # Package Directory
    artifacts_dir = BASE_DIR / "artifacts" / "model"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Serialized Production Model
    joblib.dump(cal_clf, artifacts_dir / "model.joblib")
    
    # 1b. Explanation-Only Model (Full-Development Uncalibrated Logistic Regression)
    # Required for consistency with Phase 3 explainability design
    explanation_model = Pipeline([
        ('preprocessor', factory.get_preprocessing_pipeline('linear')),
        ('model', LogisticRegression(**base_params))
    ])
    explanation_model.fit(X_train, y_train)
    joblib.dump(explanation_model, artifacts_dir / "explanation_model.joblib")
    
    # 2. Feature Schema
    with open(artifacts_dir / "feature_schema.json", "w") as f:
        json.dump(schema, f, indent=4)
        
    # Load explainability context
    global_exp_path = BASE_DIR / "reports" / "phase3_global_importance.json"
    global_exp = {}
    if global_exp_path.exists():
        with open(global_exp_path, "r") as f:
            global_exp = json.load(f)
            
    # 3. Metadata
    metadata = {
        "package_version": "1.0.0",
        "model_version": "Phase5-Final",
        "training_data_provenance": {
            "source_dataset_name": "heart.csv",
            "raw_dataset_sha256": get_file_hash(RAW_DATA_PATH),
            "development_indices_sha256": get_file_hash(dev_idx_path),
            "development_sample_count": len(dev_idx),
            "locked_test_sample_count_provenance_only": len(df) - len(dev_idx)
        },
        "random_seed": RANDOM_SEED,
        "environment": {
            "sklearn_version": req_version
        },
        "feature_schema_version": "1.0",
        "model_configuration": {
            "algorithm": "Logistic Regression",
            "hyperparameters": base_params,
            "preprocessing": "StandardScaler for continuous, OneHotEncoder(ignore) for categorical, passthrough for binary."
        },
        "calibration_configuration": {
            "method": "sigmoid",
            "cv": 5,
            "duplicate_aware_grouping": True
        },
        "threshold_policy": {
            "note": "A statistically selected threshold is NOT automatically a clinically validated decision threshold. Production inference must return calibrated probability. Applying a threshold is optional. Any threshold is a mathematical operating point, not a clinical diagnosis.",
            "candidates": {
                "default": 0.50,
                "youden_j": 0.46,
                "max_f1": 0.43
            },
            "authoritative_clinical_threshold": None
        },
        "explainability_context": {
            "note": "Local explanations detail the underlying uncalibrated Logistic Regression decision function/log-odds. They do NOT decompose the final calibrated ensemble probability. Neither global nor local explanations imply clinical causality.",
            "global_permutation_importance": global_exp
        }
    }
    
    with open(artifacts_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    # 4. Reference Predictions
    print("Generating reference predictions...")
    preds = cal_clf.predict_proba(X_train)[:, 1]
    ref_df = pd.DataFrame({
        "dev_index": dev_idx,
        "reference_probability": preds
    })
    ref_df.to_csv(artifacts_dir / "reference_predictions.csv", index=False)
    
    print("Phase 5 Packaging Complete.")

if __name__ == "__main__":
    build_production_package()
