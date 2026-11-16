"""
Portable (NumPy-only) serving: cardiovanta-lr13@1.1.1 is a JSON export of 1.1.0's fitted parameters.

These tests prove that
- 1.1.1 reproduces 1.1.0's probabilities and both explanations on many inputs;
- the registry verifies and validates portable artifacts and refuses malformed ones;
- the API starts and serves the golden values with scikit-learn, SciPy, pandas and joblib blocked from import,
  which is how the Vercel function runs (api/requirements.txt does not install them).
Synthetic inputs only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from backend.tests.served_model import GOLDEN, SERVED_VERSION
from cardiovanta_ml import InferenceEngine, clear_model_cache, load_model
from cardiovanta_ml.inference import portable as P
from cardiovanta_ml.registry.exceptions import IntegrityError, MetadataError, ModelCompatibilityError

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "artifacts"
MODEL_ID = "cardiovanta-lr13"
HIGH = dict(age=67.0, sex=1, cp=0, trestbps=160.0, chol=286.0, fbs=0, restecg=0,
            thalach=108.0, exang=1, oldpeak=3.0, slope=1, ca=3, thal=3)


@pytest.fixture(scope="module")
def engines():
    ref = InferenceEngine(load_model(MODEL_ID, "1.1.0", registry_root=REGISTRY_ROOT))
    port = InferenceEngine(load_model(MODEL_ID, "1.1.1", registry_root=REGISTRY_ROOT))
    return ref, port


def _profiles(n: int):
    rng = np.random.default_rng(7)
    for _ in range(n):
        yield dict(age=float(rng.uniform(25, 85)), sex=int(rng.integers(0, 2)), cp=int(rng.integers(0, 4)),
                   trestbps=float(rng.uniform(90, 200)), chol=float(rng.uniform(120, 450)), fbs=int(rng.integers(0, 2)),
                   restecg=int(rng.integers(0, 3)), thalach=float(rng.uniform(70, 205)), exang=int(rng.integers(0, 2)),
                   oldpeak=float(rng.uniform(0, 6)), slope=int(rng.integers(0, 3)), ca=int(rng.integers(0, 5)),
                   thal=int(rng.integers(0, 4)))


def test_served_model_is_the_portable_export():
    assert SERVED_VERSION == "1.1.1"
    meta = load_model(MODEL_ID, "1.1.1", registry_root=REGISTRY_ROOT).metadata
    assert meta.serialization == "portable_json" and meta.raw["provenance"]["exported_from"] == "cardiovanta-lr13@1.1.0"


def test_golden_values_equal_1_1_0(engines):
    _, port = engines
    assert port._portable
    assert port.predict(dict(HIGH))["probability"] == pytest.approx(GOLDEN["1.1.0"]["HIGH"], abs=1e-9)


def test_portable_predictions_and_explanations_match_scikit_learn(engines):
    ref, port = engines
    for profile in _profiles(400):
        a, b = ref.predict(dict(profile)), port.predict(dict(profile))
        assert abs(a["probability"] - b["probability"]) <= 1e-12
        assert a["outside_development_range"] == b["outside_development_range"]
        la, lb = ref.explain(dict(profile)), port.explain(dict(profile))
        assert la["intercept"] == lb["intercept"] and la["decision_function_log_odds"] == pytest.approx(lb["decision_function_log_odds"], abs=1e-12)
        assert la["contributions"] == pytest.approx(lb["contributions"], abs=1e-12)
        sa, sb = ref.explain_shap_equivalent(dict(profile)), port.explain_shap_equivalent(dict(profile))
        assert sa["expected_value"] == sb["expected_value"]
        assert sa["contributions"] == pytest.approx(sb["contributions"], abs=1e-12)


def test_threshold_and_validation_behave_the_same(engines):
    ref, port = engines
    for t in (0.3, 0.5, 0.9):
        assert ref.predict(dict(HIGH), apply_threshold=t)["class"] == port.predict(dict(HIGH), apply_threshold=t)["class"]
    for bad in (dict(HIGH, cp=9), {k: v for k, v in HIGH.items() if k != "age"}, dict(HIGH, extra=1)):
        with pytest.raises(ValueError):
            port.predict(bad)


# --- registry integrity for portable artifacts -------------------------------------------------------------

@pytest.fixture
def tmp_registry(tmp_path):
    root = tmp_path / "artifacts"
    shutil.copytree(REGISTRY_ROOT / "model-1.1.1", root / "model-1.1.1")
    shutil.copytree(REGISTRY_ROOT / "models" / MODEL_ID / "1.1.1", root / "models" / MODEL_ID / "1.1.1")
    clear_model_cache()
    yield root
    clear_model_cache()


def test_tampered_portable_parameters_are_refused(tmp_registry):
    path = tmp_registry / "model-1.1.1" / "model.json"
    doc = json.loads(path.read_text())
    doc["calibrator"]["a"] *= 1.01
    path.write_text(json.dumps(doc, indent=2) + "\n")
    with pytest.raises(IntegrityError):
        load_model(MODEL_ID, "1.1.1", registry_root=tmp_registry)


def test_unknown_serialization_is_refused(tmp_registry):
    path = tmp_registry / "models" / MODEL_ID / "1.1.1" / "metadata.json"
    meta = json.loads(path.read_text())
    meta["runtime"]["serialization"] = "pickle"
    path.write_text(json.dumps(meta, indent=2) + "\n")
    with pytest.raises(MetadataError, match="serialization"):
        load_model(MODEL_ID, "1.1.1", registry_root=tmp_registry)


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(format="other.format"),
    lambda d: d.update(kind="random_forest"),
    lambda d: d["estimator"]["logistic_regression"]["coef"].pop(),
    lambda d: d["estimator"]["preprocessor"]["continuous"]["scale"].__setitem__(0, 0.0),
    lambda d: d["estimator"]["preprocessor"]["feature_names_out"].reverse(),
    lambda d: d["calibrator"].update(method="isotonic"),
])
def test_malformed_portable_documents_are_rejected(mutate):
    doc = json.loads((REGISTRY_ROOT / "model-1.1.1" / "model.json").read_text())
    mutate(doc)
    with pytest.raises(P.PortableFormatError):
        P.load_portable(doc)


def test_portable_load_failure_is_a_compatibility_error(tmp_registry, monkeypatch):
    monkeypatch.setattr(P, "load_portable", lambda doc: (_ for _ in ()).throw(P.PortableFormatError("bad")))
    with pytest.raises(ModelCompatibilityError):
        load_model(MODEL_ID, "1.1.1", registry_root=tmp_registry)


# --- the API runs without scikit-learn, SciPy, pandas or joblib ---------------------------------------------

_NO_SKLEARN_PROBE = r"""
import importlib.abc, json, os, sys
BLOCKED = ("sklearn", "scipy", "pandas", "joblib", "threadpoolctl")
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError(f"{name} is not installed in the serving function")
        return None
