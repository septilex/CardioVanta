import pytest
from pydantic import ValidationError
from backend.app.schemas.predict import PredictRequest
from backend.app.main import app
from fastapi.testclient import TestClient
import json
from pathlib import Path

def test_valid_request_schema():
    data = {
        "age": 45.0,
        "sex": 1,
        "cp": 2,
        "trestbps": 120.0,
        "chol": 200.0,
        "fbs": 0,
        "restecg": 1,
        "thalach": 150.0,
        "exang": 0,
        "oldpeak": 1.5,
        "slope": 2,
        "ca": 0,
        "thal": 2
    }
    req = PredictRequest(**data)
    assert req.age == 45.0
    assert req.model_dump() == data

def test_missing_field_rejected():
    data = {
        "age": 45.0,
        "sex": 1,
        "cp": 2,
        "trestbps": 120.0,
        "chol": 200.0,
        "fbs": 0,
        "restecg": 1,
        "thalach": 150.0,
        "exang": 0,
        "oldpeak": 1.5,
        "slope": 2,
        "ca": 0
        # thal is missing
    }
    with pytest.raises(ValidationError):
        PredictRequest(**data)

def test_extra_field_rejected():
    data = {
        "age": 45.0,
        "sex": 1,
        "cp": 2,
        "trestbps": 120.0,
        "chol": 200.0,
        "fbs": 0,
        "restecg": 1,
        "thalach": 150.0,
        "exang": 0,
        "oldpeak": 1.5,
        "slope": 2,
        "ca": 0,
        "thal": 2,
        "extra_field": 123
    }
    with pytest.raises(ValidationError):
        PredictRequest(**data)

def test_binary_validation_rejected():
    base_data = {
        "age": 45.0, "sex": 1, "cp": 2, "trestbps": 120.0,
        "chol": 200.0, "fbs": 0, "restecg": 1, "thalach": 150.0,
        "exang": 0, "oldpeak": 1.5, "slope": 2, "ca": 0, "thal": 2
    }
    
    # Invalid sex
    bad_sex = base_data.copy()
    bad_sex["sex"] = 2
    with pytest.raises(ValidationError):
        PredictRequest(**bad_sex)
        
    # Invalid fbs
    bad_fbs = base_data.copy()
    bad_fbs["fbs"] = 3
    with pytest.raises(ValidationError):
        PredictRequest(**bad_fbs)
        
    # Invalid exang
    bad_exang = base_data.copy()
    bad_exang["exang"] = -1
    with pytest.raises(ValidationError):
        PredictRequest(**bad_exang)

def test_categorical_validation_rejected():
    base_data = {
        "age": 45.0, "sex": 1, "cp": 2, "trestbps": 120.0,
        "chol": 200.0, "fbs": 0, "restecg": 1, "thalach": 150.0,
        "exang": 0, "oldpeak": 1.5, "slope": 2, "ca": 0, "thal": 2
    }
    
    bad_cp = base_data.copy()
    bad_cp["cp"] = 4
    with pytest.raises(ValidationError):
        PredictRequest(**bad_cp)
        
    bad_restecg = base_data.copy()
    bad_restecg["restecg"] = 3
    with pytest.raises(ValidationError):
        PredictRequest(**bad_restecg)
        
    bad_slope = base_data.copy()
    bad_slope["slope"] = 3
    with pytest.raises(ValidationError):
        PredictRequest(**bad_slope)
        
    bad_ca = base_data.copy()
    bad_ca["ca"] = 5
    with pytest.raises(ValidationError):
        PredictRequest(**bad_ca)
        
    bad_thal = base_data.copy()
    bad_thal["thal"] = 4
    with pytest.raises(ValidationError):
        PredictRequest(**bad_thal)

def test_continuous_values_outside_range_accepted():
    # Outside observed development range but must be accepted by schema
    data = {
        "age": 150.0, # Way outside range
        "sex": 1,
        "cp": 2,
        "trestbps": 300.0,
        "chol": 1000.0,
        "fbs": 0,
        "restecg": 1,
        "thalach": 300.0,
        "exang": 0,
        "oldpeak": 10.0,
        "slope": 2,
        "ca": 0,
        "thal": 2
    }
    req = PredictRequest(**data)
    assert req.age == 150.0
    
def test_feature_order_schema_consistency():
    # Check that the runtime Pydantic schema matches the original feature_schema.json
    schema_path = Path(__file__).resolve().parent.parent.parent / "artifacts" / "model" / "feature_schema.json"
    with open(schema_path, "r") as f:
        packaged_schema = json.load(f)
        
    packaged_order = packaged_schema["feature_order"]
    pydantic_order = list(PredictRequest.model_fields.keys())
    
    assert pydantic_order == packaged_order

def test_health_endpoint_response():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok", "service": "CardioVanta"}
        assert "paths" not in str(data).lower()
