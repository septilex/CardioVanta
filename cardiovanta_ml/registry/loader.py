"""
Versioned model registry loader.

``load_model(model_id, model_version, registry_root)`` runs these steps, in this
order, and fails closed (raises a ``RegistryError`` subclass) at the first problem:

1. Validate the requested ID and exact semantic version. There is no
   "latest", and directories are never scanned.
2. Locate ``<root>/models/<id>/<version>/`` (must exist, inside the root).
3. Read and strictly validate ``metadata.json``. Its ID/version must equal the request.
4. Check compatibility with the bundled clinical contract: name, version, SHA-256,
   feature order and outcome, plus agreement with the contract's model-label
   mapping when the contract lists this package.
5. Resolve the artifact directory and every artifact path inside the registry root.
6. Verify the checksum manifest's own SHA-256, that the manifest lists exactly the
   declared artifacts, and every artifact's SHA-256.
7. Check the runtime scikit-learn version equals the registered one.
8. Only now deserialize: JSON artifacts, then the two joblib models.
9. Validate the loaded objects: class labels, disease label, feature order of both
   models, input schema, package metadata version, explanation/background association.

Successful loads are cached per (registry root, id, version), so a model version
is deserialized at most once per process.
"""
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from cardiovanta_ml.config import MODELS_SUBDIR, REGISTRY_METADATA_FILE, resolve_registry_root
from cardiovanta_ml.contracts import bundled_contract_sha256
from cardiovanta_ml.contracts import generated_features as contract
from cardiovanta_ml.registry.exceptions import (
    ContractMismatchError,
    MetadataError,
    ModelCompatibilityError,
    ModelNotRegisteredError,
    OutcomeMappingError,
)
from cardiovanta_ml.registry.integrity import resolve_within, verify_artifacts, verify_manifest_file
from cardiovanta_ml.registry.metadata import (
    RegistryMetadata,
    declared_files,
    read_metadata,
    validate_model_id,
    validate_model_version,
)


@dataclass(frozen=True)
class LoadedModel:
    """An integrity-verified, validated, deserialized registered model."""

    metadata: RegistryMetadata
    model: Any
    explanation_model: Any
    input_schema: Dict[str, Any]
    package_metadata: Dict[str, Any]
    shap_background: Dict[str, Any]
    entry_dir: Path
    artifact_dir: Path

    @property
    def model_id(self) -> str:
        return self.metadata.model_id

    @property
    def model_version(self) -> str:
        return self.metadata.model_version

    @property
    def disease_label(self) -> int:
        return self.metadata.disease_present_label


_CACHE: Dict[Tuple[str, str, str], LoadedModel] = {}
_LOCK = threading.Lock()


def clear_model_cache() -> None:
    """Forget cached models (tests only; production loads once per process)."""
    with _LOCK:
        _CACHE.clear()


def load_model(model_id: str, model_version: str, registry_root: Optional[Union[str, Path]] = None) -> LoadedModel:
    """Load an explicitly identified, integrity-verified model (cached per process)."""
    try:
        validate_model_id(model_id)
        validate_model_version(model_version)
    except MetadataError as e:
        raise ModelNotRegisteredError(str(e)) from e
    root = resolve_registry_root(registry_root)
    key = (str(root), model_id, model_version)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            return cached
        loaded = _load_uncached(root, model_id, model_version)
        _CACHE[key] = loaded
        return loaded


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def _locate_entry(root: Path, model_id: str, model_version: str) -> Path:
    if not root.is_dir():
        raise ModelNotRegisteredError(f"Model registry root does not exist: {root}")
    try:
        entry = resolve_within(root, f"{MODELS_SUBDIR}/{model_id}/{model_version}")
    except Exception as e:  # unsafe id/version cannot reach here after validation, but fail closed
        raise ModelNotRegisteredError(str(e)) from e
    if not entry.is_dir():
        raise ModelNotRegisteredError(f"Model {model_id}@{model_version} is not registered")
    return entry


