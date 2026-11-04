"""
Phase 10 production-incident containment: regression tests for the prediction-availability switch.

These tests use the real, shipped switch ``configs/prediction_service.json`` (the root conftest opens
the gate only for tests without the ``prediction_containment`` marker). They prove that while
predictions are unavailable:
- every direct ``POST /api/v1/predict`` gets the structured 503, before body validation;
- no probability is returned and the model is never called;
- health, startup model verification and unrelated routes are unaffected;
- the switch is fail-safe, not environment-controlled, and shared with the web app.
Synthetic inputs only.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.core import prediction_availability as pa
from backend.app.main import app

pytestmark = pytest.mark.prediction_containment

ROOT = Path(__file__).resolve().parents[2]
SWITCH = ROOT / "configs" / "prediction_service.json"
NOTICE = ("CardioVanta predictions are temporarily unavailable while we verify the prediction service. "
          "No risk estimate can currently be generated.")
UNAVAILABLE = {"detail": NOTICE, "code": "predictions_temporarily_unavailable", "predictions_available": False}

HIGH = dict(age=67.0, sex=1, cp=0, trestbps=160.0, chol=286.0, fbs=0, restecg=0,
            thalach=108.0, exang=1, oldpeak=3.0, slope=1, ca=3, thal=3)
LOW = dict(age=37.0, sex=0, cp=2, trestbps=120.0, chol=200.0, fbs=0, restecg=1,
           thalach=187.0, exang=0, oldpeak=0.0, slope=2, ca=0, thal=2)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


# ---- the shipped state ------------------------------------------------------------------------------

def test_shipped_switch_disables_predictions():
    raw = json.loads(SWITCH.read_text(encoding="utf-8"))
    assert raw["predictions_enabled"] is False
    assert raw["notice"] == NOTICE
    assert pa.AVAILABILITY_FILE == SWITCH
    assert pa.current_availability() == pa.PredictionAvailability(enabled=False, notice=NOTICE)


# ---- direct API requests are blocked ------------------------------------------------------------------

@pytest.mark.parametrize("label, kwargs", [
    ("high-risk profile", {"json": HIGH}),
    ("low-risk profile", {"json": LOW}),
    ("with threshold", {"json": HIGH, "params": {"threshold": 0.5}}),
    ("invalid body", {"json": {"age": "not a number"}}),
    ("empty object", {"json": {}}),
    ("no body", {}),
    ("non-JSON body", {"content": b"age=67", "headers": {"Content-Type": "text/plain"}}),
])
def test_direct_predict_requests_get_structured_503(client, label, kwargs):
    r = client.post("/api/v1/predict", **kwargs)
    assert r.status_code == 503, label
    assert r.json() == UNAVAILABLE
    assert r.headers["cache-control"] == "no-store"


def test_no_probability_or_prediction_fields_while_disabled(client):
    for profile in (HIGH, LOW):
        r = client.post("/api/v1/predict", json=profile)
        body = r.json()
        found = set(_keys(body))
        assert not found & {"prediction", "probability", "explanation", "shap_equivalent_explanation",
                            "development_range_warning", "metadata", "outcome"}
        # neither the correct nor the inverted golden value appears anywhere in the response
        for value in ("0.98579", "0.01606", "0.01420", "0.98393"):
            assert value not in r.text


def test_model_is_never_called_while_disabled(client, monkeypatch):
    engine = app.state.inference_engine
    calls = []
    for name in ("predict", "explain", "explain_shap_equivalent"):
        monkeypatch.setattr(engine, name, lambda *a, _n=name, **k: calls.append(_n))
    assert client.post("/api/v1/predict", json=HIGH).status_code == 503
    assert calls == []


def test_refusal_is_logged_without_input_values(client, caplog):
    with caplog.at_level(logging.WARNING):
        client.post("/api/v1/predict", json=HIGH)
    refused = [r for r in caplog.records if getattr(r, "event_type", None) == "prediction_refused"]
    assert len(refused) == 1 and refused[0].status_code == 503
    text = " ".join(r.getMessage() + " " + json.dumps(r.__dict__, default=str) for r in caplog.records)
    for raw_value in ("286.0", "160.0", "108.0"):
        assert raw_value not in text


# ---- unrelated behaviour is unchanged ----------------------------------------------------------------

def test_health_and_verified_model_load_unaffected(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "CardioVanta"}
    # startup still loads and SHA-256-verifies the unchanged registered model; the engine itself is correct
    engine = app.state.inference_engine
    assert engine.loaded.metadata.qualified_name == "cardiovanta-lr13@1.0.0"
    assert engine.predict(dict(HIGH))["probability"] == pytest.approx(0.985790929, abs=1e-6)


def test_unrelated_routes_unaffected(client):
    assert client.get("/api/v1/predict").status_code == 405       # method routing unchanged
    assert client.get("/api/v1/does-not-exist").status_code == 404


# ---- reversibility ------------------------------------------------------------------------------------

def test_reenabling_the_switch_restores_the_unchanged_prediction_path(client, monkeypatch):
    monkeypatch.setattr(pa, "current_availability", lambda: pa.PredictionAvailability(enabled=True, notice=NOTICE))
    hi, lo = (client.post("/api/v1/predict", json=p) for p in (HIGH, LOW))
    assert hi.status_code == lo.status_code == 200
    assert hi.json()["prediction"]["probability"] == pytest.approx(0.985790929, abs=1e-6)
    assert lo.json()["prediction"]["probability"] == pytest.approx(0.016065906, abs=1e-6)
    assert hi.json()["prediction"]["outcome"] == "significant_obstructive_cad_present"


# ---- the switch is fail-safe ----------------------------------------------------------------------------

@pytest.mark.parametrize("content, expected", [
    (None, False),                                         # file missing
    ("{not json", False),                                  # malformed
    ("", False),                                           # empty file
    ("[true]", False),                                     # not an object
    ('{"notice": "x"}', False),                            # key missing
    ('{"predictions_enabled": "true"}', False),            # string, not boolean
    ('{"predictions_enabled": 1}', False),                 # number, not boolean
    ('{"predictions_enabled": null}', False),
    ('{"predictions_enabled": false}', False),
    ('{"predictions_enabled": true}', True),               # the only enabling value
])
def test_switch_is_fail_safe(tmp_path, content, expected):
    path = tmp_path / "prediction_service.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert pa.load_prediction_availability(path).enabled is expected


@pytest.mark.parametrize("notice", [None, "", "   ", 42])
def test_missing_or_invalid_notice_falls_back_to_default(tmp_path, notice):
    path = tmp_path / "prediction_service.json"
    path.write_text(json.dumps({"predictions_enabled": False, "notice": notice}), encoding="utf-8")
    assert pa.load_prediction_availability(path).notice == pa.DEFAULT_NOTICE == NOTICE


def test_switch_is_not_environment_controlled():
    import ast
    tree = ast.parse(Path(pa.__file__).read_text(encoding="utf-8"))
    imported = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    imported |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
           {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not imported & {"os", "environ", "getenv", "dotenv"}
    assert not used & {"environ", "getenv", "settings"}
    from backend.app.core.config import settings
    assert not [f for f in type(settings).model_fields if "predict" in f.lower() or "avail" in f.lower()]


def test_web_app_reads_the_same_switch():
    ts = (ROOT / "src" / "lib" / "predictionAvailability.ts").read_text(encoding="utf-8")
    assert 'from "../../configs/prediction_service.json"' in ts
    assert (ROOT / "src" / "lib" / "../../configs/prediction_service.json").resolve() == SWITCH.resolve()
    assert NOTICE in ts and "predictions_enabled === true" in ts
