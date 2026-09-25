import os
import json
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path

import shap
from src.config.config import RAW_DATA_PATH, SCHEMA_PATH, BASE_DIR
from src.inference.predict import InferenceEngine

EXP_DIR = BASE_DIR / "experiments" / "phase13"
EXP_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = BASE_DIR / "reports" / "phase13"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR = EXP_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def map_to_raw(values_array, feature_names, raw_feature_order):
    raw_map = {f: 0.0 for f in raw_feature_order}
    for name, val in zip(feature_names, values_array):
        for f in raw_feature_order:
            if name.startswith(f"num__{f}") or name.startswith(f"bin__{f}") or name.startswith(f"cat__{f}_"):
                raw_map[f] += float(val)
                break
    return raw_map

def generate_dataset_hash(df):
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values).hexdigest()

def main():
    print("Loading data and model...")
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    dataset_hash = generate_dataset_hash(df.loc[dev_idx])
    
    with open(SCHEMA_PATH, "r") as f:
        schema = json.load(f)
        
    target_col = schema["target_column"]
    X_full = df.drop(columns=[target_col])
    
    X_dev = X_full.loc[dev_idx].reset_index(drop=True)
    raw_feature_order = schema["feature_order"]
    
    engine = InferenceEngine()
    preprocessor = engine.explanation_model.named_steps['preprocessor']
    lr_model = engine.explanation_model.named_steps['model']
    
    X_dev_transformed = preprocessor.transform(X_dev)
    feature_names = preprocessor.get_feature_names_out()
    
    # 1. SHAP Baseline
    print("Computing SHAP Ground Truth...")
    explainer = shap.LinearExplainer(lr_model, X_dev_transformed, feature_names=feature_names)
    shap_expected_value = explainer.expected_value
    if isinstance(shap_expected_value, np.ndarray):
        shap_expected_value = shap_expected_value[0]
    shap_vals = explainer.shap_values(X_dev_transformed)
    
    # 2. Manual SHAP-Equivalent Calculation
    print("Computing Manual SHAP-Equivalent...")
    # Extract the EXACT background mean used by SHAP's default configuration 
    # (which implicitly downsamples to 100 k-means clusters because len(X_dev) > 100)
    background_mean = explainer.mean
    coef = lr_model.coef_[0]
    intercept = lr_model.intercept_[0]
    
    # Expected value is intercept + sum(coef * E[X])
    manual_expected_value = float(intercept + np.sum(coef * background_mean))
    
    # Contributions = coef * (X - E[X])
    manual_contributions_transformed = coef * (X_dev_transformed - background_mean)
    
    # 3. Validation
    print("Validating...")
    max_err_transformed = 0.0
    mean_err_transformed = 0.0
    max_err_raw = 0.0
    mean_err_raw = 0.0
    
    additivity_pass_count = 0
    raw_mapping_pass_count = 0
    match_shap_count = 0
    
    actual_decision_functions = engine.explanation_model.decision_function(X_dev)
    
    for i in range(len(X_dev)):
        s_val = shap_vals[i]
        m_val = manual_contributions_transformed[i]
        
        # Error on transformed features
        err_trans = np.abs(s_val - m_val)
        max_err_transformed = max(max_err_transformed, np.max(err_trans))
        mean_err_transformed += np.mean(err_trans)
        
        # Map to raw
        s_raw = map_to_raw(s_val, feature_names, raw_feature_order)
        m_raw = map_to_raw(m_val, feature_names, raw_feature_order)
        
        # Error on raw features
        for f in raw_feature_order:
            err = abs(s_raw[f] - m_raw[f])
            max_err_raw = max(max_err_raw, err)
            mean_err_raw += err
            
        # Additivity
        m_sum = sum(m_raw.values())
        if np.isclose(m_sum + manual_expected_value, actual_decision_functions[i], atol=1e-5):
            additivity_pass_count += 1
            
        # Raw mapping pass (raw sum matches transformed sum)
        if np.isclose(m_sum, np.sum(m_val), atol=1e-5):
            raw_mapping_pass_count += 1
            
        # Match SHAP perfectly
        if np.allclose(s_val, m_val, atol=1e-5) and np.isclose(shap_expected_value, manual_expected_value, atol=1e-5):
            match_shap_count += 1
            
    mean_err_transformed /= len(X_dev)
    mean_err_raw /= (len(X_dev) * len(raw_feature_order))
    
    # 4. Artifact Generation
    background_artifact = {
        "metadata": {
            "version": "1.0",
            "model_reference": "explanation_model.joblib",
            "dataset_hash": dataset_hash,
            "description": "Frozen background means for SHAP-equivalent explanations."
        },
        "expected_value": float(manual_expected_value),
        "background_means": {
            name: float(val) for name, val in zip(feature_names, background_mean)
        },
        "feature_names": list(feature_names)
    }
    
    artifact_path = ARTIFACTS_DIR / "shap_background.json"
    with open(artifact_path, "w") as f:
        json.dump(background_artifact, f, indent=4)
        
    artifact_size_bytes = os.path.getsize(artifact_path)
    
    # 5. Results
    results = {
        "shap_configuration": {
            "explainer": "shap.LinearExplainer",
            "feature_dependence": "independent",
            "background": "implicit_kmeans_100_clusters"
        },
        "mathematical_formula": "contribution_i = coefficient_i * (transformed_value_i - background_mean_i)",
        "expected_value_comparison": {
            "shap_expected_value": float(shap_expected_value),
            "manual_expected_value": float(manual_expected_value),
            "difference": abs(float(shap_expected_value) - float(manual_expected_value))
        },
        "validation_errors": {
            "max_absolute_difference_transformed": float(max_err_transformed),
            "mean_absolute_difference_transformed": float(mean_err_transformed),
            "max_absolute_difference_raw": float(max_err_raw),
            "mean_absolute_difference_raw": float(mean_err_raw)
        },
        "pass_rates": {
            "total_samples": len(X_dev),
            "additivity_pass_rate": additivity_pass_count / len(X_dev),
            "raw_mapping_pass_rate": raw_mapping_pass_count / len(X_dev),
            "exact_shap_match_rate": match_shap_count / len(X_dev)
        },
        "background_artifact": {
            "path": str(artifact_path),
            "size_bytes": artifact_size_bytes
        }
    }
    
    with open(EXP_DIR / "shap_equivalent_validation.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"Validation complete. Saved to {EXP_DIR / 'shap_equivalent_validation.json'}")

if __name__ == "__main__":
    main()
