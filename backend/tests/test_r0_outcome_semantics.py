"""
R0.3 semantic regression tests: disease-positive outcome orientation.

Every patient profile here is SYNTHETIC and hand-written. No dataset rows are read
(``data/raw/heart.csv`` is never opened). Expected values are recomputed
independently from the frozen artifacts, not taken from the engine under test.

Encoding of the frozen model's inputs (Kaggle heart.csv encoding):
  cp: 0 = asymptomatic, 1 = atypical, 2 = non-anginal, 3 = typical angina
      (verified, Phase 17 KAGGLE_CP_TO_CANONICAL)
  ca: number of major vessels coloured by fluoroscopy (0-3; 4 = Kaggle sentinel)
"""
import json
import logging
import math
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.model_loader import ModelLoader
from src.inference.outcome import (
    LEGACY_PACKAGE_DISEASE_LABEL,
    OUTCOME_ID,
    disease_label_index,
    disease_log_odds_sign,
    outcome_mapping_source,
    resolve_disease_label,
)

ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = ROOT / "artifacts" / "model"

# Hand-checked synthetic fixtures.
# HIGH: older man, asymptomatic chest pain (the highest-prevalence presentation in
#   the source cohort), hypertension, exercise angina, 3.0 mm ST depression, flat
#   slope, 3 diseased vessels, low peak heart rate. Every input is a textbook
#   adverse finding.
HIGH_RISK = dict(age=67.0, sex=1, cp=0, trestbps=160.0, chol=286.0, fbs=0, restecg=0,
                 thalach=108.0, exang=1, oldpeak=3.0, slope=1, ca=3, thal=3)
# LOW: young woman, non-anginal pain, normal BP, high peak heart rate, no exercise
#   angina, no ST depression, 0 vessels.
LOW_RISK = dict(age=37.0, sex=0, cp=2, trestbps=120.0, chol=200.0, fbs=0, restecg=1,
                thalach=187.0, exang=0, oldpeak=0.0, slope=2, ca=0, thal=2)

# Pinned values (computed from the frozen model.joblib, sha256 18e2268e...).
# Before R0.3 the API returned 0.014209 for HIGH and 0.983934 for LOW (inverted).
GOLDEN_P_DISEASE = {"HIGH": 0.985790929, "LOW": 0.016065906}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def artifacts():
    schema = json.loads((MODEL_DIR / "feature_schema.json").read_text())
    return {
        "model": joblib.load(MODEL_DIR / "model.joblib"),
        "explanation_model": joblib.load(MODEL_DIR / "explanation_model.joblib"),
        "order": schema["feature_order"],
    }


def _frame(profile, order):
    return pd.DataFrame([{k: float(profile[k]) for k in order}])


def _post(client, profile, threshold=None):
    url = "/api/v1/predict" + (f"?threshold={threshold}" if threshold is not None else "")
    r = client.post(url, json=profile)
    assert r.status_code == 200, r.text
    return r.json()


# --- 1. High-risk > low-risk ---------------------------------------------------

def test_high_risk_has_higher_disease_probability_than_low_risk(client):
    p_high = _post(client, HIGH_RISK)["prediction"]["probability"]
    p_low = _post(client, LOW_RISK)["prediction"]["probability"]
    assert p_high > p_low
    # Margins are wide: both fixtures are extreme, so P(disease) should be
    # unambiguous. The inverted pre-R0.3 output (0.014 / 0.984) fails both.
    assert p_high > 0.9
    assert p_low < 0.1


def test_golden_disease_probabilities_are_pinned(client):
    assert _post(client, HIGH_RISK)["prediction"]["probability"] == pytest.approx(GOLDEN_P_DISEASE["HIGH"], abs=1e-6)
    assert _post(client, LOW_RISK)["prediction"]["probability"] == pytest.approx(GOLDEN_P_DISEASE["LOW"], abs=1e-6)


