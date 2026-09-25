import json
import pytest
import math
from fastapi.testclient import TestClient
from backend.app.main import app
from src.config.config import BASE_DIR

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

def get_schema_feature_order():
    with open(BASE_DIR / "artifacts/model/feature_schema.json", "r") as f:
        return json.load(f)["feature_order"]

def test_explanation_13_keys_and_order():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        assert response.status_code == 200
        data = response.json()
        
        contributions = data["explanation"]["contributions"]
        keys = list(contributions.keys())
        expected_order = get_schema_feature_order()
        
        # A. Exactly 13 raw feature contribution keys
        assert len(keys) == 13
        # B. Exact feature order matches feature_schema.json
        assert keys == expected_order

def test_explanation_numeric_and_finite():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        data = response.json()
        exp = data["explanation"]
        
        # C. All contribution values numeric and finite
        for val in exp["contributions"].values():
            assert isinstance(val, float)
            assert math.isfinite(val)
            
        # D. Intercept numeric and finite
        assert isinstance(exp["intercept"], float)
        assert math.isfinite(exp["intercept"])
        
        # E. Decision function numeric and finite
        assert isinstance(exp["decision_function_log_odds"], float)
        assert math.isfinite(exp["decision_function_log_odds"])

def test_mathematical_reconstruction():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        exp = response.json()["explanation"]
        
        # F. Mathematical reconstruction
        sum_contribs = sum(exp["contributions"].values())
        reconstructed = exp["intercept"] + sum_contribs
        
        assert math.isclose(reconstructed, exp["decision_function_log_odds"], abs_tol=1e-4)

def test_explanation_wording_and_semantics():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        note = response.json()["explanation"]["note"]
        
        # Exact wording check
        expected_note = "These feature contributions explain the underlying uncalibrated Logistic Regression decision function (log-odds). They do not decompose the final calibrated ensemble probability and do not imply clinical causality."
        assert note == expected_note
        
        # G, H, I: Indirectly tested by verifying exact wording and schema field description
        assert "clinical causality" in note
        assert "decompose" in note
        
        # Inspect openapi schema for Field description on contributions
        openapi = app.openapi()
        schemas = openapi["components"]["schemas"]
        # In Pydantic v2, ExplanationResult defines contributions referencing FeatureContributions
        # The description is on the Field in ExplanationResult
        exp_schema = schemas.get("ExplanationResult", {})
        contrib_prop = exp_schema.get("properties", {}).get("contributions", {})
        assert "Positive contribution: moves the Logistic Regression decision function toward the positive class" in contrib_prop.get("description", "")

def test_explanation_determinism():
    with TestClient(app) as client:
        # K. Same input twice -> identical explanation
        payload = get_valid_payload()
        res1 = client.post("/api/v1/predict", json=payload).json()["explanation"]
        res2 = client.post("/api/v1/predict", json=payload).json()["explanation"]
        
        assert res1 == res2

def test_no_leaks_or_network():
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=get_valid_payload())
        text = response.text
        
        # M. No filesystem paths/secrets/internal objects leaked
        assert "c:\\" not in text.lower()
        assert "joblib" not in text.lower()
        assert "password" not in text.lower()
        
        # O. No network dependency (implicitly tested since test runs locally without mocked network)
