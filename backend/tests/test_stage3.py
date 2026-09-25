import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

def get_valid_payload():
    return {
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

def test_valid_request():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "probability" in data["prediction"]
        
def test_probability_constraints():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        assert response.status_code == 200
        prob = response.json()["prediction"]["probability"]
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

def test_no_threshold():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        assert response.status_code == 200
        pred = response.json()["prediction"]
        assert pred["threshold_applied"] is None
        assert pred["class"] is None
        assert "no_validated_production_threshold_configured" in pred["threshold_status"]

def test_explicit_threshold():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict?threshold=0.5", json=get_valid_payload())
        assert response.status_code == 200
        pred = response.json()["prediction"]
        assert pred["threshold_applied"] == 0.5
        assert pred["class"] in [0, 1]
        assert "mathematical_model_operating_point" in pred["threshold_status"]

def test_invalid_thresholds():
    with TestClient(app) as client:
        res1 = client.post("/api/v1/predict?threshold=-0.1", json=get_valid_payload())
        assert res1.status_code == 422
        
        res2 = client.post("/api/v1/predict?threshold=1.5", json=get_valid_payload())
        assert res2.status_code == 422
        
        res3 = client.post("/api/v1/predict?threshold=abc", json=get_valid_payload())
        assert res3.status_code == 422

def test_missing_feature():
    with TestClient(app) as client:
        payload = get_valid_payload()
        del payload["age"]
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_extra_feature():
    with TestClient(app) as client:
        payload = get_valid_payload()
        payload["extra_field"] = 123
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_invalid_binary_values():
    with TestClient(app) as client:
        payload = get_valid_payload()
        payload["sex"] = 2
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_invalid_categorical_values():
    with TestClient(app) as client:
        payload = get_valid_payload()
        payload["cp"] = 4
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422

def test_continuous_outside_development_range():
    with TestClient(app) as client:
        payload = get_valid_payload()
        payload["chol"] = 1000.0 # Way outside
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        warn = data["development_range_warning"]
        assert warn["outside_development_range"] is True
        assert "chol" in warn["features"]
        assert warn["note"] is not None

def test_deterministic_inference():
    with TestClient(app) as client:
        payload = get_valid_payload()
        res1 = client.post("/api/v1/predict", json=payload).json()
        res2 = client.post("/api/v1/predict", json=payload).json()
        
        assert res1["prediction"]["probability"] == res2["prediction"]["probability"]
        assert res1["explanation"] == res2["explanation"]

def test_explanation_structure():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        assert response.status_code == 200
        exp = response.json()["explanation"]
        
        assert len(exp["contributions"]) == 13
        for k, v in exp["contributions"].items():
            assert isinstance(v, float)
        assert isinstance(exp["decision_function_log_odds"], float)
        assert isinstance(exp["intercept"], float)
        assert "calibrated ensemble probability" in exp["note"]

def test_no_secrets_leaked():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        text = response.text.lower()
        assert "c:\\" not in text
        assert "home/" not in text
        assert "password" not in text
        assert "api_key" not in text
        
        # Test 500 error doesn't leak stack trace
        # Mock InferenceEngine to raise Exception
        original = app.state.inference_engine.predict
        def mock_predict(*args, **kwargs):
            raise RuntimeError("Secret internal failure")
        app.state.inference_engine.predict = mock_predict
        
        err_res = client.post("/api/v1/predict", json=get_valid_payload())
        assert err_res.status_code == 500
        assert err_res.json()["detail"] == "Internal inference failure"
        
        app.state.inference_engine.predict = original

def test_metadata_model_type():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        assert response.status_code == 200
        metadata = response.json()["metadata"]
        assert metadata["model_type"] == "Logistic Regression"

def test_string_coercion():
    with TestClient(app) as client:
        # Pydantic coerces valid string floats to float, which is acceptable.
        payload = get_valid_payload()
        payload["age"] = "45"
        res1 = client.post("/api/v1/predict", json=payload)
        assert res1.status_code == 200
        
        # Malformed strings should be rejected
        payload["age"] = "abc"
        res2 = client.post("/api/v1/predict", json=payload)
        assert res2.status_code == 422