sys.meta_path.insert(0, Block())
sys.path.insert(0, os.getcwd())
from api.index import app
from fastapi.testclient import TestClient
import backend.app.core.prediction_availability as pa
pa.current_availability = lambda: pa.PredictionAvailability(enabled=True, notice=pa.DEFAULT_NOTICE)
with TestClient(app) as c:
    r = c.post("/api/v1/predict", json=%r)
    body = r.json()
    print("PROBE " + json.dumps({"status": r.status_code, "p": body["prediction"]["probability"],
        "version": body["metadata"]["package_version"], "why": sorted(body["shap_equivalent_explanation"]["contributions"]),
        "loaded": sorted(m for m in sys.modules if m.split(".")[0] in BLOCKED)}))
"""


def test_api_serves_without_scikit_learn_scipy_or_pandas():
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "MODEL_ID", "MODEL_VERSION", "MODEL_REGISTRY_ROOT")}
    r = subprocess.run([sys.executable, "-c", _NO_SKLEARN_PROBE % (HIGH,)], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=300)
    lines = [l[6:] for l in r.stdout.splitlines() if l.startswith("PROBE ")]
    assert r.returncode == 0 and lines, r.stderr[-3000:]
    probe = json.loads(lines[0])
    assert probe["status"] == 200 and probe["version"] == SERVED_VERSION
    assert probe["p"] == pytest.approx(GOLDEN[SERVED_VERSION]["HIGH"], abs=1e-9)
    assert len(probe["why"]) == 13
    assert probe["loaded"] == []


def test_serving_requirements_do_not_install_the_scientific_stack():
    reqs = (ROOT / "api" / "requirements.txt").read_text(encoding="utf-8").lower()
    pinned = {line.split("==")[0].strip() for line in reqs.splitlines() if "==" in line and not line.startswith("#")}
    assert "numpy" in pinned
    assert not pinned & {"scikit-learn", "scipy", "pandas", "joblib", "threadpoolctl"}
