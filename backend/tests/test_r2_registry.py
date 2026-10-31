"""
R2 tests: installable ``cardiovanta_ml`` package and versioned, SHA-256-verified model registry.

All inputs are SYNTHETIC. ``data/raw/heart.csv`` is never opened. Registry
failure tests run against throwaway copies of the registry in ``tmp_path``; the
real artifacts are never modified.
"""
import ast
import dataclasses
import fnmatch
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient

import cardiovanta_ml
from cardiovanta_ml import InferenceEngine, clear_model_cache, explain, load_model, predict
from cardiovanta_ml.contracts import bundled_contract_sha256, load_contract
from cardiovanta_ml.contracts import generated_features as contract
from cardiovanta_ml.registry import (
    ArtifactPathError,
    ContractMismatchError,
    IntegrityError,
    MetadataError,
    ModelCompatibilityError,
    ModelNotRegisteredError,
    OutcomeMappingError,
    RegistryConfigurationError,
    RegistryError,
)

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_ROOT = ROOT / "artifacts"
PKG_DIR = ROOT / "cardiovanta_ml"
ENTRY_REL = Path("models") / "cardiovanta-lr13" / "1.0.0"
MODEL_ID, MODEL_VERSION = "cardiovanta-lr13", "1.0.0"

# Original artifact SHA-256 values (R0 baseline manifest / configs/artifact_hashes.json).
ORIGINAL_SHA256 = {
    "model.joblib": "18e2268e797020e6a24da44ae7279e39581f7bab5bffb3c8d31dcf2ea379a348",
    "explanation_model.joblib": "da66de612a2bb2d45ecf1319bb2e07708c76688da2b54c2e529c6f6d7186aecc",
    "metadata.json": "c6936399f27a8f20c04106cb6f5e4dcbc88a4cb71593b69ff0d04dd739bb883d",
    "feature_schema.json": "eeb6c2bd8383628de1de552219f8c4add628277292ea5815f4f384f2ba4b44a2",
    "reference_predictions.csv": "43c226b0e54c637c8b9d5b077604a177d735f10891749ca71dfdf85d3f5b72e2",
    "shap_background.json": "f5964e2a42527ea770e7037120f355a403e0916b326ae44fad5a2c8f31339e1d",
}

HIGH_RISK = dict(age=67.0, sex=1, cp=0, trestbps=160.0, chol=286.0, fbs=0, restecg=0,
                 thalach=108.0, exang=1, oldpeak=3.0, slope=1, ca=3, thal=3)
LOW_RISK = dict(age=37.0, sex=0, cp=2, trestbps=120.0, chol=200.0, fbs=0, restecg=1,
                thalach=187.0, exang=0, oldpeak=0.0, slope=2, ca=0, thal=2)
SNAPSHOT_INPUTS = {
    "high_risk": HIGH_RISK,
    "low_risk": LOW_RISK,
    "frontend_default": dict(age=45, sex=1, cp=0, trestbps=120, chol=200, fbs=0, restecg=1, thalach=150,
                             exang=0, oldpeak=1.0, slope=1, ca=0, thal=2),
    "out_of_range": dict(age=95.0, sex=0, cp=3, trestbps=210.0, chol=600.0, fbs=1, restecg=2, thalach=60.0,
                         exang=1, oldpeak=7.0, slope=0, ca=4, thal=0),
}


@pytest.fixture(scope="module")
def model():
    return load_model(MODEL_ID, MODEL_VERSION, registry_root=REGISTRY_ROOT)


@pytest.fixture
def fresh_cache():
    clear_model_cache()
    yield
    clear_model_cache()


@pytest.fixture
def registry(tmp_path, fresh_cache):
    """A throwaway copy of the registry (registry entry + immutable artifact directory)."""
    root = tmp_path / "artifacts"
    shutil.copytree(REGISTRY_ROOT / "model", root / "model")
    shutil.copytree(REGISTRY_ROOT / ENTRY_REL, root / ENTRY_REL)
    return root


def _meta_path(root):
    return root / ENTRY_REL / "metadata.json"


def _edit_metadata(root, mutate):
    path = _meta_path(root)
    meta = json.loads(path.read_text(encoding="utf-8"))
    mutate(meta)
    path.write_text(json.dumps(meta), encoding="utf-8")


