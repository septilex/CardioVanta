import os
import sys
import json
import time
import subprocess
import numpy as np
import pandas as pd
from pathlib import Path
import psutil
from sklearn.model_selection import train_test_split

from src.config.config import RAW_DATA_PATH, SCHEMA_PATH, BASE_DIR

EXP_DIR = BASE_DIR / "experiments" / "phase13"
EXP_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = BASE_DIR / "reports" / "phase13"

def get_dir_size(path="."):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def run_cold_start_measurement():
    # Write a temporary script to measure cold start and memory phases
    script_content = """
import time
t_start = time.perf_counter()
import os
import psutil

process = psutil.Process(os.getpid())
mem_baseline = process.memory_info().rss

# 1. Imports
import json
import pandas as pd
from pathlib import Path
from src.inference.predict import InferenceEngine
import shap
t_imports = time.perf_counter()
mem_imports = process.memory_info().rss

# 2. Engine loading
engine = InferenceEngine()
t_engine = time.perf_counter()
mem_engine = process.memory_info().rss

# 3. Explainer init
dev_idx_path = Path("data/processed/dev_indices.json")
with open(dev_idx_path, "r") as f:
    dev_idx = json.load(f)

df = pd.read_csv("data/raw/heart.csv")
df.columns = [col.replace('\\ufeff', '') for col in df.columns]

with open("artifacts/model/feature_schema.json", "r") as f:
    schema = json.load(f)
target_col = schema["target_column"]
X_full = df.drop(columns=[target_col])
X_dev = X_full.loc[dev_idx].reset_index(drop=True)

preprocessor = engine.explanation_model.named_steps['preprocessor']
lr_model = engine.explanation_model.named_steps['model']
X_dev_transformed = preprocessor.transform(X_dev)
feature_names = preprocessor.get_feature_names_out()

explainer = shap.LinearExplainer(lr_model, X_dev_transformed, feature_names=feature_names)
t_explainer = time.perf_counter()
mem_explainer = process.memory_info().rss

# 4. First explanation
raw_feature_order = schema["feature_order"]
sample_raw = X_dev.iloc[[0]].to_dict(orient='records')[0]

validated, _ = engine._validate_input(sample_raw)
ordered = {k: [validated[k]] for k in raw_feature_order}
df_input = pd.DataFrame(ordered)
sample_transformed = preprocessor.transform(df_input)

shap_vals = explainer.shap_values(sample_transformed)

t_first_explain = time.perf_counter()
mem_first_explain = process.memory_info().rss

print(f"{t_imports - t_start},{t_engine - t_imports},{t_explainer - t_engine},{t_first_explain - t_explainer}")
print(f"{mem_baseline},{mem_imports},{mem_engine},{mem_explainer},{mem_first_explain}")
"""
    tmp_path = "cold_start_tmp.py"
    with open(tmp_path, "w") as f:
        f.write(script_content)
        
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR)
    
    t0 = time.time()
    res = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, env=env)
    total_cold_start_wall_time = time.time() - t0
    
    os.remove(tmp_path)
    
    if res.returncode != 0:
        print("Cold start script failed:")
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        return None, None
        
    try:
        lines = res.stdout.strip().split("\n")
        times = [float(x) for x in lines[-2].split(",")]
        mems = [float(x) / 1024**2 for x in lines[-1].split(",")]
    except Exception as e:
        print("Error parsing cold start output:", e)
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        return None, None
    
    cold_start_times = {
        "imports_sec": times[0],
        "model_load_sec": times[1],
        "explainer_init_sec": times[2],
        "first_explanation_sec": times[3],
        "total_cold_start_wall_sec": total_cold_start_wall_time
    }
    
    memory_phases = {
        "baseline_mb": mems[0],
        "after_imports_mb": mems[1],
        "after_model_load_mb": mems[2],
        "after_explainer_init_mb": mems[3],
        "after_first_explanation_mb": mems[4]
    }
    
    return cold_start_times, memory_phases

def measure_bundle_size():
    # Site packages directory
    site_packages = Path(sys.executable).parent.parent / "Lib" / "site-packages"
    
    # Packages installed by shap
    packages = ["shap", "numba", "llvmlite", "slicer"]
    
    sizes = {}
    total = 0
    for pkg in packages:
        pkg_dir = site_packages / pkg
        if pkg_dir.exists():
            s = get_dir_size(pkg_dir)
            sizes[pkg] = s / 1024**2
            total += s
            
    return sizes, total / 1024**2


def map_to_raw(values_array, feature_names, raw_feature_order):
    raw_map = {f: 0.0 for f in raw_feature_order}
    for name, val in zip(feature_names, values_array):
        for f in raw_feature_order:
            if name.startswith(f"num__{f}") or name.startswith(f"bin__{f}") or name.startswith(f"cat__{f}_"):
                raw_map[f] += float(val)
                break
    return raw_map

