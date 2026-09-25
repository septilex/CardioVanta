import os
import sys
import time
import json
import psutil
import torch
import numpy as np
import pandas as pd
from pathlib import Path

def get_dir_size(path):
    total_size = 0
    if os.path.exists(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    return total_size

def main():
    print("Starting TabICLv2 Feasibility Test...")
    results = {}
    
    # 1. Versions
    results['python_version'] = sys.version
    results['pytorch_version'] = torch.__version__
    
    try:
        import tabicl
        results['tabicl_version'] = getattr(tabicl, '__version__', 'unknown')
        from tabicl import TabICLClassifier
    except ImportError as e:
        results['error'] = f"Failed to import tabicl: {str(e)}"
        save_results(results)
        return

    # 2. Hardware
    device = "cuda" if torch.cuda.is_available() else "cpu"
    results['device_used'] = device
    if device == "cuda":
        results['gpu_name'] = torch.cuda.get_device_name(0)

    process = psutil.Process(os.getpid())
    results['ram_before_init_mb'] = process.memory_info().rss / (1024 * 1024)
    if device == "cuda":
        results['vram_before_init_mb'] = torch.cuda.memory_allocated(0) / (1024 * 1024)

    # 3. Initialize Model
    print("Initializing TabICL...")
    t0 = time.time()
    try:
        clf = TabICLClassifier(device=device)
    except Exception as e:
        results['error'] = f"Failed to init TabICLClassifier: {str(e)}"
        save_results(results)
        return
        
    results['model_init_time_sec'] = time.time() - t0
    
    # Track RAM/VRAM after init
    results['ram_after_init_mb'] = process.memory_info().rss / (1024 * 1024)
    if device == "cuda":
        results['vram_after_init_mb'] = torch.cuda.memory_allocated(0) / (1024 * 1024)
        
    # Find checkpoint size
    hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
    # TabICL models are usually under soda-inria
    tabicl_models = [d for d in os.listdir(hf_cache) if "tabicl" in d.lower() or "soda-inria" in d.lower()] if os.path.exists(hf_cache) else []
    if tabicl_models:
        model_dir = os.path.join(hf_cache, tabicl_models[0])
        results['checkpoint_dir'] = model_dir
        results['checkpoint_size_mb'] = get_dir_size(model_dir) / (1024 * 1024)
    else:
        results['checkpoint_size_mb'] = "unknown"

    # 4. Load Data
    data_path = Path("data/raw/heart.csv")
    indices_path = Path("data/processed/dev_indices.json")
    if not data_path.exists() or not indices_path.exists():
        results['error'] = f"Data not found at {data_path} or {indices_path}"
        save_results(results)
        return
        
    df = pd.read_csv(data_path)
    with open(indices_path, "r") as f:
        dev_indices = json.load(f)
    
    df_dev = df.iloc[dev_indices]
    X = df_dev.drop(columns=['target']).values
    y = df_dev['target'].values
    
    results['dataset_shape'] = X.shape
    
    # Split: train on first 193, predict on rest (simulating one CV fold)
    train_size = 193
    X_train, y_train = X[:train_size], y[:train_size]
    X_test, y_test = X[train_size:], y[train_size:]
    
    # 5. Fit (which for ICL just stores the context)
    print("Fitting model (storing context)...")
    try:
        clf.fit(X_train, y_train)
    except Exception as e:
        results['error'] = f"Failed during fit: {str(e)}"
        save_results(results)
        return
        
    # 6. Predict / Inference
    print(f"Predicting on {len(X_test)} samples...")
    try:
        t0 = time.time()
        preds = clf.predict(X_test)
        results['inference_time_predict_sec'] = time.time() - t0
        
        t0 = time.time()
        probs = clf.predict_proba(X_test)
        results['inference_time_predict_proba_sec'] = time.time() - t0
        
        # Test repeated inference to see if context is re-embedded or cached
        t0 = time.time()
        _ = clf.predict_proba(X_test)
        results['inference_time_repeated_sec'] = time.time() - t0

        results['predictions_shape'] = preds.shape
        results['probabilities_shape'] = probs.shape
        results['sample_probabilities'] = probs[:5].tolist()
        results['sample_predictions'] = preds[:5].tolist()
        
    except Exception as e:
        results['error'] = f"Failed during prediction: {str(e)}"
        save_results(results)
        return

    # Track RAM/VRAM after inference
    results['ram_after_inference_mb'] = process.memory_info().rss / (1024 * 1024)
    if device == "cuda":
        results['vram_after_inference_mb'] = torch.cuda.memory_allocated(0) / (1024 * 1024)

    results['success'] = True
    save_results(results)
    print("Test completed successfully.")

def save_results(results):
    out_dir = Path("experiments/phase13")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "tabicl_feasibility.json", "w") as f:
        json.dump(results, f, indent=4)
        
if __name__ == "__main__":
    main()
