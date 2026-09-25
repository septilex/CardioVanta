import os
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
import psutil
from sklearn.model_selection import train_test_split
import shap

from src.config.config import RAW_DATA_PATH, SCHEMA_PATH, BASE_DIR
from src.inference.predict import InferenceEngine

EXP_DIR = BASE_DIR / "experiments" / "phase13"
EXP_DIR.mkdir(parents=True, exist_ok=True)

def map_to_raw(values_array, feature_names, raw_feature_order):
    raw_map = {f: 0.0 for f in raw_feature_order}
    for name, val in zip(feature_names, values_array):
        for f in raw_feature_order:
            if name.startswith(f"num__{f}") or name.startswith(f"bin__{f}") or name.startswith(f"cat__{f}_"):
                raw_map[f] += float(val)
                break
    return raw_map

def compute_global_importance(explainer, X_transformed, feature_names, raw_feature_order):
    shap_vals = explainer.shap_values(X_transformed)
    global_imp = {f: 0.0 for f in raw_feature_order}
    for i in range(len(X_transformed)):
        sample_shap = map_to_raw(shap_vals[i], feature_names, raw_feature_order)
        for f in raw_feature_order:
            global_imp[f] += abs(sample_shap[f])
    for f in raw_feature_order:
        global_imp[f] /= len(X_transformed)
    return global_imp

def get_process_memory_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024**2

def main():
    print("Loading data and model...")
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    
    with open(SCHEMA_PATH, "r") as f:
        schema = json.load(f)
        
    target_col = schema["target_column"]
    X_full = df.drop(columns=[target_col])
    y_full = df[target_col]
    
    X_dev = X_full.loc[dev_idx].reset_index(drop=True)
    y_dev = y_full.loc[dev_idx].reset_index(drop=True)
    
    engine = InferenceEngine()
    preprocessor = engine.explanation_model.named_steps['preprocessor']
    lr_model = engine.explanation_model.named_steps['model']
    
    X_dev_transformed = preprocessor.transform(X_dev)
    feature_names = preprocessor.get_feature_names_out()
    raw_feature_order = schema["feature_order"]
    
    results = {}
    
    # 1 & 2. Additivity and Raw-Feature Mapping Validation
    print("Testing Additivity...")
    explainer_all = shap.LinearExplainer(lr_model, X_dev_transformed, feature_names=feature_names)
    shap_vals_all = explainer_all.shap_values(X_dev_transformed)
    expected_val = explainer_all.expected_value
    if isinstance(expected_val, np.ndarray):
        expected_val = expected_val[0]
        
    actual_decision_functions = engine.explanation_model.decision_function(X_dev)
    
    additivity_pass_count = 0
    raw_mapping_pass_count = 0
    
    for i in range(len(X_dev)):
        shap_sum = sum(shap_vals_all[i])
        raw_mapped = map_to_raw(shap_vals_all[i], feature_names, raw_feature_order)
        raw_mapped_sum = sum(raw_mapped.values())
        
        # Verify raw mapping sums to the same total SHAP value
        if np.isclose(shap_sum, raw_mapped_sum, atol=1e-5):
            raw_mapping_pass_count += 1
            
        # Verify Additivity
        total_pred = shap_sum + expected_val
        if np.isclose(total_pred, actual_decision_functions[i], atol=1e-5):
            additivity_pass_count += 1
            
    results["additivity"] = {
        "samples_tested": len(X_dev),
        "additivity_pass_rate": additivity_pass_count / len(X_dev),
        "raw_mapping_pass_rate": raw_mapping_pass_count / len(X_dev)
    }
    
    # 3. Background Strategies
    print("Testing Background Strategies...")
    X_100, _, y_100, _ = train_test_split(X_dev_transformed, y_dev, train_size=100, stratify=y_dev, random_state=42)
    X_25, _, y_25, _ = train_test_split(X_dev_transformed, y_dev, train_size=25, stratify=y_dev, random_state=42)
    
    explainer_100 = shap.LinearExplainer(lr_model, X_100, feature_names=feature_names)
    explainer_25 = shap.LinearExplainer(lr_model, X_25, feature_names=feature_names)
    
    # 4. Global Importance Stability
    imp_all = compute_global_importance(explainer_all, X_dev_transformed, feature_names, raw_feature_order)
    imp_100 = compute_global_importance(explainer_100, X_dev_transformed, feature_names, raw_feature_order)
    imp_25 = compute_global_importance(explainer_25, X_dev_transformed, feature_names, raw_feature_order)
    
    # Sort them by ALL background
    sorted_features = sorted(imp_all.items(), key=lambda x: x[1], reverse=True)
    sorted_feature_names = [x[0] for x in sorted_features]
    
    global_importance_comparison = {}
    for f in sorted_feature_names:
        global_importance_comparison[f] = {
            "all_dev": imp_all[f],
            "stratified_100": imp_100[f],
            "stratified_25": imp_25[f]
        }
        
    results["background_sensitivity"] = {
        "global_importance": global_importance_comparison
    }
    
    # 6. Performance Validation
    print("Measuring Performance...")
    # Pre-warm
    sample_to_explain = X_dev_transformed[0:1]
    _ = explainer_all.shap_values(sample_to_explain)
    
    latencies = []
    mem_before = get_process_memory_mb()
    
    n_runs = 5000
    t_start = time.time()
    for _ in range(n_runs):
        t0 = time.perf_counter()
        _ = explainer_all.shap_values(sample_to_explain)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000) # ms
        
    t_total = time.time() - t_start
    mem_after = get_process_memory_mb()
    
    results["performance"] = {
        "runs": n_runs,
        "median_latency_ms": float(np.median(latencies)),
        "p95_latency_ms": float(np.percentile(latencies, 95)),
        "max_latency_ms": float(np.max(latencies)),
        "total_time_sec": t_total,
        "rss_memory_mb_before": mem_before,
        "rss_memory_mb_after": mem_after,
        "rss_memory_diff_mb": mem_after - mem_before
    }
    
    # 7. Reproducibility
    rep_1 = explainer_all.shap_values(sample_to_explain)[0]
    rep_2 = explainer_all.shap_values(sample_to_explain)[0]
    is_reproducible = bool(np.allclose(rep_1, rep_2))
    
    results["reproducibility"] = {
        "exact_match_across_runs": is_reproducible
    }
    
    with open(EXP_DIR / "shap_robustness.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"Done. Saved to {EXP_DIR / 'shap_robustness.json'}")

if __name__ == "__main__":
    main()