def _rewrite_manifest(root, lines):
    """Write a new manifest AND update its pinned hash in metadata (a consistent edit)."""
    manifest = root / ENTRY_REL / "checksums.sha256"
    manifest.write_bytes(("\n".join(lines) + "\n").encode("ascii"))
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    _edit_metadata(root, lambda m: m.update(checksum_manifest_sha256=digest))


@pytest.fixture
def no_deserialize(monkeypatch):
    """Fail the test if anything is deserialized (proves verification happens first)."""
    calls = []

    def guard(*args, **kwargs):
        calls.append(args)
        raise AssertionError("joblib.load must not be called before integrity verification passes")

    monkeypatch.setattr(joblib, "load", guard)
    return calls


# =============================================================================
# Package
# =============================================================================

def test_public_api(model):
    assert cardiovanta_ml.__version__ == "0.2.0"
    assert callable(cardiovanta_ml.load_model) and callable(cardiovanta_ml.predict)
    result = predict(HIGH_RISK, model, threshold=0.5)
    assert result["outcome"] == contract.OUTCOME_ID and result["class"] == 1
    both = explain(HIGH_RISK, model)
    assert set(both) == {"linear", "shap_equivalent"}


def test_contract_resource_is_bundled_and_consistent():
    assert bundled_contract_sha256() == contract.CONTRACT_SHA256
    assert load_contract()["contract_version"] == contract.CONTRACT_VERSION == "2.0.0"
    assert contract.CONTRACT_SHA256 == "ec8918e717a892c1c14a820b4df03cd64fb8bf8810e55a7a73b9823065c5431b"
    assert list(contract.FEATURE_ORDER) == ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
                                            "thalach", "exang", "oldpeak", "slope", "ca", "thal"]


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_package_has_no_web_or_backend_imports():
    forbidden = ("fastapi", "starlette", "uvicorn", "backend", "src", "httpx")
    for py in PKG_DIR.rglob("*.py"):
        for mod in _imports(py):
            assert not mod.split(".")[0] in forbidden, f"{py.relative_to(ROOT)} imports {mod}"


