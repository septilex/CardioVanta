import json
import logging
import joblib
import sklearn
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ModelPackage:
    def __init__(self):
        self.model = None
        self.explanation_model = None
        self.metadata: Dict[str, Any] = {}
        self.feature_schema: Dict[str, Any] = {}

class ModelLoader:
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model_path = model_dir / "model.joblib"
        self.explanation_model_path = model_dir / "explanation_model.joblib"
        self.metadata_path = model_dir / "metadata.json"
        self.schema_path = model_dir / "feature_schema.json"
        
    def load_and_validate(self) -> ModelPackage:
        package = ModelPackage()
        
        # 1. Verify existence of required files
        required_paths = [self.model_path, self.explanation_model_path, self.metadata_path, self.schema_path]
        for p in required_paths:
            if not p.exists():
                raise FileNotFoundError(f"Required artifact not found: {p}")
                
        # 2. Metadata validation
        try:
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse metadata.json: {e}")
            
        required_metadata_keys = [
            "package_version",
            "environment",
            "model_configuration",
            "calibration_configuration",
            "feature_schema_version",
            "training_data_provenance"
        ]
        for k in required_metadata_keys:
            if k not in metadata:
                raise ValueError(f"Missing required metadata key: {k}")
                
        provenance = metadata["training_data_provenance"]
        if "raw_dataset_sha256" not in provenance or "development_indices_sha256" not in provenance:
            raise ValueError("Missing required provenance sha256 hashes")
            
        if "sklearn_version" not in metadata["environment"]:
            raise ValueError("Missing sklearn_version in environment metadata")
            
        # 3. Sklearn compatibility check
        expected_sklearn_version = metadata["environment"]["sklearn_version"]
        actual_sklearn_version = sklearn.__version__
        if actual_sklearn_version != expected_sklearn_version:
            raise RuntimeError(f"Sklearn version mismatch. Expected {expected_sklearn_version}, got {actual_sklearn_version}")
            
        package.metadata = metadata
        
        # 4. Schema validation
        try:
            with open(self.schema_path, 'r') as f:
                schema = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse feature_schema.json: {e}")
            
        if "features" not in schema or "feature_order" not in schema:
            raise ValueError("Schema must contain 'features' and 'feature_order'")
            
        if len(schema["features"]) != 13 or len(schema["feature_order"]) != 13:
            raise ValueError("Schema must define exactly 13 input features")
            
        target_in_features = any(f.get("name") == "target" for f in schema["features"])
        if target_in_features or "target" in schema["feature_order"]:
            raise ValueError("Target column must not be treated as an input feature")
            
        for f in schema["features"]:
            if "name" not in f or "type" not in f:
                raise ValueError("Each feature must have a name and type")
                
        package.feature_schema = schema
        
        # 5. Load Models
        try:
            package.model = joblib.load(self.model_path)
            package.explanation_model = joblib.load(self.explanation_model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load joblib models: {e}")
            
        logger.info("Successfully loaded and validated frozen CardioVanta ML package.")
        return package
