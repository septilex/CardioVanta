import json
import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import sys
import copy

from src.config.config import BASE_DIR, RAW_DATA_PATH
from src.inference.predict import InferenceEngine

# Configuration
MIN_OBSERVATIONS = 50
EFFECT_SIZE_THRESHOLD = 0.2
P_VALUE_THRESHOLD = 0.05
NUM_PERMUTATIONS = 10000
RANDOM_SEED = 42

def load_baseline_probabilities():
    """
    Dynamically generates the 242 development set prediction probabilities
    as the frozen reference baseline.
    """
    engine = InferenceEngine()
    
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_indices = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace("\ufeff", "") for col in df.columns]
    
    dev_df = df.iloc[dev_indices].copy()
    
    baseline_probs = []
    
    for _, row in dev_df.iterrows():
        # Convert row to dict
        raw_input = row.to_dict()
        # Drop target if present
        target_col = engine.schema["target_column"]
        if target_col in raw_input:
            del raw_input[target_col]
            
        res = engine.predict(raw_input)
        baseline_probs.append(res["probability"])
        
    return np.array(baseline_probs)

def parse_production_logs(log_path, expected_package_version, expected_model_type):
    """
    Parses a JSONLines file containing Phase 15A telemetry.
    Returns array of probabilities, array of boundary violation flags, and rejection stats.
    """
    probs = []
    violations = []
    rejections = {
        "mismatched_package_version": 0,
        "mismatched_model_type": 0,
        "invalid_json": 0
    }
    
    with open(log_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                rejections["invalid_json"] += 1
                continue
                
            if record.get("event_type") == "prediction_event":
                pkg_ver = record.get("package_version")
                mod_type = record.get("model_type")
                
                if pkg_ver != expected_package_version:
                    rejections["mismatched_package_version"] += 1
                    continue
                    
                if mod_type != expected_model_type:
                    rejections["mismatched_model_type"] += 1
                    continue
                    
                probs.append(record["prediction_probability"])
                violations.append(record.get("outside_development_range", False))
                
    return np.array(probs), np.array(violations), rejections

def exact_ks_statistic(data1, data2):
    """
    Computes the KS D-statistic.
    """
    from scipy.stats import ks_2samp
    return ks_2samp(data1, data2).statistic

def calculate_ks_permutation(baseline_probs, prod_probs, num_permutations=NUM_PERMUTATIONS, seed=RANDOM_SEED):
    """
    Permutation-based Monte Carlo p-value estimation for the KS D-statistic.
    Explicitly handles ties and small-sample uncertainty.
    """
    rng = np.random.default_rng(seed)
    
    d_obs = exact_ks_statistic(baseline_probs, prod_probs)
    
    combined = np.concatenate([baseline_probs, prod_probs])
    n_baseline = len(baseline_probs)
    
    count_greater_equal = 0
    
    for _ in range(num_permutations):
        permuted = rng.permutation(combined)
        pseudo_base = permuted[:n_baseline]
        pseudo_prod = permuted[n_baseline:]
        
        d_perm = exact_ks_statistic(pseudo_base, pseudo_prod)
        if d_perm >= d_obs:
            count_greater_equal += 1
            
    # Finite-sample p-value calculation to avoid p=0
    p_value = (count_greater_equal + 1) / (num_permutations + 1)
    
    return d_obs, p_value

def analyze_drift(log_path):
    """
    Main drift analysis entry point.
    """
    engine = InferenceEngine()
    expected_package_version = engine.metadata.get("package_version")
    expected_model_type = engine.metadata.get("model_configuration", {}).get("algorithm")
    
    baseline_probs = load_baseline_probabilities()
    prod_probs, violations, rejections = parse_production_logs(
        log_path, 
        expected_package_version=expected_package_version, 
        expected_model_type=expected_model_type
    )
    
    n_prod = len(prod_probs)
    
    report = {
        "eligibility": {
            "n_observations": n_prod,
            "min_required": MIN_OBSERVATIONS,
            "eligible": n_prod >= MIN_OBSERVATIONS,
            "rejections": rejections
        },
        "support_boundary": {
            "violations": int(np.sum(violations)),
            "violation_rate": float(np.mean(violations)) if n_prod > 0 else 0.0
        },
        "statistical_analysis": None,
        "drift_detected": False,
        "disclaimer": "True concept drift and real performance degradation cannot be measured because CardioVanta does not collect post-prediction ground-truth outcomes. Statistical drift ≠ clinical deterioration."
    }
    
    if not report["eligibility"]["eligible"]:
        report["status"] = "insufficient_evidence"
        return report
        
    d_obs, p_value = calculate_ks_permutation(baseline_probs, prod_probs)
    
    is_significant = p_value < P_VALUE_THRESHOLD
    has_effect_size = d_obs >= EFFECT_SIZE_THRESHOLD
    
    drift_detected = is_significant and has_effect_size
    
    report["statistical_analysis"] = {
        "ks_d_statistic": float(d_obs),
        "permutation_p_value": float(p_value),
        "p_value_threshold": P_VALUE_THRESHOLD,
        "effect_size_threshold": EFFECT_SIZE_THRESHOLD,
        "is_significant": bool(is_significant),
        "has_meaningful_effect_size": bool(has_effect_size),
        "note": f"D >= {EFFECT_SIZE_THRESHOLD} is an ENGINEERING MONITORING POLICY threshold only, not statistically or clinically validated."
    }
    
    report["drift_detected"] = bool(drift_detected)
    report["status"] = "drift_detected" if drift_detected else "no_drift"
    
    return report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python detect_drift.py <path_to_telemetry_jsonl>")
        sys.exit(1)
        
    log_file = sys.argv[1]
    result = analyze_drift(log_file)
    print(json.dumps(result, indent=2))
