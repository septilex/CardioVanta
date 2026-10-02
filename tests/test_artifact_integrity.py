import json
import pytest
from pathlib import Path
import sys

# Ensure scripts can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.verify_artifact_integrity import verify_artifacts, calculate_sha256

@pytest.fixture
def temp_artifact_env(tmp_path):
    # Create the config and model directories
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    model_dir = tmp_path / "artifacts" / "model"
    model_dir.mkdir(parents=True)
    
    # Create dummy artifacts and compute their actual hashes
    manifest_data = {}
    
    artifacts = [
        "model.joblib",
        "explanation_model.joblib",
        "metadata.json",
        "feature_schema.json",
        "reference_predictions.csv",
        "shap_background.json"
    ]
    
    for i, artifact in enumerate(artifacts):
        file_path = model_dir / artifact
        file_path.write_text(f"dummy content {i}")
        hash_val = calculate_sha256(file_path)
        manifest_data[f"artifacts/model/{artifact}"] = hash_val
        
    manifest_path = config_dir / "artifact_hashes.json"
    manifest_path.write_text(json.dumps(manifest_data))
    
    return tmp_path, manifest_path, manifest_data

def test_verify_all_correct(temp_artifact_env, capsys):
    tmp_path, manifest_path, manifest_data = temp_artifact_env
    
    result = verify_artifacts(str(manifest_path), tmp_path)
    assert result is True
    
    captured = capsys.readouterr()
    assert "[PASS] artifacts/model/model.joblib" in captured.out

def test_verify_missing_artifact(temp_artifact_env, capsys):
    tmp_path, manifest_path, manifest_data = temp_artifact_env
    
    # Delete an artifact
    (tmp_path / "artifacts" / "model" / "metadata.json").unlink()
    
    result = verify_artifacts(str(manifest_path), tmp_path)
    assert result is False
    
    captured = capsys.readouterr()
    assert "[FAIL] Missing file: artifacts/model/metadata.json" in captured.out

def test_verify_modified_artifact(temp_artifact_env, capsys):
    tmp_path, manifest_path, manifest_data = temp_artifact_env
    
    # Modify an artifact
    (tmp_path / "artifacts" / "model" / "feature_schema.json").write_text("tampered content")
    
    result = verify_artifacts(str(manifest_path), tmp_path)
    assert result is False
    
    captured = capsys.readouterr()
    assert "[FAIL] artifacts/model/feature_schema.json" in captured.out
    assert "Expected:" in captured.out
    assert "Actual:" in captured.out

def test_verify_invalid_manifest(tmp_path, capsys):
    # Test path handling when manifest doesn't exist
    result = verify_artifacts(str(tmp_path / "missing.json"), tmp_path)
    assert result is False
    captured = capsys.readouterr()
    assert "FAILED to load manifest" in captured.out
