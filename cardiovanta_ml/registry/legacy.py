"""
Legacy ``ModelLoader`` interface (pre-R2 ``backend/app/core/model_loader.py``), as a registry adapter (R3).

``ModelLoader(model_dir).load_and_validate()`` keeps its public interface and runs
its original pre-load checks in the original order (same errors and messages):
files exist, metadata keys, scikit-learn version, input schema, outcome orientation.

R3 hardening: it NO LONGER deserializes anything itself. Deserialization is
delegated to ``cardiovanta_ml.registry.load_model``, which verifies SHA-256
checksums before loading. The model identity comes from an explicit record:
either the caller's ``model_id``/``model_version``, or the clinical contract's
``model_label_mappings`` entry for the directory's ``package_version``. The
contract must record exactly one entry; nothing is scanned and there is no
fallback. The registered model's artifact directory must be ``model_dir`` itself.
A directory that is not a registered, checksum-verified model cannot be loaded
through this class.

Production serving does not use this class (FastAPI startup calls ``load_model`` directly).
"""
import json
import logging
import sklearn
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
from cardiovanta_ml.contracts import generated_features as _contract
from cardiovanta_ml.inference.outcome import resolve_disease_label, disease_label_index
from cardiovanta_ml.registry.loader import load_model

logger = logging.getLogger(__name__)

class ModelPackage:
    def __init__(self):
        self.model = None
        self.explanation_model = None
        self.metadata: Dict[str, Any] = {}
        self.feature_schema: Dict[str, Any] = {}

def _registered_identity(package_version: Any) -> Tuple[str, str]:
    """Explicit contract record for a legacy package version (exactly one match, never a scan)."""
    matches = [p for p in _contract.MODEL_LABEL_MAPPINGS if p["package_version"] == package_version]
    if len(matches) != 1:
        raise ValueError(
            f"Package version {package_version!r} has no unique registered model in the clinical contract; "
            "load models with cardiovanta_ml.load_model(model_id, model_version, registry_root)."
        )
    return matches[0]["model_id"], matches[0]["package_version"]


class ModelLoader:
    def __init__(self, model_dir: Path, model_id: Optional[str] = None, model_version: Optional[str] = None,
                 registry_root: Optional[Union[str, Path]] = None):
        self.model_dir = model_dir
        self.model_id = model_id
        self.model_version = model_version
        self.registry_root = registry_root
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

        # Outcome orientation must be established before serving (R0.3).
        # Raises ValueError for packages that declare no disease-present label
        # and are not the documented interim legacy package.
        disease_label = resolve_disease_label(metadata)

        # 5. Load Models through the verified registry (R3): SHA-256 checks run BEFORE
        #    deserialization. There is no unchecked joblib.load path here any more.
        if (self.model_id is None) != (self.model_version is None):
            raise ValueError("Pass both model_id and model_version, or neither")
        if self.model_id is None:
            model_id, model_version = _registered_identity(metadata.get("package_version"))
        else:
            model_id, model_version = self.model_id, self.model_version
        model_dir = Path(self.model_dir).resolve()
        registry_root = Path(self.registry_root).resolve() if self.registry_root is not None else model_dir.parent
        loaded = load_model(model_id, model_version, registry_root=registry_root)
        if loaded.artifact_dir != model_dir:
            raise ValueError(
                f"{model_id}@{model_version} is registered with artifact directory {loaded.artifact_dir}, not {model_dir}"
            )
        package.model = loaded.model
        package.explanation_model = loaded.explanation_model
        package.metadata = loaded.package_metadata
        package.feature_schema = loaded.input_schema

        # The disease label must exist in both models' binary class sets.
        disease_label_index(package.model.classes_, disease_label)
        disease_label_index(package.explanation_model.classes_, disease_label)

        logger.info("Successfully loaded and validated frozen CardioVanta ML package.")
        return package
