import pytest
import json
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

valid_payload = {
    "age": 60,
    "sex": 1,
    "cp": 3,
    "trestbps": 145,
    "chol": 233,
    "fbs": 1,
    "restecg": 0,
    "thalach": 150,
    "exang": 0,
    "oldpeak": 2.3,
    "slope": 0,
    "ca": 0,
    "thal": 1
}

from unittest.mock import patch

def test_prediction_event_schema(caplog):
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=valid_payload)
        assert response.status_code == 200
        
        event = None
        for record in caplog.records:
            if getattr(record, "event_type", None) == "prediction_event":
                event = record
                break
                
        assert event is not None, "prediction_event log not found"
        assert hasattr(event, "request_id")
        assert event.endpoint == "/api/v1/predict"
        assert event.status_code == 200
        assert hasattr(event, "latency_ms")
        assert event.latency_ms > 0
        assert hasattr(event, "package_version")
        assert hasattr(event, "model_type")
        assert hasattr(event, "calibration_method")
        assert hasattr(event, "prediction_probability")
        assert hasattr(event, "threshold_status")
        assert hasattr(event, "outside_development_range")
        assert hasattr(event, "out_of_range_features")
        
        assert not hasattr(event, "age")
        assert not hasattr(event, "chol")
        assert not hasattr(event, "trestbps")

def test_validation_error_logging(caplog):
    invalid_payload = valid_payload.copy()
    invalid_payload["age"] = "not_a_number" # Invalid age type
    
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=invalid_payload)
        assert response.status_code == 422
        
        event = None
        for record in caplog.records:
            if getattr(record, "status_code", None) == 422:
                event = record
                break
                
        assert event is not None, "422 validation error log not found"
        assert hasattr(event, "request_id")
        assert hasattr(event, "errors")
        assert event.endpoint == "/api/v1/predict"

def test_telemetry_graceful_degradation():
    with patch("backend.app.api.endpoints.predict.logger.info", side_effect=Exception("Simulated logging failure")):
        with TestClient(app) as client:
            response = client.post("/api/v1/predict", json=valid_payload)
            assert response.status_code == 200
            assert "prediction" in response.json()
