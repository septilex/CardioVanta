"""
R5 synthetic regression tests (no dataset is read; the production model is loaded read-only via the registry).
"""
import ast
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("r5", ROOT / "experiments" / "r5_explanation_stability.py")
r5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r5)


def test_profiles_deterministic_and_within_contract():
    a, b = r5.generate_profiles(30), r5.generate_profiles(30)
    assert a == b and len(a) == 30 and a != r5.generate_profiles(30, seed=1)
    for p in a:
        assert list(p) == r5.FEATURES
        for f in r5.FEATURES:
            meta = r5.contract.FEATURES[f]
            if meta["type"] == "continuous":
                assert meta["development_range"]["min"] <= p[f] <= meta["development_range"]["max"]
            else:
                assert p[f] in {o["code"] for o in meta["options"]}


def test_perturbations_stay_within_constraints_and_change_one_feature():
    prof = r5.generate_profiles(1)[0]
    seen = {f: 0 for f in r5.FEATURES}
    for feature, kind, label, new in r5.perturbations(prof):
        seen[feature] += 1
        if new is None:
            assert kind == "continuous"          # out-of-range shift skipped, not clipped
            continue
        assert [f for f in r5.FEATURES if new[f] != prof[f]] == [feature]
        meta = r5.contract.FEATURES[feature]
        if kind == "continuous":
            assert meta["development_range"]["min"] <= new[feature] <= meta["development_range"]["max"]
        else:
            assert new[feature] in {o["code"] for o in meta["options"]} and new[feature] != prof[feature]
    for f in r5.CONTINUOUS:
        assert seen[f] == 4
    for f in r5.DISCRETE:
        assert seen[f] == len(r5.contract.FEATURES[f]["options"]) - 1


def test_metric_helpers_on_known_vectors():
    feats = r5.FEATURES
    a = {f: float(i + 1) for i, f in enumerate(feats)}            # thal largest ... age smallest
    b = dict(a)
    assert r5.top_k(a, 3) == ["thal", "ca", "slope"]
    assert r5.top_k_overlap(a, b, 3) == 1.0 and r5.rank_correlation(a, b) == pytest.approx(1.0)
    b["age"] = 100.0                                               # age jumps to the top
    assert r5.top_k_overlap(a, b, 3) == pytest.approx(2 / 3)
    tied = {f: 1.0 for f in feats}
    assert r5.top_k(tied, 2) == feats[:2]                          # deterministic tie-break
    assert math.isnan(r5.rank_correlation(tied, a))
    assert r5._sign(1e-13) == 0 and r5._sign(-0.5) == -1


def test_verification_levels_reported_without_meanings():
    assert r5.verification_level("cp", 0) == "verified_patient_matched"
    assert r5.verification_level("slope", 1) == "unverified"
    assert r5.verification_level("ca", 4) == "undefined_in_codebook"
    assert r5.verification_level("thal", 0) == "undefined_in_codebook"


@pytest.fixture(scope="module")
def small_run():
    return r5.run(n_profiles=8)


def test_locality_additivity_and_shared_deltas(small_run):
    chk = small_run["expectation_checks"]
    assert chk["locality_holds"] and chk["locality_max_other_contribution_change"] <= 1e-12
    assert chk["additivity_holds"] and chk["max_additivity_error"] < 1e-9
    assert chk["methods_share_deltas"]
    for kind in ("continuous", "categorical"):
        for m in r5.METHODS:
            assert small_run[kind][m]["other_sign_flips_total"] == 0


def test_summary_structure_and_separation(small_run):
    c = small_run["counts"]
    assert c["profiles"] == 8 and c["continuous"] + c["categorical"] == c["perturbations_evaluated"]
    assert small_run["continuous"]["n_perturbations"] == c["continuous"]
    assert set(small_run["continuous_by_magnitude"]) <= {"-10%", "-5%", "+5%", "+10%"}
    assert set(small_run["categorical_by_verification"]) == {"verified_only", "unverified", "undefined_in_codebook"}
    for m in r5.METHODS:
        s = small_run["continuous"][m]
        assert 0 <= s["top3_overlap"]["min"] <= s["top3_overlap"]["max"] <= 1
        assert 0 <= s["own_sign_flip_rate"] <= 1
    assert small_run["model"] == {"id": "cardiovanta-lr13", "version": "1.0.0",
                                  "outcome_mapping": "interim_legacy", "registry_verified": True}


def test_run_is_deterministic():
    a, b = r5.run(n_profiles=3), r5.run(n_profiles=3)
    assert a == b


def test_no_dataset_and_no_production_writes():
    src = (ROOT / "experiments" / "r5_explanation_stability.py").read_text(encoding="utf-8")
    for forbidden in ("heart.csv", "dev_indices", "hungarian", "long-beach", "read_csv", ".fit("):
        assert forbidden not in src, forbidden
    tree = ast.parse(src)
    calls = {f"{n.func.value.id}.{n.func.attr}" for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)}
    assert not {"joblib.dump", "joblib.load", "pickle.dump", "pickle.load"} & calls
    assert r5.RESULTS == ROOT / "experiments" / "results" / "r5_explanation_stability.json"
