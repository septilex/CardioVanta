"""
Registry metadata schema (``<registry root>/models/<model_id>/<model_version>/metadata.json``).

Validation is strict: unknown, missing, mistyped or contradictory fields are
rejected (``MetadataError`` / ``OutcomeMappingError``). Nothing here falls back
to an implicit default. In particular, the disease-present class label must be
declared explicitly for every registered model.

The clinical outcome definition lives in the feature contract. This metadata only
records how THIS artifact's class labels map onto it.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from cardiovanta_ml.config import REGISTRY_SCHEMA_VERSION
from cardiovanta_ml.registry.exceptions import MetadataError, OutcomeMappingError
from cardiovanta_ml.registry.integrity import is_sha256, validate_file_name

MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
MODEL_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

REQUIRED_ARTIFACT_ROLES = ("model", "explanation_model", "package_metadata", "input_schema", "shap_background")
OPTIONAL_ARTIFACT_ROLES = ("reference_predictions",)
MAPPING_STATUSES = ("explicit", "interim_legacy")
CLASS_SEMANTICS = ("disease_present", "disease_absent")

_TOP_LEVEL = {
    "registry_schema_version": str,
    "model_id": str,
    "model_version": str,
    "model_package_name": str,
    "artifact_directory": str,
    "artifacts": dict,
    "checksum_manifest": str,
    "checksum_manifest_sha256": str,
    "model_card": str,
    "feature_contract": dict,
    "feature_order": list,
    "model_classes": list,
    "class_label_semantics": dict,
    "outcome_semantics": dict,
    "calibration": dict,
    "explanation": dict,
    "runtime": dict,
    "provenance": dict,
}


@dataclass(frozen=True)
class FeatureContractRef:
    name: str
    version: str
    sha256: str


@dataclass(frozen=True)
class OutcomeSemantics:
    outcome: str
    contract_version: str
    disease_present_label: int
    mapping_status: str
    evidence: Tuple[str, ...]


@dataclass(frozen=True)
class ExplanationInfo:
    artifact_role: str
    background_role: str
    associated_model: str
    description: str


@dataclass(frozen=True)
class RegistryMetadata:
    model_id: str
    model_version: str
    model_package_name: str
    artifact_directory: str
    artifacts: Dict[str, str]          # role -> file name
    checksum_manifest: str
    checksum_manifest_sha256: str
    model_card: str
    feature_contract: FeatureContractRef
    feature_order: Tuple[str, ...]
    model_classes: Tuple[int, ...]
    class_label_semantics: Dict[int, str]
    outcome: OutcomeSemantics
    calibration: Dict[str, Any]
    explanation: ExplanationInfo
    sklearn_version: str
    provenance: Dict[str, Any]
    raw: Dict[str, Any]

    @property
    def qualified_name(self) -> str:
        return f"{self.model_id}@{self.model_version}"

    @property
    def disease_present_label(self) -> int:
        return self.outcome.disease_present_label

    def artifact_file(self, role: str) -> str:
        return self.artifacts[role]


def validate_model_id(model_id: object) -> str:
    if not isinstance(model_id, str) or not MODEL_ID_RE.match(model_id):
        raise MetadataError(f"Invalid model id {model_id!r}")
    return model_id


def validate_model_version(version: object) -> str:
    if not isinstance(version, str) or not MODEL_VERSION_RE.match(version):
        raise MetadataError(f"Invalid model version {version!r}: expected exact semantic version MAJOR.MINOR.PATCH")
    return version


def _require_keys(obj: Mapping[str, Any], spec: Mapping[str, type], where: str) -> None:
    if not isinstance(obj, dict):
        raise MetadataError(f"{where}: expected an object")
    unknown = set(obj) - set(spec)
    missing = set(spec) - set(obj)
    if unknown:
        raise MetadataError(f"{where}: unsupported key(s) {sorted(unknown)}")
    if missing:
        raise MetadataError(f"{where}: missing required key(s) {sorted(missing)}")
    for key, typ in spec.items():
        value = obj[key]
        if typ is int:
            ok = isinstance(value, int) and not isinstance(value, bool)
        else:
            ok = isinstance(value, typ)
        if not ok:
            raise MetadataError(f"{where}.{key}: expected {typ.__name__}, got {type(value).__name__}")


def _nonempty(value: str, where: str) -> str:
    if not value.strip():
        raise MetadataError(f"{where} must be non-empty")
    return value


def _class_label(value: object, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OutcomeMappingError(f"{where}: class labels must be integers, got {value!r}")
    return value


def parse_metadata(raw: Any) -> RegistryMetadata:
    """Validate raw metadata JSON and return a typed, immutable ``RegistryMetadata``."""
    _require_keys(raw, _TOP_LEVEL, "metadata")
    if raw["registry_schema_version"] != REGISTRY_SCHEMA_VERSION:
        raise MetadataError(
            f"Unsupported registry_schema_version {raw['registry_schema_version']!r} (expected {REGISTRY_SCHEMA_VERSION!r})"
        )
    model_id = validate_model_id(raw["model_id"])
    model_version = validate_model_version(raw["model_version"])
    _nonempty(raw["model_package_name"], "metadata.model_package_name")
    _nonempty(raw["artifact_directory"], "metadata.artifact_directory")

    # Artifacts: role -> plain file name.
    artifacts = raw["artifacts"]
    allowed_roles = set(REQUIRED_ARTIFACT_ROLES) | set(OPTIONAL_ARTIFACT_ROLES)
    unknown_roles = set(artifacts) - allowed_roles
    missing_roles = set(REQUIRED_ARTIFACT_ROLES) - set(artifacts)
    if unknown_roles:
        raise MetadataError(f"metadata.artifacts: unsupported role(s) {sorted(unknown_roles)}")
    if missing_roles:
        raise MetadataError(f"metadata.artifacts: missing required role(s) {sorted(missing_roles)}")
    files = {role: validate_file_name(name) for role, name in artifacts.items()}
    if len(set(files.values())) != len(files):
        raise MetadataError("metadata.artifacts: two roles reference the same file")

    validate_file_name(raw["checksum_manifest"])
    validate_file_name(raw["model_card"])
    if not is_sha256(raw["checksum_manifest_sha256"]):
        raise MetadataError("metadata.checksum_manifest_sha256 must be a lowercase hex SHA-256")

    fc = raw["feature_contract"]
    _require_keys(fc, {"name": str, "version": str, "sha256": str}, "metadata.feature_contract")
    if not is_sha256(fc["sha256"]):
        raise MetadataError("metadata.feature_contract.sha256 must be a lowercase hex SHA-256")

    order = raw["feature_order"]
    if not order or not all(isinstance(f, str) and f for f in order) or len(set(order)) != len(order):
        raise MetadataError("metadata.feature_order must be a non-empty list of unique feature ids")

    # Class labels and their clinical semantics.
    classes = [_class_label(c, "metadata.model_classes") for c in raw["model_classes"]]
    if len(classes) != 2 or len(set(classes)) != 2:
        raise OutcomeMappingError(f"metadata.model_classes must list exactly two distinct labels, got {classes}")
    semantics_raw = raw["class_label_semantics"]
    try:
        semantics = {int(k): v for k, v in semantics_raw.items()}
    except (TypeError, ValueError):
        raise OutcomeMappingError("metadata.class_label_semantics keys must be integer labels")
    if set(semantics) != set(classes):
        raise OutcomeMappingError(
            f"metadata.class_label_semantics labels {sorted(semantics)} do not match model_classes {classes}"
        )
    if sorted(semantics.values()) != sorted(CLASS_SEMANTICS):
        raise OutcomeMappingError(
            "metadata.class_label_semantics must map exactly one label to 'disease_present' and one to 'disease_absent'"
        )

    os_raw = raw["outcome_semantics"]
    try:
        _require_keys(os_raw, {"outcome": str, "contract_version": str, "disease_present_label": int,
                               "mapping_status": str, "evidence": list}, "metadata.outcome_semantics")
    except MetadataError as e:  # a missing or mistyped outcome mapping is an outcome-mapping failure
        raise OutcomeMappingError(str(e)) from e
    disease_label = os_raw["disease_present_label"]
    if disease_label not in classes:
        raise OutcomeMappingError(f"disease_present_label {disease_label!r} is not one of model_classes {classes}")
    if semantics[disease_label] != "disease_present":
        raise OutcomeMappingError(
            f"disease_present_label {disease_label} contradicts class_label_semantics ({semantics[disease_label]!r})"
        )
    if os_raw["mapping_status"] not in MAPPING_STATUSES:
        raise OutcomeMappingError(f"outcome_semantics.mapping_status must be one of {MAPPING_STATUSES}")
    outcome = OutcomeSemantics(
        outcome=os_raw["outcome"],
        contract_version=os_raw["contract_version"],
        disease_present_label=disease_label,
        mapping_status=os_raw["mapping_status"],
        evidence=tuple(str(e) for e in os_raw["evidence"]),
    )

    cal = raw["calibration"]
    for key in ("method", "estimator"):
        if not isinstance(cal.get(key), str) or not cal[key]:
            raise MetadataError(f"metadata.calibration.{key} is required")

    exp = raw["explanation"]
    _require_keys(exp, {"artifact_role": str, "background_role": str, "associated_model": str, "description": str},
                  "metadata.explanation")
    if exp["artifact_role"] != "explanation_model" or exp["background_role"] != "shap_background":
        raise MetadataError("metadata.explanation must reference the 'explanation_model' and 'shap_background' roles")

    rt = raw["runtime"]
    if not isinstance(rt.get("sklearn_version"), str) or not rt["sklearn_version"]:
        raise MetadataError("metadata.runtime.sklearn_version is required")

    return RegistryMetadata(
        model_id=model_id,
        model_version=model_version,
        model_package_name=raw["model_package_name"],
        artifact_directory=raw["artifact_directory"],
        artifacts=files,
        checksum_manifest=raw["checksum_manifest"],
        checksum_manifest_sha256=raw["checksum_manifest_sha256"],
        model_card=raw["model_card"],
        feature_contract=FeatureContractRef(fc["name"], fc["version"], fc["sha256"]),
        feature_order=tuple(order),
        model_classes=tuple(classes),
        class_label_semantics=semantics,
        outcome=outcome,
        calibration=dict(cal),
        explanation=ExplanationInfo(exp["artifact_role"], exp["background_role"], exp["associated_model"],
                                    exp["description"]),
        sklearn_version=rt["sklearn_version"],
        provenance=dict(raw["provenance"]),
        raw=raw,
    )


def read_metadata(path: Path) -> RegistryMetadata:
    if not path.is_file():
        raise MetadataError(f"Registry metadata not found: {path.name}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise MetadataError(f"Malformed registry metadata {path.name}: {e}") from e
    return parse_metadata(raw)


def declared_files(meta: RegistryMetadata) -> List[str]:
    return list(meta.artifacts.values())


def optional_role(meta: RegistryMetadata, role: str) -> Optional[str]:
    return meta.artifacts.get(role)