def _run_isolated(code, cwd, extra_env=None, pythonpath=None):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "CARDIOVANTA_MODEL_REGISTRY")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if pythonpath:
        env["PYTHONPATH"] = os.pathsep.join(str(p) for p in pythonpath)
    env.update(extra_env or {})
    return subprocess.run([sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True, timeout=240)


def test_package_works_without_fastapi_and_outside_repo_cwd(tmp_path):
    code = (
        "import sys\n"
        "for m in ('fastapi', 'starlette', 'backend'): sys.modules[m] = None  # make them unimportable\n"
        "import cardiovanta_ml\n"
        "m = cardiovanta_ml.load_model('cardiovanta-lr13', '1.0.0')\n"
        "print(round(cardiovanta_ml.predict(%r, m)['probability'], 6))\n" % (HIGH_RISK,)
    )
    r = _run_isolated(code, cwd=tmp_path, pythonpath=[ROOT],
                      extra_env={"CARDIOVANTA_MODEL_REGISTRY": str(REGISTRY_ROOT)})
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "0.985791"


def test_contract_import_is_lightweight(tmp_path):
    code = ("import sys, cardiovanta_ml.contracts as c\n"
            "print(c.bundled_contract_sha256())\n"
            "print(any(m in sys.modules for m in ('sklearn', 'numpy', 'pandas', 'joblib')))\n")
    r = _run_isolated(code, cwd=tmp_path, pythonpath=[ROOT])
    assert r.returncode == 0, r.stderr
    digest, heavy = r.stdout.split()
    assert digest == contract.CONTRACT_SHA256 and heavy == "False"


def test_pyproject_declares_package_correctly():
    meta = tomllib.loads((PKG_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    project = meta["project"]
    assert project["name"] == "cardiovanta-ml" and project["version"] == cardiovanta_ml.__version__
    assert project["requires-python"] == ">=3.11,<3.13"  # R3: 3.12 production runtime, 3.11 local dev
    deps = " ".join(project["dependencies"])
    for dep in ("scikit-learn==1.9.1", "joblib==1.6.0", "pandas==3.0.6", "pydantic==2.10.4", "numpy==2.4.6",
                "scipy==1.17.1"):
        assert dep in deps
    assert "fastapi" not in deps.lower()
    assert project["optional-dependencies"]["test"] == ["pytest==9.1.1"]
    data = meta["tool"]["setuptools"]["package-data"]
    assert "feature_schema.v2.json" in data["cardiovanta_ml.contracts"]
    assert set(meta["tool"]["setuptools"]["packages"]) == {
        "cardiovanta_ml", "cardiovanta_ml.contracts", "cardiovanta_ml.inference", "cardiovanta_ml.registry"}


@pytest.mark.skipif(os.environ.get("CARDIOVANTA_RUN_INSTALL_TESTS") != "1",
                    reason="Builds and installs the package with pip (needs build backend); set CARDIOVANTA_RUN_INSTALL_TESTS=1")
def test_package_installs_and_resources_load_after_install(tmp_path):
    target = tmp_path / "site"
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(PKG_DIR)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (target / "cardiovanta_ml" / "contracts" / "feature_schema.v2.json").is_file()
    assert (target / "cardiovanta_ml" / "py.typed").is_file()
    code = (
        "import cardiovanta_ml, cardiovanta_ml.contracts as c\n"
        "from cardiovanta_ml.contracts import generated_features as g\n"
        "print(cardiovanta_ml.__file__)\n"
        "assert c.bundled_contract_sha256() == g.CONTRACT_SHA256\n"
        "m = cardiovanta_ml.load_model('cardiovanta-lr13', '1.0.0')\n"
        "print(round(cardiovanta_ml.predict(%r, m)['probability'], 6))\n" % (LOW_RISK,)
    )
    out = _run_isolated(code, cwd=tmp_path, pythonpath=[target],
                        extra_env={"CARDIOVANTA_MODEL_REGISTRY": str(REGISTRY_ROOT)})
    assert out.returncode == 0, out.stderr
    file_line, prob = out.stdout.split()
    assert Path(file_line).resolve().is_relative_to(target.resolve())  # the installed copy, not the repo
    assert prob == "0.016066"


# =============================================================================
# Registry: selection
# =============================================================================

def test_selects_exact_registered_model(model):
    assert (model.model_id, model.model_version) == (MODEL_ID, MODEL_VERSION)
    assert model.artifact_dir == (REGISTRY_ROOT / "model").resolve()
    assert model.entry_dir == (REGISTRY_ROOT / ENTRY_REL).resolve()
    assert model.metadata.model_classes == (0, 1)
    assert model.metadata.class_label_semantics == {0: "disease_present", 1: "disease_absent"}
    assert model.disease_label == 0
    assert model.metadata.outcome.mapping_status == "interim_legacy"
    assert model.package_metadata["package_version"] == "1.0.0"


@pytest.mark.parametrize("version", ["9.9.9", "1.0.1", "2.0.0"])
def test_unknown_version_rejected(version):
    with pytest.raises(ModelNotRegisteredError):
        load_model(MODEL_ID, version, registry_root=REGISTRY_ROOT)


@pytest.mark.parametrize("model_id,version", [
    ("unknown-model", "1.0.0"), (MODEL_ID, "latest"), (MODEL_ID, "1.0"), (MODEL_ID, "v1.0.0"),
    (MODEL_ID, "../1.0.0"), ("../models", "1.0.0"), (MODEL_ID, ""), ("Cardiovanta-LR13", "1.0.0"),
])
def test_invalid_or_unregistered_identity_rejected(model_id, version):
    with pytest.raises(ModelNotRegisteredError):
        load_model(model_id, version, registry_root=REGISTRY_ROOT)


def test_newer_directory_is_never_selected_implicitly(registry):
    shutil.copytree(registry / ENTRY_REL, registry / "models" / MODEL_ID / "9.9.9")
    loaded = load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)
    assert loaded.model_version == "1.0.0"
    with pytest.raises(MetadataError, match="registered at"):  # the 9.9.9 copy still declares 1.0.0
        load_model(MODEL_ID, "9.9.9", registry_root=registry)


def test_registry_root_must_be_explicit(monkeypatch):
    monkeypatch.delenv("CARDIOVANTA_MODEL_REGISTRY", raising=False)
    with pytest.raises(RegistryConfigurationError):
        load_model(MODEL_ID, MODEL_VERSION)
    with pytest.raises(RegistryConfigurationError, match="absolute"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root="artifacts")


def test_all_registry_errors_share_base_class():
    for exc in (ModelNotRegisteredError, MetadataError, IntegrityError, ArtifactPathError, ContractMismatchError,
                OutcomeMappingError, ModelCompatibilityError, RegistryConfigurationError):
        assert issubclass(exc, RegistryError)


# =============================================================================
# Registry: metadata
# =============================================================================

def test_missing_metadata_rejected(registry, no_deserialize):
    _meta_path(registry).unlink()
    with pytest.raises(MetadataError, match="not found"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_malformed_metadata_rejected(registry, no_deserialize):
    _meta_path(registry).write_text('{"model_id": ', encoding="utf-8")
    with pytest.raises(MetadataError, match="Malformed"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


@pytest.mark.parametrize("mutate,match", [
    (lambda m: m.update(surprise=True), "unsupported key"),
    (lambda m: m.pop("calibration"), "missing required key"),
    (lambda m: m.update(model_id="other-model"), "registered at"),
    (lambda m: m.update(model_version="1.0.1"), "registered at"),
    (lambda m: m.update(registry_schema_version="0.9"), "registry_schema_version"),
    (lambda m: m["artifacts"].pop("shap_background"), "missing required role"),
    (lambda m: m["artifacts"].update(extra_role="x.bin"), "unsupported role"),
    (lambda m: m.update(checksum_manifest_sha256="not-a-hash"), "SHA-256"),
    (lambda m: m["runtime"].pop("sklearn_version"), "sklearn_version"),
    (lambda m: m.update(feature_order=["age", "age"]), "unique"),
])
def test_invalid_metadata_rejected(registry, no_deserialize, mutate, match):
    _edit_metadata(registry, mutate)
    with pytest.raises(MetadataError, match=match):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


# =============================================================================
# Registry: outcome mapping
# =============================================================================

@pytest.mark.parametrize("mutate,match", [
    (lambda m: m["outcome_semantics"].update(disease_present_label=2), "not one of model_classes"),
    (lambda m: m["outcome_semantics"].update(disease_present_label=True), "expected int"),
    (lambda m: m["outcome_semantics"].update(disease_present_label=1), "contradicts class_label_semantics"),
    (lambda m: m["outcome_semantics"].pop("disease_present_label"), "missing required key"),
    (lambda m: m.update(class_label_semantics={"0": "disease_present", "1": "disease_present"}), "exactly one"),
    (lambda m: m.update(class_label_semantics={"0": "disease_present"}), "do not match model_classes"),
    (lambda m: m["outcome_semantics"].update(outcome="healthy"), "not the contract outcome"),
    (lambda m: m["outcome_semantics"].update(contract_version="1.0.0"), "different contract version"),
    (lambda m: m["outcome_semantics"].update(mapping_status="explicit"), "contradicts the contract"),
    (lambda m: m["outcome_semantics"].update(mapping_status="guessed"), "mapping_status"),
])
def test_outcome_mapping_errors_rejected(registry, no_deserialize, mutate, match):
    _edit_metadata(registry, mutate)
    with pytest.raises(OutcomeMappingError, match=match):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_consistently_flipped_label_contradicting_contract_is_rejected(registry, no_deserialize):
    """Even an internally consistent metadata flip (label 1 = disease) must agree with the contract record."""
    def flip(m):
        m["class_label_semantics"] = {"0": "disease_absent", "1": "disease_present"}
        m["outcome_semantics"]["disease_present_label"] = 1
    _edit_metadata(registry, flip)
    with pytest.raises(OutcomeMappingError, match="contract records 0"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_interim_mapping_requires_contract_record(registry, no_deserialize):
    """A new model cannot claim an interim legacy mapping the contract does not corroborate."""
    new_entry = registry / "models" / "cardiovanta-new" / "1.0.0"
    shutil.copytree(registry / ENTRY_REL, new_entry)
    meta = json.loads((new_entry / "metadata.json").read_text())
    meta["model_id"] = "cardiovanta-new"
    meta["explanation"]["associated_model"] = "cardiovanta-new@1.0.0"
    (new_entry / "metadata.json").write_text(json.dumps(meta))
    with pytest.raises(OutcomeMappingError, match="does not record"):
        load_model("cardiovanta-new", "1.0.0", registry_root=registry)


# =============================================================================
# Registry: integrity (all before deserialization)
# =============================================================================

@pytest.mark.parametrize("name", sorted(ORIGINAL_SHA256))
def test_missing_artifact_rejected(registry, no_deserialize, name):
    (registry / "model" / name).unlink()
    with pytest.raises(IntegrityError, match="not found"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


@pytest.mark.parametrize("name", sorted(ORIGINAL_SHA256))
def test_modified_artifact_rejected_before_deserialization(registry, no_deserialize, name):
    path = registry / "model" / name
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(IntegrityError, match="SHA-256 mismatch"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)
    assert no_deserialize == []


def test_tampered_manifest_rejected(registry, no_deserialize):
    manifest = registry / ENTRY_REL / "checksums.sha256"
    manifest.write_text(manifest.read_text().replace("18e2268e", "00000000"), encoding="utf-8")
    with pytest.raises(IntegrityError, match="does not match the SHA-256 recorded"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_manifest_missing_or_unexpected_entries_rejected(registry, no_deserialize):
    lines = [f"{h}  {n}" for n, h in sorted(ORIGINAL_SHA256.items()) if n != "shap_background.json"]
    _rewrite_manifest(registry, lines)
    with pytest.raises(IntegrityError, match="missing from checksum manifest"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)
    lines = [f"{h}  {n}" for n, h in sorted(ORIGINAL_SHA256.items())] + ["0" * 64 + "  extra.bin"]
    _rewrite_manifest(registry, lines)
    with pytest.raises(IntegrityError, match="Unexpected artifacts"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_consistently_rewritten_manifest_still_fails_on_real_hash(registry, no_deserialize):
    path = registry / "model" / "model.joblib"
    path.write_bytes(path.read_bytes() + b"x")
    lines = [f"{h}  {n}" for n, h in sorted(ORIGINAL_SHA256.items())]  # original (now wrong) model hash
    _rewrite_manifest(registry, lines)
    with pytest.raises(IntegrityError, match="SHA-256 mismatch for artifact model.joblib"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


@pytest.mark.parametrize("mutate", [
    lambda m: m.update(artifact_directory="../outside"),
    lambda m: m.update(artifact_directory="/etc"),
    lambda m: m.update(artifact_directory="C:/Windows"),
    lambda m: m.update(artifact_directory="model/../../x"),
    lambda m: m["artifacts"].update(model="../model/model.joblib"),
    lambda m: m["artifacts"].update(model="sub/model.joblib"),
    lambda m: m["artifacts"].update(model="..\\model.joblib"),
    lambda m: m.update(checksum_manifest="../checksums.sha256"),
    lambda m: m.update(model_card="/abs/card.md"),
])
def test_path_traversal_rejected(registry, no_deserialize, mutate):
    _edit_metadata(registry, mutate)
    with pytest.raises(ArtifactPathError):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_manifest_with_traversing_file_name_rejected(registry, no_deserialize):
    _rewrite_manifest(registry, [f"{ORIGINAL_SHA256['model.joblib']}  ../model.joblib"])
    with pytest.raises(ArtifactPathError):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


# =============================================================================
# Registry: contract and model compatibility
# =============================================================================

@pytest.mark.parametrize("mutate,match", [
    (lambda m: m["feature_contract"].update(version="1.9.0"), "contract v1.9.0"),
    (lambda m: m["feature_contract"].update(sha256="0" * 64), "SHA-256 does not match"),
    (lambda m: m["feature_contract"].update(name="other.contract"), "registered against contract"),
    (lambda m: m.update(feature_order=list(reversed(m["feature_order"]))), "feature order"),
])
def test_feature_contract_mismatch_rejected(registry, no_deserialize, mutate, match):
    _edit_metadata(registry, mutate)
    with pytest.raises(ContractMismatchError, match=match):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_model_class_mismatch_rejected(registry):
    def classes(m):
        m["model_classes"] = [0, 2]
        m["class_label_semantics"] = {"0": "disease_present", "2": "disease_absent"}
    _edit_metadata(registry, classes)
    with pytest.raises(ModelCompatibilityError, match="classes"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_runtime_version_mismatch_rejected_before_deserialization(registry, no_deserialize):
    _edit_metadata(registry, lambda m: m["runtime"].update(sklearn_version="1.8.0"))
    with pytest.raises(ModelCompatibilityError, match="refusing to deserialize"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


def test_explanation_association_mismatch_rejected(registry):
    _edit_metadata(registry, lambda m: m["explanation"].update(associated_model="other-model@1.0.0"))
    with pytest.raises(ModelCompatibilityError, match="associated"):
        load_model(MODEL_ID, MODEL_VERSION, registry_root=registry)


# =============================================================================
# Registry: single load
# =============================================================================

def test_single_load_per_process(fresh_cache, monkeypatch):
    real = joblib.load
    calls = []
    monkeypatch.setattr(joblib, "load", lambda *a, **k: calls.append(Path(a[0]).name) or real(*a, **k))
    first = load_model(MODEL_ID, MODEL_VERSION, registry_root=REGISTRY_ROOT)
    second = load_model(MODEL_ID, MODEL_VERSION, registry_root=REGISTRY_ROOT)
    assert first is second
    assert sorted(calls) == ["explanation_model.joblib", "model.joblib"]  # each artifact deserialized once
    from backend.app.main import app
    with TestClient(app):
        engine_a = app.state.inference_engine
    with TestClient(app):
        engine_b = app.state.inference_engine
    assert engine_a.loaded is engine_b.loaded is first
    assert sorted(calls) == ["explanation_model.joblib", "model.joblib"]


def test_backend_startup_uses_registry_not_legacy_loader():
    src = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "load_model(" in src and "ModelLoader" not in src
    from backend.app.core.config import settings
    assert (settings.MODEL_ID, settings.MODEL_VERSION) == (MODEL_ID, MODEL_VERSION)


# =============================================================================
# Inference parity (R0.3 golden behaviour)
# =============================================================================

def _assert_close(a, b, path="body"):
    if isinstance(a, float) or isinstance(b, float):
        assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), path
    elif isinstance(a, dict):
        assert set(a) == set(b), path
        for k in a:
            _assert_close(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_close(x, y, f"{path}[{i}]")
    else:
        assert a == b, path


def test_api_responses_match_pre_r2_snapshot():
    snapshot = json.loads((Path(__file__).parent / "fixtures" / "pre_r2_api_snapshot.json").read_text())
    from backend.app.main import app
    with TestClient(app) as c:
        for name, payload in SNAPSHOT_INPUTS.items():
            for threshold in (None, 0.5):
                url = "/api/v1/predict" + ("" if threshold is None else f"?threshold={threshold}")
                r = c.post(url, json=payload)
                expected = snapshot[f"{name}|{threshold}"]
                assert r.status_code == expected["status"]
                _assert_close(r.json(), expected["body"], name)


def test_golden_disease_probabilities(model):
    assert predict(HIGH_RISK, model)["probability"] == pytest.approx(0.985790929, abs=1e-6)
    assert predict(LOW_RISK, model)["probability"] == pytest.approx(0.016065906, abs=1e-6)
    assert round(predict(HIGH_RISK, model)["probability"], 4) == 0.9858
    assert round(predict(LOW_RISK, model)["probability"], 4) == 0.0161


def test_package_matches_independent_computation(model):
    import pandas as pd
    raw = joblib.load(REGISTRY_ROOT / "model" / "model.joblib")
    for profile in (HIGH_RISK, LOW_RISK):
        X = pd.DataFrame([{k: float(profile[k]) for k in contract.FEATURE_ORDER}])
        expected = raw.predict_proba(X)[0, list(raw.classes_).index(0)]
        assert predict(profile, model)["probability"] == pytest.approx(expected, abs=1e-15)


def test_probability_column_follows_declared_label(model):
    """The column is chosen from the declared label, not hard-coded: declaring label 1 selects P(label 1)."""
    flipped_outcome = dataclasses.replace(model.metadata.outcome, disease_present_label=1)
    flipped = dataclasses.replace(model, metadata=dataclasses.replace(model.metadata, outcome=flipped_outcome))
    p0 = InferenceEngine(model).predict(HIGH_RISK)["probability"]
    p1 = InferenceEngine(flipped).predict(HIGH_RISK)["probability"]
    assert p0 + p1 == pytest.approx(1.0, abs=1e-12)
    e0 = InferenceEngine(model).explain(HIGH_RISK)["decision_function_log_odds"]
    e1 = InferenceEngine(flipped).explain(HIGH_RISK)["decision_function_log_odds"]
    assert e0 == pytest.approx(-e1, abs=1e-12)


def test_threshold_and_explanation_orientation(model):
    engine = InferenceEngine(model)
    assert engine.predict(HIGH_RISK, apply_threshold=0.5)["class"] == 1
    assert engine.predict(LOW_RISK, apply_threshold=0.5)["class"] == 0
    for exp in (engine.explain(HIGH_RISK), engine.explain_shap_equivalent(HIGH_RISK)):
        assert exp["decision_function_log_odds"] > 0
        for feature in ("exang", "oldpeak", "ca"):
            assert exp["contributions"][feature] > 0
    assert engine.explain(LOW_RISK)["decision_function_log_odds"] < 0


def test_legacy_wrappers_delegate_to_package():
    from src.inference.outcome import LEGACY_PACKAGE_DISEASE_LABEL
    from src.inference.predict import InferenceEngine as LegacyEngine
    from cardiovanta_ml.inference.outcome import LEGACY_PACKAGE_DISEASE_LABEL as pkg_map
    assert LEGACY_PACKAGE_DISEASE_LABEL is pkg_map
    engine = LegacyEngine()
    assert isinstance(engine, InferenceEngine)
    assert engine.predict(HIGH_RISK)["probability"] == pytest.approx(0.985790929, abs=1e-6)
    with pytest.raises(ValueError, match="registered artifact directory"):
        LegacyEngine(model_dir=ROOT / "somewhere-else")


# =============================================================================
# Artifacts untouched and deployment packaging
# =============================================================================

def test_original_artifacts_unchanged_and_manifest_matches():
    for name, digest in ORIGINAL_SHA256.items():
        assert hashlib.sha256((REGISTRY_ROOT / "model" / name).read_bytes()).hexdigest() == digest, name
    manifest = (REGISTRY_ROOT / ENTRY_REL / "checksums.sha256").read_text(encoding="ascii")
    entries = dict(reversed(line.split("  ")) for line in manifest.splitlines() if line and not line.startswith("#"))
    assert entries == ORIGINAL_SHA256
    legacy_manifest = json.loads((ROOT / "configs" / "artifact_hashes.json").read_text())
    assert {Path(k).name: v for k, v in legacy_manifest.items()} == ORIGINAL_SHA256


def test_model_card_is_present_and_honest():
    card = (REGISTRY_ROOT / ENTRY_REL / "model_card.md").read_text(encoding="utf-8")
    for phrase in ("not clinically validated", "Label 0 = disease present", "not an independent test set",
                   "No external validation", "does NOT decompose", "not established in project records"):
        assert phrase.lower() in card.lower(), phrase


def _vercel_bundle(dest):
    """Copy what the Vercel Python function would contain: includeFiles globs + api/, minus .vercelignore."""
    vercel = json.loads((ROOT / "vercel.json").read_text())
    globs = vercel["functions"]["api/**/*.py"]["includeFiles"].strip("{}").split(",")
    ignore = [l.strip() for l in (ROOT / ".vercelignore").read_text().splitlines() if l.strip()]
    tops = [g.split("/")[0] for g in globs] + ["api"]

    def ignored(rel):
        return any(fnmatch.fnmatch(part, pat) for part in rel.parts for pat in ignore)

    for top in tops:
        for path in (ROOT / top).rglob("*"):
            rel = path.relative_to(ROOT)
            if path.is_file() and not ignored(rel):
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest / rel)
    return tops


def test_vercel_bundle_contains_package_and_serves_predictions(tmp_path):
    bundle = tmp_path / "bundle"
    tops = _vercel_bundle(bundle)
    assert "cardiovanta_ml" in tops, "vercel.json includeFiles must ship the ML package"
    assert (bundle / "cardiovanta_ml" / "contracts" / "feature_schema.v2.json").is_file()
    assert not (bundle / "data").exists() and not (bundle / "contracts").exists()
    code = (
        "import sys, os\n"
        "sys.path.insert(0, os.getcwd())\n"
        "from api.index import app\n"
        "from fastapi.testclient import TestClient\n"
        "with TestClient(app) as c:\n"
        "    r = c.post('/api/v1/predict', json=%r)\n"
        "    print('RESULT', r.status_code, round(r.json()['prediction']['probability'], 4))\n" % (HIGH_RISK,)
    )
    r = _run_isolated(code, cwd=bundle)
    assert r.returncode == 0, r.stderr[-2000:]
    results = [line for line in r.stdout.splitlines() if line.startswith("RESULT ")]  # app logs JSON to stdout too
    assert results == ["RESULT 200 0.9858"]
