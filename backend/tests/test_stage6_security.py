import pytest
import math
import json
from fastapi.testclient import TestClient
from backend.app.main import app


valid_payload = {
    "age": 55.0,
    "sex": 1,
    "cp": 2,
    "trestbps": 140.0,
    "chol": 250.0,
    "fbs": 0,
    "restecg": 1,
    "thalach": 150.0,
    "exang": 0,
    "oldpeak": 2.0,
    "slope": 1,
    "ca": 0,
    "thal": 2
}

def test_valid_finite_values():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=valid_payload)
        assert response.status_code == 200

@pytest.mark.parametrize("invalid_val", ["NaN", "Infinity", "-Infinity"])
def test_reject_non_finite_inputs(invalid_val):
    with TestClient(app) as client:
        for field in ["age", "trestbps", "chol", "thalach", "oldpeak"]:
            payload = valid_payload.copy()
            json_payload = json.dumps(payload).replace(str(payload[field]), invalid_val)
            response = client.post("/api/v1/predict", content=json_payload, headers={"Content-Type": "application/json"})
            assert response.status_code == 422
        
def test_missing_fields():
    with TestClient(app) as client:
        payload = valid_payload.copy()
        del payload["age"]
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_extra_fields():
    with TestClient(app) as client:
        payload = valid_payload.copy()
        payload["extra_field_attack"] = 123
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_null_values():
    with TestClient(app) as client:
        payload = valid_payload.copy()
        payload["age"] = None
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_empty_string():
    with TestClient(app) as client:
        payload = valid_payload.copy()
        payload["age"] = ""
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_wrong_type():
    with TestClient(app) as client:
        payload = valid_payload.copy()
        payload["age"] = "not_a_number"
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_invalid_categorical_values():
    with TestClient(app) as client:
        payload = valid_payload.copy()
        payload["sex"] = 3  # Valid is 0 or 1
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_extreme_finite_continuous_values():
    with TestClient(app) as client:
        # Should be 200 but out of range
        payload = valid_payload.copy()
        payload["age"] = 9999999999.0
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 200
        assert response.json()["development_range_warning"]["outside_development_range"] is True

def test_malformed_json():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/predict",
            content="{ malformed json: true,",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

def test_validation_logging_sanitized(caplog):
    with TestClient(app) as client:
        import logging
        # Attempt to trigger validation error with a sensitive value
        payload = valid_payload.copy()
        sensitive_value = 999999.555
        payload["age"] = sensitive_value
        payload["sex"] = 99 # trigger validation error
        
        with caplog.at_level(logging.ERROR):
            response = client.post("/api/v1/predict", json=payload)
            
        assert response.status_code == 422
        
        # Check that sensitive_value is NOT in the logs
        for record in caplog.records:
            assert str(sensitive_value) not in record.message
            # If extra dictionary has errors, verify 'input' was stripped
            if hasattr(record, "errors"):
                for err in record.errors:
                    assert "input" not in err
        
        # Also verify it's not in the response
        assert str(sensitive_value) not in response.text
