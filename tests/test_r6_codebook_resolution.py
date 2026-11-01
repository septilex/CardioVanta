"""
R6 tests: verified and unresolved codebook mappings, and evidence/contract consistency.

Reads documentation and project records only (no dataset rows).
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("r6", ROOT / "experiments" / "r6_codebook_evidence.py")
r6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r6)

CONTRACT_SHA256 = "50249533dd26a9ca30c070100a045c921182e206dca88620f4e073c8568df531"   # file bytes, unchanged since R1


@pytest.fixture(scope="module")
def record():
    return r6.build()


@pytest.fixture(scope="module")
def contract():
    return json.loads((ROOT / "cardiovanta_ml" / "contracts" / "feature_schema.v2.json").read_text(encoding="utf-8"))


def _opt(contract, feature, code):
    feat = next(f for f in contract["features"] if f["id"] == feature)
    return next(o for o in feat["options"] if o["code"] == code)


# --- Verified mappings remain verified ----------------------------------------

def test_cp_patient_matched_mapping_is_canonical_and_verified(contract):
    from src.cardiovanta.data.validation import KAGGLE_CP_TO_CANONICAL
    assert KAGGLE_CP_TO_CANONICAL == {0: 4, 1: 2, 2: 3, 3: 1}
    canonical = {1: "typical angina", 2: "atypical angina", 3: "non-anginal pain", 4: "asymptomatic"}
    for code, canon in KAGGLE_CP_TO_CANONICAL.items():
        o = _opt(contract, "cp", code)
        assert o["verification"] == "verified_patient_matched" and o["canonical_uci_code"] == canon
        assert o["clinical_meaning"] == canonical[canon]


@pytest.mark.parametrize("feature,code", [("ca", 0), ("ca", 1), ("ca", 2), ("ca", 3),
                                          ("restecg", 0), ("restecg", 1), ("restecg", 2)])
def test_codebook_supported_codes_keep_their_meaning(contract, feature, code):
    o = _opt(contract, feature, code)
    assert o["verification"] == "codebook_and_project_contract" and o["clinical_meaning"]


# --- Unresolved mappings remain unresolved, with no clinical meaning --------------

@pytest.mark.parametrize("feature,code,status", [
    ("slope", 0, "unverified"), ("slope", 1, "unverified"), ("slope", 2, "unverified"),
    ("thal", 1, "unverified"), ("thal", 2, "unverified"), ("thal", 3, "unverified"),
    ("thal", 0, "undefined_in_codebook"), ("ca", 4, "undefined_in_codebook"),
])
def test_unresolved_codes_keep_status_and_no_meaning(record, contract, feature, code, status):
    o = _opt(contract, feature, code)
    assert o["verification"] == status and o["clinical_meaning"] is None
    m = next(x for x in record["mappings"] if x["feature"] == feature and x["production_code"] == code)
    assert m["resolved_status"] == m["contract_status"] == status
    assert m["clinical_meaning"] is None and m["confidence"].startswith("unresolved")
    assert m["resolution_path"]


def test_no_status_upgraded_without_verifying_evidence(record):
    assert record["summary"]["newly_verified"] == []
    for m in record["mappings"]:
        assert not any(e["level"] in r6.VERIFYING_LEVELS for e in m["evidence"])
        assert m["resolved_status"] == m["contract_status"]
    assert record["summary"]["consistent_with_contract"] is True


def test_hypotheses_are_labelled_and_never_used_as_evidence(record):
    for m in record["mappings"]:
        for h in m["hypotheses_not_evidence"]:
            assert isinstance(h, str)
        assert all(e["level"] != "E4" for e in m["evidence"])   # secondary claims appear only as hypotheses
    ca4 = next(x for x in record["mappings"] if x["feature"] == "ca" and x["production_code"] == 4)
    assert any("missing" in h for h in ca4["hypotheses_not_evidence"])
    assert ca4["resolved_status"] == "undefined_in_codebook"     # the hypothesis did not change the status


# --- Source vs production codes and documented provenance ---------------------------

def test_canonical_source_codes_come_from_the_uci_codebook(record):
    defs = record["mappings"][0]["evidence"][0]["finding"]
    assert "Value 1: upsloping" in defs["slope"] and "Value 3: downsloping" in defs["slope"]
    assert "3 = normal; 6 = fixed defect; 7 = reversable defect" in defs["thal"]
    assert "(0-3)" in defs["ca"]
    assert "-9.0" in defs["missing_values"]
    assert defs["cleveland_class_distribution"].split()[1:] == ["164", "55", "36", "35", "13", "303"]


def test_provenance_findings_are_recorded(record):
    finding = next(e for e in record["mappings"][0]["evidence"] if "Phase 17 matched" in e["finding"])["finding"]
    assert "'cp': True" in finding and "'target': True" in finding
    assert "'slope': False" in finding and "'thal': False" in finding and "'ca': False" in finding
    docs = record["sources"]["public_documentation"]
    assert docs["uci_dataset_page"]["loaded"] is True and docs["uci_dataset_page"]["documents_kaggle_recoding"] is False
    assert docs["kaggle_dataset_page"]["http_status"] == 404
    assert record["discrepancies"][0]["item"] == "Cleveland num = 0 count"


# --- Isolation, determinism and integrity -----------------------------------------

def test_builder_reads_no_dataset_rows_and_is_deterministic(record):
    src = (ROOT / "experiments" / "r6_codebook_evidence.py").read_text(encoding="utf-8")
    # Every file the builder can open is a module-level Path constant; none is a dataset.
    paths = {name: v for name, v in vars(r6).items() if isinstance(v, Path)}
    assert set(paths) == {"PROJECT_ROOT", "CODEBOOK", "CONTRACT", "VALIDATION_MODULE", "PHASE17_REPORT", "PROFILING", "RESULTS"}
    for name, p in paths.items():
        assert p.suffix not in (".csv", ".data") or name == "RESULTS", name
        assert "dev_indices" not in str(p)
    assert r6.CODEBOOK.name == "heart-disease.names"        # documentation text, not a data file
    for forbidden in ("read_csv", '"heart.csv"', "dev_indices.json", "hungarian.data\"", "urllib", "joblib", "csv.reader"):
        assert forbidden not in src, forbidden
    assert record["summary"]["data_rows_read"] == 0
    assert json.dumps(r6.build(), sort_keys=True) == json.dumps(record, sort_keys=True)


def test_contract_and_registry_pin_unchanged(record):
    path = ROOT / "cardiovanta_ml" / "contracts" / "feature_schema.v2.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == CONTRACT_SHA256
    assert record["sources"]["contract"]["sha256"] == CONTRACT_SHA256
    from cardiovanta_ml.contracts import bundled_contract_sha256, generated_features
    meta = json.loads((ROOT / "artifacts" / "models" / "cardiovanta-lr13" / "1.0.0" / "metadata.json").read_text())
    assert bundled_contract_sha256() == generated_features.CONTRACT_SHA256 == meta["feature_contract"]["sha256"]
