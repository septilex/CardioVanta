import pytest
import json
import sklearn
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.model_loader import ModelLoader
from fastapi.testclient import TestClient
from backend.app.main import app

def test_startup_validation_success():
    # Verify that the ModelLoader can successfully load the artifacts from the real project directory
    loader = ModelLoader(model_dir=settings.MODEL_DIR)
    package = loader.load_and_validate()
    
    assert package.model is not None
    assert package.explanation_model is not None
    
    # Verify metadata and schema
    assert package.metadata["package_version"] is not None
    assert len(package.feature_schema["features"]) == 13
    assert len(package.feature_schema["feature_order"]) == 13
    assert "target" not in package.feature_schema["feature_order"]

def test_sklearn_compatibility_passes():
    loader = ModelLoader(model_dir=settings.MODEL_DIR)
    package = loader.load_and_validate()
    expected_version = package.metadata["environment"]["sklearn_version"]
    assert sklearn.__version__ == expected_version

def test_missing_model_artifact_fails(tmp_path):
    loader = ModelLoader(model_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.load_and_validate()

def test_invalid_metadata_fails(tmp_path):
    # Setup dummy files
    (tmp_path / "model.joblib").touch()
    (tmp_path / "explanation_model.joblib").touch()
    (tmp_path / "feature_schema.json").touch()
    
    # Write invalid metadata
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text('{"bad_json": }')
    
    loader = ModelLoader(model_dir=tmp_path)
    with pytest.raises(ValueError, match="Failed to parse metadata"):
        loader.load_and_validate()

def test_missing_schema_fails(tmp_path):
    (tmp_path / "model.joblib").touch()
    (tmp_path / "explanation_model.joblib").touch()
    
    # Write valid metadata
    meta_path = tmp_path / "metadata.json"
    valid_meta = {
        "package_version": "1.0",
        "environment": {"sklearn_version": sklearn.__version__},
        "model_configuration": {},
        "calibration_configuration": {},
        "feature_schema_version": "1.0",
        "training_data_provenance": {
            "raw_dataset_sha256": "abc",
            "development_indices_sha256": "def"
        }
    }
    meta_path.write_text(json.dumps(valid_meta))
    
    loader = ModelLoader(model_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="feature_schema.json"):
        loader.load_and_validate()
        
def test_schema_wrong_feature_count(tmp_path):
    (tmp_path / "model.joblib").touch()
    (tmp_path / "explanation_model.joblib").touch()
    
    meta_path = tmp_path / "metadata.json"
    valid_meta = {
        "package_version": "1.0",
        "environment": {"sklearn_version": sklearn.__version__},
        "model_configuration": {},
        "calibration_configuration": {},
        "feature_schema_version": "1.0",
        "training_data_provenance": {
            "raw_dataset_sha256": "abc",
            "development_indices_sha256": "def"
        }
    }
    meta_path.write_text(json.dumps(valid_meta))
    
    schema_path = tmp_path / "feature_schema.json"
    invalid_schema = {
        "features": [{"name": "f1", "type": "binary"}],
        "feature_order": ["f1"]
    }
    schema_path.write_text(json.dumps(invalid_schema))
    
    loader = ModelLoader(model_dir=tmp_path)
    with pytest.raises(ValueError, match="exactly 13 input features"):
        loader.load_and_validate()

def test_api_health_endpoint():
    # Using TestClient automatically triggers the lifespan context manager
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "CardioVanta"}
