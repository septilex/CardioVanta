"""
H2.1 synthetic regression tests (no dataset or external cohort is read).
"""
import ast
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("h21", ROOT / "experiments" / "h2_1_calibration_confirmation.py")
h21 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h21)

SMALL = dict(c_grid=(0.1, 1.0), n_outer=3, n_inner=3, n_inner_cal=2, n_cal=3)


def _synthetic(n=96, seed=3):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({
        "age": rng.uniform(30, 75, n), "sex": rng.integers(0, 2, n), "cp": rng.integers(0, 4, n),
        "trestbps": rng.uniform(95, 190, n), "chol": rng.uniform(130, 400, n), "fbs": rng.integers(0, 2, n),
        "restecg": rng.integers(0, 3, n), "thalach": rng.uniform(80, 200, n), "exang": rng.integers(0, 2, n),
        "oldpeak": rng.uniform(0, 5, n), "slope": rng.integers(0, 3, n), "ca": rng.choice([0, 1, 2, 3, 4], n, p=[.5, .2, .15, .1, .05]),
        "thal": rng.integers(0, 4, n),
    })[h21.h2.r4.FEATURES].astype(float)
    logit = -1 + 0.9 * X["exang"] + 0.6 * X["oldpeak"] + 0.6 * np.minimum(X["ca"], 3) - 0.02 * (X["thalach"] - 150)
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit.to_numpy()))).astype(int)
    X.iloc[1] = X.iloc[0]
    y[1] = y[0]
    return X, y, X.groupby(h21.h2.r4.FEATURES).ngroup().to_numpy()


def test_preregistered_constants():
    assert h21.ARMS == ("A_production", "C_pooled_oof_calibration")
    assert h21.h2.ARMS["A_production"] == {"class_weight": "balanced", "ensemble": True}
    assert h21.h2.ARMS["C_pooled_oof_calibration"] == {"class_weight": "balanced", "ensemble": False}
    assert h21.N_REPEATS == 20 and h21.N_BOOTSTRAP == 2000
    # seeds disjoint from H2 (1000/2000/3000 + r for r < 10, bootstrap 42)
    h2_seeds = {o + r for o in (1000, 2000, 3000) for r in range(10)} | {42}
    h21_seeds = {o + r for o in (h21.SEED_OUTER, h21.SEED_INNER, h21.SEED_CAL) for r in range(h21.N_REPEATS)} | {h21.SEED_BOOT}
    assert not h2_seeds & h21_seeds
    assert h21.ACCEPT == {"slope_ci_high_below": 0.0, "auc_ci_low_at_least": -0.01,
                          "candidate_slope_range": (0.90, 1.10), "min_repeats_expected_direction": 16}
    assert h21.SECONDARY == ("log_loss", "brier", "ece_10")


def test_run_deterministic_identical_splits_complete():
    X, y, g = _synthetic()
    a = h21.run(X, y, g, n_repeats=2, **SMALL)
    b = h21.run(X, y, g, n_repeats=2, **SMALL)
    assert a["outer_test_folds"] == b["outer_test_folds"]
    for arm in h21.ARMS:
        assert not np.isnan(a["oof"][arm]).any()
        assert np.array_equal(a["oof"][arm], b["oof"][arm])
    for folds in a["outer_test_folds"]:
        assert sorted(i for f in folds for i in f) == list(range(len(y)))
        assert all(not ({0, 1} & set(f)) or {0, 1} <= set(f) for f in folds)   # duplicates kept together


def test_outer_test_labels_never_influence_tuning_calibration_or_prediction():
    """Mirror run()'s per-fold steps (H2.1 seeds): flipping outer-test labels changes nothing."""
    from sklearn.model_selection import StratifiedGroupKFold
    X, y, g = _synthetic()
    tr, te = next(StratifiedGroupKFold(3, shuffle=True, random_state=h21.SEED_OUTER).split(X, y, g))
    y_flip = y.copy()
    y_flip[te] = 1 - y_flip[te]
    for arm in h21.ARMS:
        preds = []
        for labels in (y, y_flip):
            C = h21.h2.select_C(arm, X.iloc[tr], labels[tr], g[tr], (0.1, 1.0), h21.SEED_INNER, 3, 2)
            model = h21.h2.fit_arm(arm, C, X.iloc[tr], labels[tr], g[tr], 3, h21.SEED_CAL)
            preds.append((C, model.predict_proba(X.iloc[te])[:, 1]))
        assert preds[0][0] == preds[1][0] and np.array_equal(preds[0][1], preds[1][1]), arm


def test_bootstrap_levels_and_verdict_consistency():
    X, y, g = _synthetic()
    res = h21.run(X, y, g, n_repeats=2, **SMALL)
    out = h21.evaluate(y, g, res, n_bootstrap=40)
    sec = out["secondary_bonferroni"]
    assert sec["level"] == pytest.approx(1 - 0.05 / 3)
    for k, v in sec["endpoints"].items():
        assert v["ci_bonferroni_low"] <= v["ci95_low"] <= v["mean"] <= v["ci95_high"] <= v["ci_bonferroni_high"], k
        assert v["supportive_bonferroni"] == (v["ci_bonferroni_high"] < 0)
    crit = out["acceptance_criteria"]
    assert len(crit) == 4
    assert out["verdict"] == ("confirmed" if all(c["pass"] for c in crit.values()) else "not_confirmed")
    p = out["primary"]
    assert p["expected_direction"] == "negative" and len(p["per_repeat_differences"]) == 2
    assert crit["1_primary_dslope_ci95_high_below_0"]["pass"] == (p["ci95_high"] < 0)
    assert crit["4_dslope_negative_in_at_least_80pct_of_repeats"]["required"] == pytest.approx(1.6)


def test_acceptance_criterion_3_range():
    lo, hi = h21.ACCEPT["candidate_slope_range"]
    assert (lo, hi) == (0.90, 1.10)


def test_external_cohorts_excluded_and_never_parsed():
    ext = h21.EXTERNAL_EXCLUSION
    assert ext["evaluated"] is False and ext["external_data_parsed"] is False
    assert "Phase 17" in ext["reuse_disclosure"] and "not untouched" in ext["reuse_disclosure"]
    assert ext["evidence"]["documented_missing_counts_-9_sentinel"]["hungary_n294"]["ca"] == 290
    src = (ROOT / "experiments" / "h2_1_calibration_confirmation.py").read_text(encoding="utf-8")
    for forbidden in ("parse_hungarian_cohort", "parse_long_beach_cohort", "load_all_multicenter_cohorts",
                      "hungarian.data", "long-beach-va.data"):
        assert forbidden not in src, forbidden


def test_never_touches_production():
    tree = ast.parse((ROOT / "experiments" / "h2_1_calibration_confirmation.py").read_text(encoding="utf-8"))
    calls = {f"{n.func.value.id}.{n.func.attr}" for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)}
    assert not {"joblib.dump", "joblib.load", "pickle.dump", "pickle.load"} & calls
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not any(m.startswith(("cardiovanta_ml", "backend", "src")) for m in modules)
    assert h21.RESULTS == ROOT / "experiments" / "results" / "h2_1_calibration_confirmation.json"
