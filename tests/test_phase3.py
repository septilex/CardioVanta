import json
import pandas as pd
import numpy as np
import ast
from pathlib import Path
from src.config.config import BASE_DIR
from src.experiment.phase3 import map_transformed_features

def test_temperature_scaling_detection():
    from sklearn.dummy import DummyClassifier
    from sklearn.calibration import CalibratedClassifierCV
    
    runtime_supported = False
    try:
        clf = CalibratedClassifierCV(estimator=DummyClassifier(strategy="prior"), method='temperature', cv=2)
        clf.fit([[0], [1], [0], [1]], np.array([0, 1, 0, 1]))
        runtime_supported = True
    except Exception:
        runtime_supported = False
        
    cal_file = BASE_DIR / "reports" / "phase3_calibration_results.json"
    with open(cal_file, "r") as f:
        data = json.load(f)
        
    report_supported = data["temperature_scaling_evaluated"]
    assert runtime_supported == report_supported, f"Runtime temp scaling: {runtime_supported}, Report: {report_supported}"

def test_calibration_schema():
    cal_file = BASE_DIR / "reports" / "phase3_calibration_results.json"
    with open(cal_file, "r") as f:
        data = json.load(f)
        assert "base_model" in data
        assert "selected_method" in data
        assert "selection_rule" in data
        assert data["selected_method"] in [r["method"] for r in data["results"]]
        
        # Verify Average Precision terminology is used
        for res in data["results"]:
            assert "avg_precision_mean" in res
            assert "pr_auc" not in res

def test_feature_mapping_logic():
    orig = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"]
    
    # Valid mapping
    transformed = [
        "num__age", "num__trestbps", "num__chol", "num__thalach", "num__oldpeak",
        "cat__sex_1", "cat__cp_1", "cat__cp_2", "cat__cp_3", "cat__fbs_1", 
        "cat__restecg_1", "cat__restecg_2", "cat__exang_1", "cat__slope_1", 
        "cat__slope_2", "cat__ca_1", "cat__ca_2", "cat__ca_3", "cat__ca_4",
        "cat__thal_1", "cat__thal_2", "cat__thal_3"
    ]
    mapping = map_transformed_features(transformed, orig)
    
    # Verify properties
    assert len(mapping) == len(transformed), "Every transformed feature must be mapped exactly once"
    assert set(mapping.values()) == set(orig), "All raw features must be present"
    assert len(set(mapping.values())) == 13, "Exactly 13 unique raw features must exist"
    
    assert mapping["num__age"] == "age" # Continuous
    assert mapping["cat__cp_2"] == "cp" # One-hot categorical
    assert mapping["num__thalach"] == "thalach" # Check overlapping substring edge-case (thal vs thalach)
    assert mapping["cat__thal_1"] == "thal"
    
    # Invalid test (unmapped)
    try:
        map_transformed_features(["num__age", "cat__unknown_1"], orig)
        assert False, "Should have raised ValueError for unmapped feature"
    except ValueError:
        pass
        
    # Invalid test (missing raw features)
    try:
        map_transformed_features(["num__age"], orig)
        assert False, "Should have raised ValueError for missing raw features"
    except ValueError:
        pass

def test_local_explainability_mathematics_and_schema():
    loc_file = BASE_DIR / "reports" / "phase3_local_examples.json"
    with open(loc_file, "r") as f:
        data = json.load(f)
        assert "Base Logistic Regression" in data.get("method", "")
        
        note = data.get("note", "")
        assert "do not decompose the calibrated ensemble probability" in note.lower()
        
        examples = data.get("examples", [])
        for ex in examples:
            assert "base_logistic_regression_probability" in ex
            assert "calibrated_final_probability" in ex
            assert "explanation_target" in ex
            assert "Base Logistic Regression logit contribution" in ex["explanation_target"]
            
            # Check bounds
            assert 0 <= ex["base_logistic_regression_probability"] <= 1
            assert 0 <= ex["calibrated_final_probability"] <= 1
            
            # Check math reconstruction within floating point tolerance
            assert np.isclose(ex["reconstructed_logit"], ex["actual_logit"])
            assert ex["all_features_represented"] == True
            
            # Check directions
            for pos in ex["top_positive_contributors"]:
                assert pos["direction"] == "positive"
                assert pos["contribution"] > 0
            for neg in ex["top_negative_contributors"]:
                assert neg["direction"] == "negative"
                assert neg["contribution"] < 0

def test_no_test_set_construction_in_phase3():
    # Verify that get_train_test_split and StratifiedShuffleSplit are NOT used for generating full split
    phase3_path = BASE_DIR / "src" / "experiment" / "phase3.py"
    with open(phase3_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    tree = ast.parse(content)
    
    called_get_train_test_split = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == "get_train_test_split":
                    called_get_train_test_split = True
    
    assert not called_get_train_test_split, "get_train_test_split was called in Phase 3! Test set was constructed!"
    assert "dev_indices.json" in content, "Must use the frozen development split artifact!"
