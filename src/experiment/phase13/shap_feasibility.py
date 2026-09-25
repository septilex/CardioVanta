import os
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
import joblib
import tracemalloc

import shap

from src.config.config import RAW_DATA_PATH, SCHEMA_PATH, BASE_DIR
from src.inference.predict import InferenceEngine

# Ensure output dirs
REPORTS_DIR = BASE_DIR / "reports" / "phase13"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
EXP_DIR = BASE_DIR / "experiments" / "phase13"
EXP_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print(f"SHAP Version: {shap.__version__}")
    
    # Load data
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
    
    X_dev = X_full.loc[dev_idx].reset_index(drop=True)
    
    print("Loading Production Explanation Model...")
    engine = InferenceEngine()
    
    # Transform background dataset
    preprocessor = engine.explanation_model.named_steps['preprocessor']
    lr_model = engine.explanation_model.named_steps['model']
    
    X_dev_transformed = preprocessor.transform(X_dev)
    feature_names = preprocessor.get_feature_names_out()
    
    # Measure SHAP runtime and memory
    print("Initializing SHAP LinearExplainer...")
    tracemalloc.start()
    t_start = time.time()
    
    # LinearExplainer uses the model and background data to compute expected values
    explainer = shap.LinearExplainer(lr_model, X_dev_transformed, feature_names=feature_names)
    
    t_init = time.time() - t_start
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"LinearExplainer init time: {t_init:.4f}s")
    print(f"LinearExplainer peak memory: {peak_mem / 1024**2:.4f} MB")
    
    # Calculate SHAP values for a sample
    sample_idx = 0
    sample_raw = X_dev.iloc[[sample_idx]].to_dict(orient='records')[0]
    sample_transformed = preprocessor.transform(X_dev.iloc[[sample_idx]])
    
    t_start_explain = time.time()
    shap_values = explainer.shap_values(sample_transformed)
    t_explain = time.time() - t_start_explain
    
    # Mapping back to raw features
    raw_feature_order = schema["feature_order"]
    
    def map_to_raw(values_array):
        raw_map = {f: 0.0 for f in raw_feature_order}
        for name, val in zip(feature_names, values_array):
            for f in raw_feature_order:
                if name.startswith(f"num__{f}") or name.startswith(f"bin__{f}") or name.startswith(f"cat__{f}_"):
                    raw_map[f] += float(val)
                    break
        return raw_map

    shap_raw_contributions = map_to_raw(shap_values[0])
    
    # Get current method explanations
    current_explanation = engine.explain(sample_raw)
    current_contributions = current_explanation["contributions"]
    
    # SHAP vs Current Output Agreement
    # SHAP sum(values) + explainer.expected_value == model output (log-odds)
    shap_sum = sum(shap_raw_contributions.values())
    shap_expected_value = explainer.expected_value
    if isinstance(shap_expected_value, np.ndarray):
        shap_expected_value = shap_expected_value[0]
        
    shap_log_odds = shap_sum + shap_expected_value
    current_log_odds = current_explanation["decision_function_log_odds"]
    
    print(f"\nLocal Explanation (Sample {sample_idx}):")
    print(f"SHAP sum + expected: {shap_log_odds:.5f}")
    print(f"Current log-odds: {current_log_odds:.5f}")
    
    discrepancies = {}
    for f in raw_feature_order:
        discrepancies[f] = abs(shap_raw_contributions[f] - current_contributions[f])
    
    # Global Feature Importance
    shap_values_dev = explainer.shap_values(X_dev_transformed)
    global_importance_raw = {f: 0.0 for f in raw_feature_order}
    
    # For global importance, we sum the absolute SHAP values per raw feature across all samples
    # then take the mean
    for i in range(len(X_dev_transformed)):
        sample_shap = map_to_raw(shap_values_dev[i])
        for f in raw_feature_order:
            global_importance_raw[f] += abs(sample_shap[f])
            
    for f in raw_feature_order:
        global_importance_raw[f] /= len(X_dev_transformed)
        
    global_importance_sorted = dict(sorted(global_importance_raw.items(), key=lambda item: item[1], reverse=True))
    
    results = {
        "shap_version": shap.__version__,
        "metrics": {
            "init_time_sec": t_init,
            "peak_memory_mb": peak_mem / 1024**2,
            "explanation_time_sec": t_explain
        },
        "sample_explanation_agreement": {
            "shap_log_odds": shap_log_odds,
            "current_log_odds": current_log_odds,
            "is_equal": bool(np.isclose(shap_log_odds, current_log_odds, atol=1e-5)),
            "shap_expected_value": float(shap_expected_value),
            "current_intercept": current_explanation["intercept"]
        },
        "discrepancies": discrepancies,
        "global_importance": global_importance_sorted
    }
    
    with open(EXP_DIR / "shap_feasibility.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\nResults saved to {EXP_DIR / 'shap_feasibility.json'}")

if __name__ == "__main__":
    main()
