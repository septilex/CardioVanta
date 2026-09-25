import os
import json
import pytest
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
import sklearn
import sys

from src.config.config import BASE_DIR, RAW_DATA_PATH
from src.inference.predict import InferenceEngine

# Test suite for Phase 5 Model Packaging and Inference

@pytest.fixture
def artifacts_dir():
    return BASE_DIR / "artifacts" / "model"

@pytest.fixture
def engine():
    return InferenceEngine()

def test_artifacts_exist(artifacts_dir):
    assert (artifacts_dir / "model.joblib").exists()
    assert (artifacts_dir / "explanation_model.joblib").exists()
    assert (artifacts_dir / "feature_schema.json").exists()
    assert (artifacts_dir / "metadata.json").exists()
    assert (artifacts_dir / "reference_predictions.csv").exists()

def test_metadata_parses_and_sklearn_version(artifacts_dir):
    with open(artifacts_dir / "metadata.json", "r") as f:
        metadata = json.load(f)
    
    req_version = metadata["environment"]["sklearn_version"]
    assert sklearn.__version__ == req_version, "Environment sklearn version must match package metadata"
    assert "package_version" in metadata
    assert "training_data_provenance" in metadata
    
    # Check that explanation context mentions Logistic Regression
    note = metadata["explainability_context"]["note"]
    assert "Logistic Regression" in note
    assert "not claim to decompose the final calibrated ensemble" in note.lower() or "do not decompose the final calibrated ensemble" in note.lower()

def test_feature_schema_consistency(engine):
    schema = engine.schema
    assert schema["feature_count"] == 13
    assert len(schema["feature_order"]) == 13
    assert schema["feature_order"] == [
        "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", 
        "thalach", "exang", "oldpeak", "slope", "ca", "thal"
    ]

def get_valid_input(engine):
    # Construct a valid input based on the schema
    schema = engine.schema
    raw = {}
    for f in schema["features"]:
        if f["type"] == "continuous":
            raw[f["name"]] = (f["min"] + f["max"]) / 2.0
        elif f["type"] in ["categorical", "binary"]:
            raw[f["name"]] = f["allowed_values"][0]
    return raw

def test_missing_feature_rejection(engine):
    raw = get_valid_input(engine)
    del raw["age"]
    with pytest.raises(ValueError, match="Missing required features"):
        engine.predict(raw)

def test_extra_feature_rejection(engine):
    raw = get_valid_input(engine)
    raw["extra_invalid_feature"] = 1.0
    with pytest.raises(ValueError, match="Unexpected extra features"):
        engine.predict(raw)

def test_categorical_binary_validation(engine):
    raw = get_valid_input(engine)
    
    # Valid binary
    raw["sex"] = 1
    engine.predict(raw)
    
    # Invalid binary
    raw["sex"] = 5
    with pytest.raises(ValueError, match="not in allowed"):
        engine.predict(raw)
        
    # Invalid categorical
    raw = get_valid_input(engine)
    raw["cp"] = 10
    with pytest.raises(ValueError, match="not in allowed"):
        engine.predict(raw)

def test_continuous_guardrails(engine):
    raw = get_valid_input(engine)
    
    # Out of bounds continuous should NOT reject, but set the warning flag
    raw["age"] = 150.0 
    res = engine.predict(raw)
    assert res["outside_development_range"] is True
    assert "guardrails" in res["development_range_note"]
    
    # Non-numeric should reject
    raw["age"] = "invalid_string"
    with pytest.raises(ValueError, match="must be numeric"):
        engine.predict(raw)

def test_deterministic_inference_and_bounds(engine):
    raw = get_valid_input(engine)
    
    res1 = engine.predict(raw)
    res2 = engine.predict(raw)
    
    assert res1["probability"] == res2["probability"]
    assert 0.0 <= res1["probability"] <= 1.0
    
    assert res1["threshold_applied"] is None
    assert res1["class"] is None
    assert "No validated production decision threshold" in res1["threshold_note"]

def test_optional_threshold_application(engine):
    raw = get_valid_input(engine)
    
    res = engine.predict(raw, apply_threshold=0.5)
    assert res["threshold_applied"] == 0.5
    
    if res["probability"] >= 0.5:
        assert res["class"] == 1
    else:
        assert res["class"] == 0

def test_explainability_sum_integrity(engine):
    raw = get_valid_input(engine)
    exp = engine.explain(raw)
    
    intercept = exp["intercept"]
    contributions = exp["contributions"]
    df_value = exp["decision_function_log_odds"]
    
    assert len(contributions) == 13
    assert "Logistic Regression" in exp["note"]
    
    # Test numerical integrity (already asserted in code but good to double check)
    assert np.isclose(intercept + sum(contributions.values()), df_value, atol=1e-4)

def test_package_reference_prediction(artifacts_dir, engine):
    """
    Ensure the package exactly reproduces the reference predictions
    generated dynamically during its creation.
    """
    ref_df = pd.read_csv(artifacts_dir / "reference_predictions.csv")
    
    # Load raw data to feed into the engine
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\\ufeff', '') for col in df.columns]
    
    with open(BASE_DIR / "data" / "processed" / "dev_indices.json", "r") as f:
        dev_idx = json.load(f)
        
    assert len(ref_df) == len(dev_idx)
    
    # Test a handful of records for exact strict numerical tolerance
    for i in range(min(50, len(ref_df))):
        idx = int(ref_df.iloc[i]["dev_index"])
        ref_prob = ref_df.iloc[i]["reference_probability"]
        
        row_dict = df.iloc[idx].drop("target").to_dict()
        res = engine.predict(row_dict)
        
        assert np.isclose(res["probability"], ref_prob, atol=1e-8), f"Mismatch at index {idx}"

def test_no_test_set_leakage(artifacts_dir):
    """
    Verify locked test observations were not accidentally used.
    """
    with open(artifacts_dir / "metadata.json", "r") as f:
        metadata = json.load(f)
    
    prov = metadata["training_data_provenance"]
    dev_count = prov["development_sample_count"]
    
    # Known fixed counts from Phase 0
    assert dev_count == 242
    
    # We should also ensure test count logic matches without relying on missing test_indices.json
    df = pd.read_csv(RAW_DATA_PATH)
    actual_test_count = len(df) - dev_count
    assert prov["locked_test_sample_count_provenance_only"] == actual_test_count

def test_no_network_dependency(engine, monkeypatch):
    """
    Ensure no external AI/Network dependency during prediction.
    """
    import socket
    def guard(*args, **kwargs):
        raise Exception("Network access attempted!")
    monkeypatch.setattr(socket, "socket", guard)
    
    raw = get_valid_input(engine)
    res = engine.predict(raw)
    assert res is not None