def test_api_probability_equals_independent_disease_column(client, artifacts):
    """API probability == predict_proba[:, index of label 0] computed directly here."""
    model = artifacts["model"]
    assert list(model.classes_) == [0, 1]
    disease_col = list(model.classes_).index(0)
    for profile in (HIGH_RISK, LOW_RISK):
        expected = model.predict_proba(_frame(profile, artifacts["order"]))[0, disease_col]
        assert _post(client, profile)["prediction"]["probability"] == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("feature,low_value,high_value", [
    ("exang", 0, 1),          # exercise angina present
    ("oldpeak", 0.0, 3.0),    # more ST depression
    ("ca", 0, 3),             # more diseased vessels
    ("thalach", 180.0, 110.0),  # lower peak heart rate
    ("cp", 2, 0),             # non-anginal -> asymptomatic
])
def test_single_adverse_change_raises_disease_probability(client, feature, low_value, high_value):
    base = dict(LOW_RISK)
    base[feature] = low_value
    worse = dict(base)
    worse[feature] = high_value
    p_base = _post(client, base)["prediction"]["probability"]
    p_worse = _post(client, worse)["prediction"]["probability"]
    assert p_worse > p_base, f"{feature}: {low_value}->{high_value} should raise P(disease)"


# --- 2. Finite and bounded -----------------------------------------------------

@pytest.mark.parametrize("profile", [HIGH_RISK, LOW_RISK])
def test_probability_finite_and_bounded(client, profile):
    p = _post(client, profile)["prediction"]["probability"]
    assert isinstance(p, float) and math.isfinite(p) and 0.0 <= p <= 1.0


# --- 3. Explicit disease-positive outcome semantics ----------------------------

def test_api_outcome_semantics_are_disease_positive(client):
    pred = _post(client, HIGH_RISK)["prediction"]
    assert pred["outcome"] == OUTCOME_ID == "significant_obstructive_cad_present"
    assert "obstructive coronary artery disease is present" in pred["probability_definition"]
    assert "not a diagnosis" in pred["probability_definition"]


def test_outcome_helpers_match_loaded_model(artifacts):
    metadata = json.loads((MODEL_DIR / "metadata.json").read_text())
    assert metadata["package_version"] == "1.0.0"
    assert "outcome_semantics" not in metadata  # frozen package: interim mapping applies
    label = resolve_disease_label(metadata)
    assert label == LEGACY_PACKAGE_DISEASE_LABEL["1.0.0"] == 0
    assert disease_label_index(artifacts["model"].classes_, label) == 0
    assert disease_log_odds_sign(artifacts["explanation_model"].classes_, label) == -1.0
    assert outcome_mapping_source(metadata) == "interim_legacy_inverted_target_mapping"
    with pytest.raises(ValueError):
        disease_label_index([0, 1, 2], 0)


def test_complementary_probability_mapping(client, artifacts):
    """P(disease) returned by the API == 1 - P(healthy label 1), and the two sum to 1."""
    model = artifacts["model"]
    healthy_col = list(model.classes_).index(1)
    for profile in (HIGH_RISK, LOW_RISK):
        proba = model.predict_proba(_frame(profile, artifacts["order"]))[0]
        assert proba.sum() == pytest.approx(1.0, abs=1e-12)
        api_p = _post(client, profile)["prediction"]["probability"]
        assert api_p == pytest.approx(1.0 - proba[healthy_col], abs=1e-12)


def test_api_metadata_discloses_interim_mapping(client):
    assert _post(client, HIGH_RISK)["metadata"]["outcome_mapping"] == "interim_legacy_inverted_target_mapping"


# --- Future model v2 readiness -------------------------------------------------

def test_explicit_v2_metadata_is_honoured_without_workaround():
    v2 = {"package_version": "2.0.0",
          "outcome_semantics": {"outcome": OUTCOME_ID, "disease_present_label": 1}}
    assert resolve_disease_label(v2) == 1
    assert disease_label_index([0, 1], 1) == 1          # P(disease) = proba[:, 1]
    assert disease_log_odds_sign([0, 1], 1) == 1.0      # no negation for a harmonised model
    assert outcome_mapping_source(v2) == "explicit_package_metadata"


@pytest.mark.parametrize("bad", [
    {"package_version": "2.0.0"},                                                   # undeclared
    {"package_version": "2.0.0", "outcome_semantics": {"outcome": OUTCOME_ID, "disease_present_label": 2}},
    {"package_version": "2.0.0", "outcome_semantics": {"outcome": "healthy", "disease_present_label": 1}},
    {"package_version": "2.0.0", "outcome_semantics": {"outcome": OUTCOME_ID, "disease_present_label": True}},
])
def test_unknown_orientation_fails_closed(bad):
    with pytest.raises(ValueError):
        resolve_disease_label(bad)