def compute_global_importance(exp, X_trans, fnames, r_order):
    s_vals = exp.shap_values(X_trans)
    g_imp = {f: 0.0 for f in r_order}
    for idx in range(len(X_trans)):
        smpl = map_to_raw(s_vals[idx], fnames, r_order)
        for f in r_order:
            g_imp[f] += abs(smpl[f])
    for f in r_order:
        g_imp[f] /= len(X_trans)
    return g_imp

def main():
    print("Measuring Cold Start & Memory...")
    cold_start_times, memory_phases = run_cold_start_measurement()
    
    print("Measuring Bundle Impact...")
    bundle_sizes, bundle_total_mb = measure_bundle_size()
    
    import shap
    from src.inference.predict import InferenceEngine
    
    print("Loading Data for Warm Tests...")
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
    raw_feature_order = schema["feature_order"]
    
    engine = InferenceEngine()
    preprocessor = engine.explanation_model.named_steps['preprocessor']
    lr_model = engine.explanation_model.named_steps['model']
    X_dev_transformed = preprocessor.transform(X_dev)
    feature_names = preprocessor.get_feature_names_out()
    
    explainer = shap.LinearExplainer(lr_model, X_dev_transformed, feature_names=feature_names)
    expected_value = explainer.expected_value
    if isinstance(expected_value, np.ndarray):
        expected_value = expected_value[0]
        
    print("Running Warm End-to-End Latency Tests...")
    sample_raw = X_dev.iloc[[0]].to_dict(orient='records')[0]
    
    def end_to_end_explain():
        validated, _ = engine._validate_input(sample_raw)
        ordered = {k: [validated[k]] for k in raw_feature_order}
        df_input = pd.DataFrame(ordered)
        
        sample_transformed = preprocessor.transform(df_input)
        shap_vals = explainer.shap_values(sample_transformed)
        raw_mapped = map_to_raw(shap_vals[0], feature_names, raw_feature_order)
        
        # Serialize check (mock)
        resp = {
            "expected_value": expected_value,
            "contributions": raw_mapped
        }
        return json.dumps(resp)

    # Warm up
    for _ in range(10):
        end_to_end_explain()
        
    latencies = []
    n_runs = 2000
    for _ in range(n_runs):
        t0 = time.perf_counter()
        end_to_end_explain()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)
        
    process = psutil.Process(os.getpid())
    memory_after_warm_runs = process.memory_info().rss / 1024**2
        
    warm_latency = {
        "runs": n_runs,
        "median_ms": float(np.median(latencies)),
        "p95_ms": float(np.percentile(latencies, 95)),
        "p99_ms": float(np.percentile(latencies, 99)),
        "max_ms": float(np.max(latencies))
    }
    
    print("Testing Background Stability...")
    background_diffs = []
    base_imp = compute_global_importance(explainer, X_dev_transformed, feature_names, raw_feature_order)
    
    for i in range(5):
        X_sub, _, y_sub, _ = train_test_split(X_dev_transformed, y_dev, train_size=50, stratify=y_dev, random_state=42+i)
        exp_sub = shap.LinearExplainer(lr_model, X_sub, feature_names=feature_names)
        imp_sub = compute_global_importance(exp_sub, X_dev_transformed, feature_names, raw_feature_order)
        
        # max absolute difference in any feature's global importance
        max_diff = max([abs(base_imp[f] - imp_sub[f]) for f in raw_feature_order])
        background_diffs.append(max_diff)
        
    print("Comparing Explanations...")
    # Get local SHAP vs Current for 3 samples
    comparison = {}
    for idx in [0, 50, 100]:
        s_raw = X_dev.iloc[[idx]].to_dict(orient='records')[0]
        curr_exp = engine.explain(s_raw)
        
        ordered = {k: [s_raw[k]] for k in raw_feature_order}
        df_input = pd.DataFrame(ordered)
        s_trans = preprocessor.transform(df_input)
        s_shap = explainer.shap_values(s_trans)[0]
        shap_raw = map_to_raw(s_shap, feature_names, raw_feature_order)
        
        comparison[f"sample_{idx}"] = {
            "current_contributions": curr_exp["contributions"],
            "current_intercept": curr_exp["intercept"],
            "shap_contributions": shap_raw,
            "shap_expected_value": float(expected_value)
        }
        
    results = {
        "cold_start_sec": cold_start_times,
        "memory_mb": memory_phases,
        "memory_after_warm_mb": memory_after_warm_runs,
        "bundle_impact_mb": {
            "packages": bundle_sizes,
            "total_new_mb": bundle_total_mb,
            "vercel_limit_mb": 500
        },
        "warm_end_to_end_latency": warm_latency,
        "background_stability": {
            "max_importance_deviations_5_runs": [float(x) for x in background_diffs]
        },
        "explanation_comparison": comparison
    }
    
    with open(EXP_DIR / "shap_production_decision.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"Results saved to {EXP_DIR / 'shap_production_decision.json'}")

if __name__ == "__main__":
    main()