def _check_contract(meta: RegistryMetadata) -> None:
    fc = meta.feature_contract
    if fc.name != contract.CONTRACT_NAME:
        raise ContractMismatchError(f"Model registered against contract {fc.name!r}, expected {contract.CONTRACT_NAME!r}")
    if fc.version != contract.CONTRACT_VERSION:
        raise ContractMismatchError(
            f"Model registered against contract v{fc.version}, package provides v{contract.CONTRACT_VERSION}"
        )
    if fc.sha256 != contract.CONTRACT_SHA256:
        raise ContractMismatchError("Model's feature contract SHA-256 does not match the bundled contract")
    if bundled_contract_sha256() != contract.CONTRACT_SHA256:
        raise ContractMismatchError(
            "Bundled contract JSON does not match the generated contract module (run contracts/codegen/generate.py)"
        )
    if meta.feature_order != tuple(contract.FEATURE_ORDER):
        raise ContractMismatchError("Registered feature order does not match the clinical contract")

    if meta.outcome.outcome != contract.OUTCOME_ID:
        raise OutcomeMappingError(
            f"Model outcome {meta.outcome.outcome!r} is not the contract outcome {contract.OUTCOME_ID!r}"
        )
    if meta.outcome.contract_version != contract.CONTRACT_VERSION:
        raise OutcomeMappingError("Model outcome mapping refers to a different contract version")

    # The contract's model_label_mappings records known artifact mappings. If it lists
    # this package, the registry metadata must agree. Interim (legacy) mappings MUST
    # be corroborated by the contract; they are never accepted on metadata alone.
    listed = [p for p in contract.MODEL_LABEL_MAPPINGS
              if p["model_id"] == meta.model_id and p["package_version"] == meta.model_version]
    if listed:
        expected = listed[0]
        if expected["disease_present_label"] != meta.disease_present_label:
            raise OutcomeMappingError(
                f"Registry declares disease label {meta.disease_present_label} but the contract records "
                f"{expected['disease_present_label']} for {meta.qualified_name}"
            )
        if expected["status"] != meta.outcome.mapping_status:
            raise OutcomeMappingError("Registry mapping_status contradicts the contract's model_label_mappings")
    elif meta.outcome.mapping_status == "interim_legacy":
        raise OutcomeMappingError(
            f"{meta.qualified_name} declares an interim legacy mapping that the contract does not record"
        )


def _check_runtime(meta: RegistryMetadata) -> None:
    import sklearn

    if sklearn.__version__ != meta.sklearn_version:
        raise ModelCompatibilityError(
            f"scikit-learn {sklearn.__version__} cannot load {meta.qualified_name} "
            f"(registered with {meta.sklearn_version}); refusing to deserialize"
        )


def _read_json(path: Path, role: str) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise MetadataError(f"Artifact {role} ({path.name}) is not valid JSON: {e}") from e


def _labels(obj: Any) -> Tuple[int, ...]:
    return tuple(int(c) for c in getattr(obj, "classes_", ()))


