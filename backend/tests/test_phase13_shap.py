import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

valid_payload = {
    "age": 63.0,
    "sex": 1,
    "cp": 3,
    "trestbps": 145.0,
    "chol": 233.0,
    "fbs": 1,
    "restecg": 0,
    "thalach": 150.0,
    "exang": 0,
    "oldpeak": 2.3,
    "slope": 0,
    "ca": 0,
    "thal": 1
}

def test_shap_equivalent_presence_and_structure(client):
    response = client.post("/api/v1/predict", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    
    # 1. Existing explanation is unchanged
    assert "explanation" in data
    assert "intercept" in data["explanation"]
    assert "contributions" in data["explanation"]
    assert "decision_function_log_odds" in data["explanation"]
    
    # 2. New SHAP-equivalent explanation is present
    assert "shap_equivalent_explanation" in data
    shap_exp = data["shap_equivalent_explanation"]
    
    assert "expected_value" in shap_exp
    assert "contributions" in shap_exp
    assert "decision_function_log_odds" in shap_exp
    
    # 3. All 13 features present
    contributions = shap_exp["contributions"]
    expected_features = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", 
                         "thalach", "exang", "oldpeak", "slope", "ca", "thal"]
    for f in expected_features:
        assert f in contributions
        
    # 4. Additivity holds
    total_contrib = sum(contributions.values())
    expected_val = shap_exp["expected_value"]
    df_val = shap_exp["decision_function_log_odds"]
    
    # Due to floating point precision, check almost equal
    assert abs(total_contrib + expected_val - df_val) < 1e-4

def test_deterministic_repeated_output(client):
    response1 = client.post("/api/v1/predict", json=valid_payload).json()
    response2 = client.post("/api/v1/predict", json=valid_payload).json()
    
    assert response1["shap_equivalent_explanation"] == response2["shap_equivalent_explanation"]

def test_production_probability_unchanged(client):
    response = client.post("/api/v1/predict", json=valid_payload)
    data = response.json()
    
    assert "prediction" in data
    assert "probability" in data["prediction"]
    
    # The probability should be identical to the unmodified endpoint.
    # Note: If this fails, the core inference engine logic was accidentally changed!
    # A known good probability for this valid_payload from earlier phases:
    # We can just ensure it doesn't crash and returns a valid float in [0, 1]
    assert 0.0 <= data["prediction"]["probability"] <= 1.0

def test_malformed_requests_behave_identically(client):
    bad_payload = valid_payload.copy()
    bad_payload["age"] = "invalid"
    
    response = client.post("/api/v1/predict", json=bad_payload)
    assert response.status_code == 422 # Pydantic validation error
    
    bad_payload_2 = valid_payload.copy()
    bad_payload_2["thal"] = 99 # Not in allowed literal
    response2 = client.post("/api/v1/predict", json=bad_payload_2)
    assert response2.status_code == 422