def test_model_loader_refuses_package_without_orientation(tmp_path):
    """Startup must fail for a non-legacy package that does not declare disease_present_label."""
    import shutil
    for name in ("model.joblib", "explanation_model.joblib", "feature_schema.json"):
        shutil.copy(MODEL_DIR / name, tmp_path / name)
    metadata = json.loads((MODEL_DIR / "metadata.json").read_text())
    metadata["package_version"] = "2.0.0-undeclared"
    (tmp_path / "metadata.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="disease_present_label"):
        ModelLoader(model_dir=tmp_path).load_and_validate()


def test_openapi_documents_disease_positive_outcome():
    props = app.openapi()["components"]["schemas"]["PredictionResult"]["properties"]
    assert "significant obstructive CAD is present" in props["probability"]["description"]
    assert "1 = disease present" in props["class"]["description"]


# --- 4. Threshold classification follows P(disease) ----------------------------

def test_threshold_class_is_disease_positive(client):
    assert _post(client, HIGH_RISK, threshold=0.5)["prediction"]["class"] == 1
    assert _post(client, LOW_RISK, threshold=0.5)["prediction"]["class"] == 0


def test_threshold_boundary_is_inclusive(client):
    p = _post(client, HIGH_RISK)["prediction"]["probability"]
    below = _post(client, HIGH_RISK, threshold=round(p - 1e-4, 6))["prediction"]
    above = _post(client, HIGH_RISK, threshold=round(p + 1e-4, 6))["prediction"]
    assert below["class"] == 1 and above["class"] == 0


# --- 5. Chest-pain labels match the verified encoding --------------------------

CANONICAL_CP_NAMES = {1: "typical angina", 2: "atypical angina", 3: "non-anginal pain", 4: "asymptomatic"}


def _generated_ts_options():
    """Parse CATEGORICAL_OPTIONS from the contract-generated TypeScript module."""
    ts = (ROOT / "src" / "types" / "generated-features.ts").read_text(encoding="utf-8")
    m = re.search(r"export const CATEGORICAL_OPTIONS[^=]*= (\{[\s\S]*?\n\});", ts)
    assert m, "CATEGORICAL_OPTIONS not found in generated TypeScript"
    return json.loads(m.group(1))


def test_frontend_cp_labels_match_verified_mapping():
    """R1: labels come from the generated contract; they must still match Phase 17's mapping."""
    from src.cardiovanta.data.validation import KAGGLE_CP_TO_CANONICAL
    cp = {o["code"]: o["display_label"].lower() for o in _generated_ts_options()["cp"]}
    assert cp == {k: CANONICAL_CP_NAMES[KAGGLE_CP_TO_CANONICAL[k]] for k in range(4)}
    # The <select> for cp must render from the generated options, not hardcoded strings.
    src = (ROOT / "src" / "app" / "assessment" / "page.tsx").read_text(encoding="utf-8")
    select = re.search(r'<select[^>]*id="cp"[\s\S]*?</select>', src).group(0)
    assert '{renderOptions("cp")}' in select and "<option" not in select
    assert "CATEGORICAL_OPTIONS[feature].map" in src


def _page_source():
    return (ROOT / "src" / "app" / "assessment" / "page.tsx").read_text(encoding="utf-8")


def test_out_of_codebook_codes_are_not_presented_as_clinical_values():
    """UCI codebook: ca = 0-3 vessels, thal = 3/6/7. Kaggle ca=4 / thal=0 are undefined there."""
    opts = _generated_ts_options()
    ca = {o["code"]: o for o in opts["ca"]}
    thal = {o["code"]: o for o in opts["thal"]}
    assert ca[4]["display_label"] == "Code 4 (not in UCI codebook)"   # not shown as "4 vessels"
    assert ca[4]["clinical_meaning"] is None and ca[4]["verification"] == "undefined_in_codebook"
    assert thal[0]["display_label"] == "Code 0 (not in UCI codebook)"  # not "Unknown"
    assert thal[0]["clinical_meaning"] is None and thal[0]["verification"] == "undefined_in_codebook"
    # Input encodings themselves are unchanged (values 0..4 and 0..3 still offered).
    assert sorted(ca) == [0, 1, 2, 3, 4] and sorted(thal) == [0, 1, 2, 3]
    src = _page_source()
    for fid in ("ca", "thal"):
        select = re.search(r'<select[^>]*id="%s"[\s\S]*?</select>' % fid, src).group(0)
        assert '{renderOptions("%s")}' % fid in select


def test_frontend_outcome_and_threshold_wording_is_disease_positive():
    src = _page_source()
    assert "Modelled probability of significant obstructive CAD" in src
    assert "classified as CAD present" in src and "classified as CAD absent" in src
    assert "prediction.class === 1" in src  # class 1 -> "CAD present"
    assert "Factors pushing the model toward CAD present" in src
    assert ">Model Probability<" not in src


# --- 6. Explanation signs match their stated disease meaning -------------------

def test_explanation_is_disease_log_odds_of_explanation_model(client, artifacts):
    e = artifacts["explanation_model"]
    for profile in (HIGH_RISK, LOW_RISK):
        data = _post(client, profile)
        X = _frame(profile, artifacts["order"])
        p_dis_expl = e.predict_proba(X)[0, list(e.classes_).index(0)]
        expected_logodds = math.log(p_dis_expl / (1 - p_dis_expl))
        for key in ("explanation", "shap_equivalent_explanation"):
            exp = data[key]
            assert exp["decision_function_log_odds"] == pytest.approx(expected_logodds, abs=1e-9)
            base = exp["intercept"] if key == "explanation" else exp["expected_value"]
            assert base + sum(exp["contributions"].values()) == pytest.approx(exp["decision_function_log_odds"], abs=1e-6)


def test_explanation_sign_agrees_with_calibrated_disease_probability(client):
    high, low = _post(client, HIGH_RISK), _post(client, LOW_RISK)
    assert high["explanation"]["decision_function_log_odds"] > 0 and high["prediction"]["probability"] > 0.5
    assert low["explanation"]["decision_function_log_odds"] < 0 and low["prediction"]["probability"] < 0.5
    # Adverse findings in the HIGH profile must contribute toward disease presence.
    for exp in (high["explanation"]["contributions"], high["shap_equivalent_explanation"]["contributions"]):
        for feature in ("exang", "oldpeak", "ca"):
            assert exp[feature] > 0, f"{feature} should push toward disease presence"


def test_explanation_notes_do_not_claim_calibrated_decomposition(client):
    data = _post(client, HIGH_RISK)
    for key in ("explanation", "shap_equivalent_explanation"):
        note = data[key]["note"]
        assert "CAD being present" in note
        assert "do not decompose" in note
        assert "clinical causality" in note
    # Attributions really do NOT reconstruct the calibrated probability:
    exp = data["explanation"]
    reconstructed = 1.0 / (1.0 + math.exp(-exp["decision_function_log_odds"]))
    assert abs(reconstructed - data["prediction"]["probability"]) > 1e-3
    # UI and OpenAPI disclose the same distinction.
    assert "do not exactly decompose" in _page_source()
    props = app.openapi()["components"]["schemas"]["ExplanationResult"]["properties"]
    assert "not the calibrated probability" in props["contributions"]["description"]


# --- 7. Strict validation remains intact ---------------------------------------

@pytest.mark.parametrize("mutation", [
    {"cp": 4}, {"ca": 5}, {"thal": 4}, {"sex": 2}, {"age": None}, {"extra": 1},
])
def test_strict_validation_still_rejects(client, mutation):
    payload = {**HIGH_RISK, **mutation}
    assert client.post("/api/v1/predict", json=payload).status_code == 422


def test_non_finite_still_rejected(client):
    body = json.dumps(HIGH_RISK).replace("286.0", "NaN")
    r = client.post("/api/v1/predict", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code == 422


# --- 8. No raw patient information in logs -------------------------------------

def test_no_raw_inputs_in_logs(client, caplog, capsys):
    marker = dict(HIGH_RISK, age=61.4375, chol=287.8125, trestbps=151.5625)
    with caplog.at_level(logging.DEBUG):
        _post(client, marker)
        client.post("/api/v1/predict", json={**marker, "sex": 9})  # 422 path
    captured = capsys.readouterr()
    text = "\n".join(
        [r.getMessage() + " " + json.dumps({k: str(v) for k, v in r.__dict__.items()}) for r in caplog.records]
    ) + captured.out + captured.err
    for raw in ("61.4375", "287.8125", "151.5625"):
        assert raw not in text
    events = [r for r in caplog.records if getattr(r, "event_type", None) == "prediction_event"]
    assert events and events[0].prediction_outcome == OUTCOME_ID