def _validate_loaded(meta: RegistryMetadata, model: Any, explanation_model: Any, input_schema: Dict[str, Any],
                     package_metadata: Dict[str, Any], shap_background: Dict[str, Any]) -> None:
    for name, obj in (("model", model), ("explanation_model", explanation_model)):
        if _labels(obj) != meta.model_classes:
            raise ModelCompatibilityError(
                f"{name} classes {_labels(obj)} do not match registered model_classes {meta.model_classes}"
            )
        names = tuple(getattr(obj, "feature_names_in_", ()))
        if names != meta.feature_order:
            raise ModelCompatibilityError(f"{name} feature order {names} does not match the registered contract order")
    if meta.disease_present_label not in _labels(model):
        raise OutcomeMappingError("Declared disease-present label is not a class of the loaded model")

    # Model input schema shipped with the package.
    features = input_schema.get("features")
    order = input_schema.get("feature_order")
    if not isinstance(features, list) or not isinstance(order, list):
        raise ModelCompatibilityError("input_schema must contain 'features' and 'feature_order'")
    if tuple(order) != meta.feature_order or [f.get("name") for f in features] != list(meta.feature_order):
        raise ModelCompatibilityError("input_schema feature order does not match the registered contract order")
    if "target" in order:
        raise ModelCompatibilityError("Target column must not be an input feature")
    for f in features:
        if "name" not in f or "type" not in f:
            raise ModelCompatibilityError("Each input_schema feature must have a name and type")

    if package_metadata.get("package_version") != meta.model_version:
        raise ModelCompatibilityError(
            f"Package metadata version {package_metadata.get('package_version')!r} does not match {meta.model_version}"
        )
    pkg_sklearn = package_metadata.get("environment", {}).get("sklearn_version")
    if pkg_sklearn != meta.sklearn_version:
        raise ModelCompatibilityError("Package metadata sklearn_version contradicts registry metadata")

    # Explanation model and SHAP background must belong to THIS model.
    if meta.explanation.associated_model != meta.qualified_name:
        raise ModelCompatibilityError(
            f"Explanation artifacts are associated with {meta.explanation.associated_model!r}, not {meta.qualified_name}"
        )
    bg_ref = shap_background.get("metadata", {}).get("model_reference")
    if bg_ref != meta.artifact_file("explanation_model"):
        raise ModelCompatibilityError(f"SHAP background references {bg_ref!r}, not the registered explanation model")
    try:
        transformed = list(explanation_model.named_steps["preprocessor"].get_feature_names_out())
    except Exception as e:
        raise ModelCompatibilityError(f"Explanation model lacks the expected preprocessor: {e}") from e
    if list(shap_background.get("feature_names", [])) != transformed:
        raise ModelCompatibilityError("SHAP background feature names do not match the explanation model")
    if set(shap_background.get("background_means", {})) != set(transformed):
        raise ModelCompatibilityError("SHAP background means do not cover the explanation model's features")


def _load_uncached(root: Path, model_id: str, model_version: str) -> LoadedModel:
    entry = _locate_entry(root, model_id, model_version)
    meta = read_metadata(entry / REGISTRY_METADATA_FILE)
    if (meta.model_id, meta.model_version) != (model_id, model_version):
        raise MetadataError(
            f"Metadata identifies {meta.qualified_name} but is registered at {model_id}@{model_version}"
        )
    _check_contract(meta)

    artifact_dir = resolve_within(root, meta.artifact_directory)
    if not artifact_dir.is_dir():
        raise MetadataError(f"Artifact directory {meta.artifact_directory!r} does not exist")
    resolve_within(entry, meta.model_card)
    manifest = verify_manifest_file(resolve_within(entry, meta.checksum_manifest), meta.checksum_manifest_sha256)
    verified = verify_artifacts(artifact_dir, manifest, declared_files(meta))   # <- before any deserialization
    _check_runtime(meta)

    def path(role: str) -> Path:
        return verified[meta.artifact_file(role)]

    input_schema = _read_json(path("input_schema"), "input_schema")
    package_metadata = _read_json(path("package_metadata"), "package_metadata")
    shap_background = _read_json(path("shap_background"), "shap_background")

    import joblib  # deserialization only after every integrity check above has passed

    try:
        model = joblib.load(path("model"))
        explanation_model = joblib.load(path("explanation_model"))
    except Exception as e:
        raise ModelCompatibilityError(f"Failed to deserialize verified artifacts for {meta.qualified_name}: {e}") from e

    _validate_loaded(meta, model, explanation_model, input_schema, package_metadata, shap_background)
    return LoadedModel(
        metadata=meta,
        model=model,
        explanation_model=explanation_model,
        input_schema=input_schema,
        package_metadata=package_metadata,
        shap_background=shap_background,
        entry_dir=entry,
        artifact_dir=artifact_dir,
    )
