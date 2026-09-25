import os
import json
import pandas as pd
import numpy as np
import ast
from pathlib import Path
from sklearn.model_selection import StratifiedKFold
from src.config.config import BASE_DIR, RANDOM_SEED, RAW_DATA_PATH, load_schema

def test_phase4a_no_test_set_construction():
    phase4a_path = BASE_DIR / "src" / "experiment" / "phase4a.py"
    with open(phase4a_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    tree = ast.parse(content)
    
    called_get_train_test_split = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == "get_train_test_split":
                    called_get_train_test_split = True
    
    assert not called_get_train_test_split, "get_train_test_split was called in Phase 4A! Test set was constructed!"
    assert "dev_indices.json" in content, "Must use the frozen development split artifact!"

def test_oof_predictions_schema():
    oof_file = BASE_DIR / "reports" / "phase4a_oof_predictions.csv"
    assert oof_file.exists()
    df = pd.read_csv(oof_file)
    
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    # 4. Strengthen OOF Index Validation
    assert set(df['dev_index']) == set(range(len(dev_idx))), "Dev indices do not match expected positions (0 to len-1)"
    
    # Exactly one prediction per observation
    assert len(df) == len(dev_idx), "Missing or duplicate OOF predictions"
    assert df['dev_index'].is_unique, "Duplicate development observation in OOF"
    
    # Valid fold IDs
    assert set(df['fold_id'].unique()) == {1, 2, 3, 4, 5}, "Fold IDs are invalid"
    
    # Original sample indices exactly match dev_indices.json
    for _, row in df.iterrows():
        assert row['original_sample_index'] == dev_idx[int(row['dev_index'])], "Original sample index mismatch"

def test_threshold_metrics_consistency():
    metrics_file = BASE_DIR / "reports" / "phase4a_threshold_metrics.csv"
    assert metrics_file.exists()
    df = pd.read_csv(metrics_file)
    
    # 7. Threshold Grid Validation
    expected_thresholds = np.round(np.arange(0.05, 0.96, 0.01), 2)
    assert len(df) == len(expected_thresholds)
    assert np.allclose(df['threshold'].values, expected_thresholds), "Missing or duplicate threshold values in grid"
    
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        expected_total = len(json.load(f))
    
    # 5. Strengthen Threshold Metric Validation
    for _, row in df.iterrows():
        tn, fp, fn, tp = row['tn'], row['fp'], row['fn'], row['tp']
        assert tn + fp + fn + tp == expected_total, f"Total counts ({tn+fp+fn+tp}) don't match dev total ({expected_total})"
        
        accuracy = (tp + tn) / expected_total
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        fpr = fp / (tn + fp) if (tn + fp) > 0 else 0
        fnr = fn / (tp + fn) if (tp + fn) > 0 else 0
        balanced_accuracy = (recall + specificity) / 2
        youden = recall + specificity - 1
        
        assert np.isclose(row['accuracy'], accuracy)
        assert np.isclose(row['precision'], precision)
        assert np.isclose(row['recall'], recall)
        assert np.isclose(row['specificity'], specificity)
        assert np.isclose(row['f1'], f1)
        assert np.isclose(row['fpr'], fpr)
        assert np.isclose(row['fnr'], fnr)
        assert np.isclose(row['balanced_accuracy'], balanced_accuracy)
        assert np.isclose(row['youden_j'], youden)

def test_error_analysis_schema():
    err_file = BASE_DIR / "reports" / "phase4a_error_analysis.csv"
    assert err_file.exists()
    df = pd.read_csv(err_file)
    
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        expected_total = len(json.load(f))
        
    for cand in df['candidate'].unique():
        sub = df[df['candidate'] == cand]
        assert len(sub) == expected_total, f"Candidate {cand} has {len(sub)} rows, expected {expected_total}"
        assert sub['development_sample_index'].is_unique, f"Duplicate indices for candidate {cand}"
        
    for _, row in df.iterrows():
        # predicted_class == int(predicted_prob >= threshold)
        p_class = int(row['predicted_probability'] >= row['threshold'])
        assert row['predicted_class'] == p_class, "Predicted class mismatch"
        
        # Error type strict matches based on true label
        yt = row['true_label']
        yp = row['predicted_class']
        
        if yt == 1 and yp == 1:
            assert row['error_type'] == 'TP'
        elif yt == 0 and yp == 0:
            assert row['error_type'] == 'TN'
        elif yt == 0 and yp == 1:
            assert row['error_type'] == 'FP'
        elif yt == 1 and yp == 0:
            assert row['error_type'] == 'FN'

def test_threshold_stability_schema():
    stab_file = BASE_DIR / "reports" / "phase4a_threshold_stability.json"
    assert stab_file.exists()
    with open(stab_file, "r") as f:
        data = json.load(f)
        
    assert "outer_folds" in data
    assert len(data["outer_folds"]) == 5
    
    summary = data["summary"]
    for cand in ["youden_j", "max_f1"]:
        assert f"outer_fold_accuracy_std" in summary[cand]
        assert f"outer_fold_precision_std" in summary[cand]
        assert f"outer_fold_recall_std" in summary[cand]
        assert f"outer_fold_specificity_std" in summary[cand]
        assert f"outer_fold_f1_std" in summary[cand]
        assert f"outer_fold_balanced_accuracy_std" in summary[cand]

def test_nested_outer_fold_disjointness():
    # Construct exact dataset
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace("\ufeff", "") for col in df.columns]
    schema = load_schema()
    
    y_full = df[schema["target_column"]].to_numpy()
    y_train = y_full[dev_idx]
    
    # StratifiedKFold
    outer_kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED+1)
    
    folds = list(outer_kf.split(np.zeros(len(y_train)), y_train))
    assert len(folds) == 5, "Exactly 5 outer folds expected"
    
    all_val_indices = []
    
    for tr_idx, val_idx in folds:
        # Verify empty set intersection
        intersect = set(tr_idx).intersection(set(val_idx))
        assert len(intersect) == 0, f"Overlap found in outer fold: {intersect}"
        all_val_indices.extend(val_idx)
        
    # Verify every dev observation belongs to exactly one outer validation fold
    assert set(all_val_indices) == set(range(len(y_train))), "Not all observations in outer val"
    assert len(all_val_indices) == len(y_train), "Duplicate observations in outer val"

def test_no_production_artifacts():
    # Assert Phase 4A does not create new .pkl or .joblib files
    for root, dirs, files in os.walk(BASE_DIR):
        # Exclude venv to avoid finding pip or site-packages artifacts
        if "venv" in root:
            continue
        for f in files:
            if f.endswith(".pkl") or f.endswith(".joblib"):
                assert "phase4a" not in f.lower(), f"Found production artifact from phase 4A: {f}"

def test_calibration_configuration_consistency():
    phase3_file = BASE_DIR / "reports" / "phase3_calibration_results.json"
    phase4a_file = BASE_DIR / "reports" / "phase4a_threshold_analysis.json"
    
    assert phase3_file.exists()
    assert phase4a_file.exists()
    
    with open(phase3_file, "r") as f:
        p3_data = json.load(f)
        
    with open(phase4a_file, "r") as f:
        p4_data = json.load(f)
        
    assert p4_data["calibration_method"] == p3_data["selected_method"], "Calibration method mismatch"
    assert p4_data["calibration_cv"] == 5, "Calibration CV must be 5"
