import pytest
import json
from pathlib import Path
from pydantic import ValidationError
from typing import get_args, Literal
from backend.app.schemas.predict import PredictRequest
from backend.app.core.config import settings
from backend.app.main import app
from fastapi.testclient import TestClient

def get_schema():
    schema_path = Path(settings.MODEL_DIR).parent.parent.parent / "configs" / "feature_schema.json"
    if not schema_path.exists():
        # Fallback for different test execution paths
        schema_path = Path(__file__).resolve().parent.parent.parent / "configs" / "feature_schema.json"
    with open(schema_path, "r") as f:
        return json.load(f)

def test_contract_artifacts_exist():
    # Verify required model artifacts exist
    model_dir = Path(settings.MODEL_DIR)
    assert (model_dir / "model.joblib").exists(), "model.joblib missing"
    assert (model_dir / "explanation_model.joblib").exists(), "explanation_model.joblib missing"
    assert (model_dir / "metadata.json").exists(), "metadata.json missing"
    assert (model_dir / "feature_schema.json").exists(), "feature_schema.json missing in artifacts"

def test_contract_metadata_references():
    model_dir = Path(settings.MODEL_DIR)
    with open(model_dir / "metadata.json", "r") as f:
        metadata = json.load(f)
    
    assert "model_version" in metadata
    assert "training_data_provenance" in metadata
    assert "feature_schema_version" in metadata

def test_contract_feature_schema_consistency():
    schema = get_schema()
    
    # Feature count exactly 13
    assert schema["feature_count"] == 13
    assert len(schema["features"]) == 13
    assert len(schema["feature_order"]) == 13
    
    # Check that PredictRequest matches schema allowed_values for categorical/binary
    pydantic_fields = PredictRequest.model_fields
    
    for feature in schema["features"]:
        f_name = feature["name"]
        assert f_name in pydantic_fields, f"{f_name} missing from PredictRequest"
        
        if feature["type"] in ["categorical", "binary"]:
            allowed = feature["allowed_values"]
            annotation = pydantic_fields[f_name].annotation
            
            # Extract literal arguments
            # Note: For optional or union types, might need more complex parsing, but here it's straight Literal
            literal_args = get_args(annotation)
            
            assert set(literal_args) == set(allowed), f"Mismatched options for {f_name}: schema {allowed}, pydantic {literal_args}"

def test_golden_input_deterministic_inference():
    # A fixed valid input (matches our frontend initialData)
    golden_input = {
        "age": 45.0,
        "sex": 1,
        "cp": 0,
        "trestbps": 120.0,
        "chol": 200.0,
        "fbs": 0,
        "restecg": 1,
        "thalach": 150.0,
        "exang": 0,
        "oldpeak": 1.0,
        "slope": 1,
        "ca": 0,
        "thal": 2
    }
    
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=golden_input)
        assert response.status_code == 200
        
        data = response.json()
        
        # 1. API response fields remain stable
        assert "prediction" in data
        assert "explanation" in data
        assert "development_range_warning" in data
        assert "metadata" in data
        
        # 2. Deterministic probability (it shouldn't change randomly)
        prob = data["prediction"]["probability"]
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0
        
        # We assert the probability is deterministic by comparing to itself if we run it twice
        response2 = client.post("/api/v1/predict", json=golden_input)
        assert prob == response2.json()["prediction"]["probability"]
        
        # 3. Explanation keys match authoritative raw feature names
        contributions = data["explanation"]["contributions"]
        schema = get_schema()
        for feature in schema["features"]:
            assert feature["name"] in contributions, f"Missing contribution for {feature['name']}"
        assert len(contributions) == 13

def test_contract_out_of_range_warning():
    # Golden input but age is 150
    bad_input = {
        "age": 150.0,
        "sex": 1,
        "cp": 0,
        "trestbps": 120.0,
        "chol": 200.0,
        "fbs": 0,
        "restecg": 1,
        "thalach": 150.0,
        "exang": 0,
        "oldpeak": 1.0,
        "slope": 1,
        "ca": 0,
        "thal": 2
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=bad_input)
        assert response.status_code == 200
        
        data = response.json()
        assert data["development_range_warning"]["outside_development_range"] is True
        assert "age" in data["development_range_warning"]["features"]

def test_contract_malformed_request_rejected():
    with TestClient(app) as client:
        bad_input = {
            "age": 45.0,
            # missing sex
            "cp": 999, # invalid category
            "trestbps": 120.0,
            "chol": 200.0,
            "fbs": 0,
            "restecg": 1,
            "thalach": 150.0,
            "exang": 0,
            "oldpeak": 1.0,
            "slope": 1,
            "ca": 0,
            "thal": 2
        }
        response = client.post("/api/v1/predict", json=bad_input)
        assert response.status_code == 422
