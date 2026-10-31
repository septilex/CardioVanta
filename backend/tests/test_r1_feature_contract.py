"""
R1 tests: unified, versioned clinical feature & outcome contract.

Source of truth: cardiovanta_ml/contracts/feature_schema.v2.json (moved into the ML package in R2)
Generated:       cardiovanta_ml/contracts/generated_features.py, src/types/generated-features.ts

All fixtures are synthetic. data/raw/heart.csv is never opened.
"""
import importlib.util
import json
import math
import re
import shutil
from pathlib import Path
from typing import Literal, get_args

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.main import app
from cardiovanta_ml.contracts import generated_features as gen
from backend.app.schemas.predict import FeatureContributions, PredictRequest

ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACT_PATH = ROOT / "cardiovanta_ml" / "contracts" / "feature_schema.v2.json"
ARTIFACT_SCHEMA_PATH = ROOT / "artifacts" / "model" / "feature_schema.json"
PRODUCTION_FEATURES = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
                       "thalach", "exang", "oldpeak", "slope", "ca", "thal"]


def _load_generator():
    spec = importlib.util.spec_from_file_location("cv_contract_generate", ROOT / "contracts" / "codegen" / "generate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


generator = _load_generator()


@pytest.fixture(scope="module")
def contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def features(contract):
    return {f["id"]: f for f in contract["features"]}


# --- 1-3. Feature inventory ----------------------------------------------------

def test_all_13_production_features_present_in_order(contract):
    assert contract["feature_order"] == PRODUCTION_FEATURES
    assert [f["id"] for f in contract["features"]] == PRODUCTION_FEATURES


def test_no_duplicate_feature_identifiers(contract):
    ids = [f["id"] for f in contract["features"]]
    assert len(ids) == len(set(ids)) == 13


def test_every_feature_has_type_description_and_policy(features):
    for fid, f in features.items():
        assert f["type"] in {"continuous", "binary", "categorical"}, fid
        assert f["label"].strip() and f["description"].strip(), fid
        assert f["required"] is True and f["missing_value_policy"] == "rejected", fid
        assert f.get("evidence"), f"{fid}: source evidence required"
        if f["type"] == "continuous":
            assert f["unit"] and f["unit_evidence"], fid
        else:
            assert f["options"], fid


# --- 4. Units, bounds and codes match existing backend behaviour ---------------

def test_contract_matches_frozen_model_input_schema(features):
    artifact = json.loads(ARTIFACT_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert artifact["feature_order"] == PRODUCTION_FEATURES
    for a in artifact["features"]:
        f = features[a["name"]]
        assert f["type"] == a["type"], a["name"]
        if a["type"] == "continuous":
            assert f["development_range"]["min"] == a["min"]
            assert f["development_range"]["max"] == a["max"]
            # Backend accepts any finite value; the range is only a warning guardrail.
            assert f["accepted"] == {"finite_only": True, "min": None, "max": None}
        else:
            assert [o["code"] for o in f["options"]] == a["allowed_values"], a["name"]


def test_units_match_codebook_and_existing_ui(features):
    assert {fid: f["unit"] for fid, f in features.items() if f["type"] == "continuous"} == {
        "age": "years", "trestbps": "mm Hg", "chol": "mg/dl", "thalach": "bpm", "oldpeak": "mm"}
    # oldpeak's unit is not stated by the codebook: the contract must say so.
    assert "does not state a unit" in features["oldpeak"]["unit_evidence"]


def test_outside_development_range_is_accepted_with_warning():
    payload = dict(_VALID, age=95.0)
    with TestClient(app) as c:
        r = c.post("/api/v1/predict", json=payload)
    assert r.status_code == 200
    assert r.json()["development_range_warning"]["features"] == ["age"]


# --- 5-7. Categorical mappings -------------------------------------------------

def _options(features, fid):
    return {o["code"]: o for o in features[fid]["options"]}


def test_chest_pain_mapping(features):
    from src.cardiovanta.data.validation import KAGGLE_CP_TO_CANONICAL
    cp = _options(features, "cp")
    assert {k: v["display_label"] for k, v in cp.items()} == {
        0: "Asymptomatic", 1: "Atypical Angina", 2: "Non-anginal Pain", 3: "Typical Angina"}
    assert {k: v["canonical_uci_code"] for k, v in cp.items()} == KAGGLE_CP_TO_CANONICAL
    assert all(v["verification"] == "verified_patient_matched" for v in cp.values())


def test_resting_ecg_mapping(features):
    ecg = _options(features, "restecg")
    assert {k: v["display_label"] for k, v in ecg.items()} == {
        0: "Normal", 1: "ST-T Wave Abnormality", 2: "Left Ventricular Hypertrophy"}
    assert all(v["verification"] == "codebook_and_project_contract" for v in ecg.values())


def test_unverified_mappings_remain_explicitly_unverified(features):
    for fid in ("slope", "thal"):
        for code, o in _options(features, fid).items():
            if fid == "thal" and code == 0:
                continue
            assert o["verification"] == "unverified", (fid, code)
            assert o["clinical_meaning"] is None, (fid, code)
    for fid, code in (("ca", 4), ("thal", 0)):
        o = _options(features, fid)[code]
        assert o["verification"] == "undefined_in_codebook"
        assert o["clinical_meaning"] is None
        assert "not in UCI codebook" in o["display_label"]
        assert "missing" not in o["display_label"].lower()  # not converted into a fabricated category
    assert gen.FEATURES["slope"]["mapping_fully_verified"] is False
    assert gen.FEATURES["thal"]["mapping_fully_verified"] is False
    assert gen.FEATURES["cp"]["mapping_fully_verified"] is True


def test_accepted_code_is_distinct_from_verified_label(features):
    """Every discrete option has an accepted code; only verified ones carry a clinical meaning."""
    for f in features.values():
        for o in f.get("options", []):
            verified = o["verification"] in {"verified_patient_matched", "codebook_and_project_contract"}
            assert (o["clinical_meaning"] is not None) == verified, (f["id"], o["code"])


# --- 8-9. Outcome semantics ----------------------------------------------------

def test_outcome_definition_is_disease_present(contract):
    o = contract["outcome"]
    assert o["id"] == gen.OUTCOME_ID == "significant_obstructive_cad_present"
    assert o["positive"] == {"value": 1, "meaning": "disease_present", "label": "Significant obstructive CAD present"}
    assert o["negative"]["meaning"] == "disease_absent" and o["negative"]["value"] == 0
    assert o["output_probability"] == "P(disease present)"
    assert "greater than 50% diameter stenosis" in o["clinical_definition"]
    assert gen.OUTCOME == generator._outcome(contract)


def test_legacy_model_label_mapping_is_separate_from_outcome(contract):
    assert "disease_present_label" not in json.dumps(contract["outcome"])
    pkgs = contract["model_label_mappings"]["packages"]
    assert pkgs == [p for p in pkgs if p["model_id"] == "cardiovanta-lr13"]
    legacy = pkgs[0]
    assert legacy["package_version"] == "1.0.0" and legacy["status"] == "interim_legacy"
    # Clinical positive value is 1; the legacy artifact's disease label is 0. Two different concepts.
    assert contract["outcome"]["positive"]["value"] == 1 and legacy["disease_present_label"] == 0
    assert gen.LEGACY_PACKAGE_DISEASE_LABELS == {"1.0.0": 0}
    from src.inference import outcome
    assert outcome.LEGACY_PACKAGE_DISEASE_LABEL == gen.LEGACY_PACKAGE_DISEASE_LABELS
    assert outcome.OUTCOME_ID == gen.OUTCOME_ID
    assert outcome.PROBABILITY_DEFINITION == contract["outcome"]["probability_definition"]


# --- 10-11. Generated definitions match the contract ---------------------------

def test_generated_python_matches_contract(contract):
    path = ROOT / "cardiovanta_ml" / "contracts" / "generated_features.py"
    assert path.read_text(encoding="utf-8").replace("\r\n", "\n") == generator.render_python(contract)
    assert gen.CONTRACT_VERSION == contract["contract_version"]
    assert gen.CONTRACT_SHA256 == generator.contract_sha256(contract)
    assert list(gen.FEATURE_ORDER) == PRODUCTION_FEATURES
    for f in contract["features"]:
        field = gen.ClinicalFeaturesBase.model_fields[f["id"]]
        if f["type"] == "continuous":
            assert field.annotation is float
        else:
            assert list(get_args(field.annotation)) == [o["code"] for o in f["options"]]
        assert field.description.startswith(f["label"])


def test_backend_reexport_is_the_package_contract_module():
    """R2: backend.app.schemas.generated_features is a thin re-export, not a second copy."""
    from backend.app.schemas import generated_features as backend_gen
    for name in ("ClinicalFeaturesBase", "FeatureContributionsBase", "OUTCOME", "FEATURE_ORDER",
                 "CONTRACT_SHA256", "LEGACY_PACKAGE_DISEASE_LABELS"):
        assert getattr(backend_gen, name) is getattr(gen, name)
    src = (ROOT / "backend" / "app" / "schemas" / "generated_features.py").read_text(encoding="utf-8")
    assert "class ClinicalFeaturesBase" not in src and "AUTO-GENERATED" not in src


def test_single_canonical_contract_file():
    assert not (ROOT / "contracts" / "feature_schema.v2.json").exists()
    assert generator.CONTRACT_REL.as_posix() == "cardiovanta_ml/contracts/feature_schema.v2.json"
    assert generator.PY_OUT_REL.as_posix() == "cardiovanta_ml/contracts/generated_features.py"


def test_backend_request_schema_uses_generated_contract():
    assert issubclass(PredictRequest, gen.ClinicalFeaturesBase)
    assert issubclass(FeatureContributions, gen.FeatureContributionsBase)
    assert list(PredictRequest.model_fields) == PRODUCTION_FEATURES
    assert list(FeatureContributions.model_fields) == PRODUCTION_FEATURES
    src = (ROOT / "backend" / "app" / "schemas" / "predict.py").read_text(encoding="utf-8")
    assert "Literal[0, 1]" not in src  # no hand-written feature codes left


def _ts_const(ts, name):
    m = re.search(r"export const %s[^=]*= (\{[\s\S]*?\n\})(?: as const)?;" % name, ts)
    assert m, name
    return json.loads(m.group(1))


def test_generated_typescript_matches_contract(contract):
    path = ROOT / "src" / "types" / "generated-features.ts"
    ts = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert ts == generator.render_typescript(contract)
    assert f'CONTRACT_VERSION = "{contract["contract_version"]}"' in ts
    opts = _ts_const(ts, "CATEGORICAL_OPTIONS")
    for f in contract["features"]:
        if f["type"] == "continuous":
            assert f"  {f['id']}: number;" in ts
            assert f["id"] not in opts
        else:
            assert [o["code"] for o in opts[f["id"]]] == [o["code"] for o in f["options"]]
            assert [o["display_label"] for o in opts[f["id"]]] == [o["display_label"] for o in f["options"]]
            codes = " | ".join(str(o["code"]) for o in f["options"])
            assert f"export type {generator._pascal(f['id'])}Code = {codes};" in ts
    assert _ts_const(ts, "OUTCOME")["output_probability"] == "P(disease present)"


def test_frontend_types_reuse_generated_definitions():
    idx = (ROOT / "src" / "types" / "index.ts").read_text(encoding="utf-8")
    assert 'export * from "./generated-features";' in idx
    assert "export type PredictRequest = ClinicalFeatures;" in idx
    assert "sex: 0 | 1" not in idx  # no hand-written feature interface
    page = (ROOT / "src" / "app" / "assessment" / "page.tsx").read_text(encoding="utf-8")
    assert "CATEGORICAL_OPTIONS" in page and "CATEGORICAL_LABELS" in page
    assert '"Typical Angina"' not in page and '"Asymptomatic"' not in page  # no hand-copied option tables


# --- 12-13. Deterministic generation and --check -------------------------------

@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / generator.CONTRACT_REL).parent.mkdir(parents=True)
    shutil.copy(CONTRACT_PATH, tmp_path / generator.CONTRACT_REL)
    return tmp_path


def _outputs(root):
    return {rel: (root / rel).read_bytes() for rel in (generator.PY_OUT_REL, generator.TS_OUT_REL)}


def test_generation_is_deterministic(sandbox):
    assert generator.main(["--root", str(sandbox)]) == 0
    first = _outputs(sandbox)
    assert generator.main(["--root", str(sandbox)]) == 0
    assert _outputs(sandbox) == first
    for rel, content in first.items():
        assert b"\r\n" not in content
        assert content.decode("utf-8").replace("\r\n", "\n") == (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def test_check_mode_passes_when_fresh_and_detects_stale(sandbox, capsys):
    assert generator.main(["--root", str(sandbox), "--check"]) == 1  # outputs missing
    assert generator.main(["--root", str(sandbox)]) == 0
    assert generator.main(["--root", str(sandbox), "--check"]) == 0
    ts = sandbox / generator.TS_OUT_REL
    ts.write_text(ts.read_text(encoding="utf-8").replace("Asymptomatic", "Typical Angina"), encoding="utf-8")
    assert generator.main(["--root", str(sandbox), "--check"]) == 1
    assert "STALE" in capsys.readouterr().err
    # A contract change without regeneration is also stale.
    assert generator.main(["--root", str(sandbox)]) == 0
    c = json.loads((sandbox / generator.CONTRACT_REL).read_text())
    c["contract_version"] = "2.0.1"
    (sandbox / generator.CONTRACT_REL).write_text(json.dumps(c))
    assert generator.main(["--root", str(sandbox), "--check"]) == 1


def test_check_against_repository_is_clean():
    assert generator.main(["--check"]) == 0


def _mutated(mutate):
    c = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    mutate(c)
    return c


@pytest.mark.parametrize("mutate,expected", [
    (lambda c: c["features"].append(dict(c["features"][0])), "duplicate feature ids"),
    (lambda c: c["features"][0].update(type="ordinal"), "unsupported type"),
    (lambda c: c["features"][0].update(colour="red"), "unsupported key"),
    (lambda c: c["features"][1].update(required=False), "optional features are not supported"),
    (lambda c: c["features"][10]["options"][0].update(clinical_meaning="upsloping"), "must not assert a clinical_meaning"),
    (lambda c: c["features"][2]["options"][0].update(verification="probably"), "unknown verification"),
    (lambda c: c["features"][1]["options"].append({"code": 2, "display_label": "x", "clinical_meaning": "x", "verification": "codebook_and_project_contract"}), "binary features must have codes"),
    (lambda c: c["outcome"]["positive"].update(meaning="healthy"), "disease_present"),
    (lambda c: c.update(feature_order=c["feature_order"][::-1]), "feature_order"),
    (lambda c: c["model_label_mappings"]["packages"][0].update(disease_present_label=2), "0 or 1"),
])
def test_generator_rejects_unsupported_definitions(sandbox, capsys, mutate, expected):
    (sandbox / generator.CONTRACT_REL).write_text(json.dumps(_mutated(mutate)))
    assert generator.main(["--root", str(sandbox)]) == 2
    assert expected in capsys.readouterr().err
    assert not (sandbox / generator.PY_OUT_REL).exists()


def test_generator_rejects_malformed_json(sandbox, capsys):
    (sandbox / generator.CONTRACT_REL).write_text('{"contract": ')
    assert generator.main(["--root", str(sandbox)]) == 2
    assert "malformed JSON" in capsys.readouterr().err


# --- 14. Request validation behaviour is unchanged -----------------------------

class LegacyPredictRequest(BaseModel):
    """Frozen copy of the pre-R1 hand-written backend/app/schemas/predict.py PredictRequest."""
    model_config = ConfigDict(extra='forbid', json_schema_serialization_defaults_required=True)
    age: float = Field(allow_inf_nan=False)
    sex: Literal[0, 1]
    cp: Literal[0, 1, 2, 3]
    trestbps: float = Field(allow_inf_nan=False)
    chol: float = Field(allow_inf_nan=False)
    fbs: Literal[0, 1]
    restecg: Literal[0, 1, 2]
    thalach: float = Field(allow_inf_nan=False)
    exang: Literal[0, 1]
    oldpeak: float = Field(allow_inf_nan=False)
    slope: Literal[0, 1, 2]
    ca: Literal[0, 1, 2, 3, 4]
    thal: Literal[0, 1, 2, 3]


_VALID = dict(age=55.0, sex=1, cp=2, trestbps=130.0, chol=240.0, fbs=0, restecg=1,
              thalach=150.0, exang=0, oldpeak=1.2, slope=1, ca=0, thal=2)


def _payload_matrix():
    cases = [("valid", dict(_VALID))]
    for fid in PRODUCTION_FEATURES:
        for bad in (None, "", "abc", "1", True, [], {}):
            cases.append((f"{fid}={bad!r}", {**_VALID, fid: bad}))
        missing = dict(_VALID)
        del missing[fid]
        cases.append((f"missing {fid}", missing))
    for fid in ("sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"):
        for v in (-1, 0, 1, 2, 3, 4, 5, 9, 1.0, 1.5, 0.0):
            cases.append((f"{fid}={v!r}", {**_VALID, fid: v}))
    for fid in ("age", "trestbps", "chol", "thalach", "oldpeak"):
        for v in (0, -5, 1e9, 45, "45", "4.5e1", float("nan"), float("inf"), float("-inf")):
            cases.append((f"{fid}={v!r}", {**_VALID, fid: v}))
    cases.append(("extra field", {**_VALID, "extra": 1}))
    return cases


def _outcome_of(model, payload):
    try:
        return ("ok", model.model_validate(payload).model_dump())
    except ValidationError as e:
        return ("error", [(err["type"], err["loc"]) for err in e.errors()])


@pytest.mark.parametrize("name,payload", _payload_matrix(), ids=[c[0] for c in _payload_matrix()])
def test_request_validation_identical_to_pre_r1_schema(name, payload):
    assert _outcome_of(PredictRequest, payload) == _outcome_of(LegacyPredictRequest, payload)


@pytest.mark.parametrize("field,token", [
    (f, t) for f in ("age", "trestbps", "chol", "thalach", "oldpeak")
    for t in ("NaN", "Infinity", "-Infinity", '"NaN"', '"inf"', '"-inf"', '"Infinity"')
])
def test_json_non_finite_validation_identical(field, token):
    # Substitute the raw JSON token in place (no duplicate keys).
    text = json.dumps({**_VALID, field: "__TOKEN__"}).replace('"__TOKEN__"', token)
    def run(model):
        try:
            model.model_validate_json(text)
            return "ok"
        except ValidationError as e:
            return sorted((err["type"], err["loc"]) for err in e.errors())
    assert run(PredictRequest) == run(LegacyPredictRequest) != "ok"


def test_request_json_schema_constraints_unchanged():
    def strip(schema):
        props = {k: {kk: vv for kk, vv in v.items() if kk not in ("description", "title")}
                 for k, v in schema["properties"].items()}
        return props, schema["required"], schema.get("additionalProperties")
    assert strip(PredictRequest.model_json_schema()) == strip(LegacyPredictRequest.model_json_schema())


# --- 15. R0.3 prediction semantics intact -------------------------------------

def test_r03_disease_positive_semantics_intact():
    high = dict(age=67.0, sex=1, cp=0, trestbps=160.0, chol=286.0, fbs=0, restecg=0,
                thalach=108.0, exang=1, oldpeak=3.0, slope=1, ca=3, thal=3)
    low = dict(age=37.0, sex=0, cp=2, trestbps=120.0, chol=200.0, fbs=0, restecg=1,
               thalach=187.0, exang=0, oldpeak=0.0, slope=2, ca=0, thal=2)
    with TestClient(app) as c:
        h = c.post("/api/v1/predict?threshold=0.5", json=high).json()
        lo = c.post("/api/v1/predict?threshold=0.5", json=low).json()
    assert h["prediction"]["probability"] == pytest.approx(0.985790929, abs=1e-6)
    assert lo["prediction"]["probability"] == pytest.approx(0.016065906, abs=1e-6)
    assert (h["prediction"]["class"], lo["prediction"]["class"]) == (1, 0)
    assert h["prediction"]["outcome"] == gen.OUTCOME_ID
    assert h["prediction"]["probability_definition"] == gen.PROBABILITY_DEFINITION
    assert math.isfinite(h["explanation"]["decision_function_log_odds"])
