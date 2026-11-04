"""
H2 synthetic regression tests (no dataset is read).
"""
import ast
import importlib.util
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("h2", ROOT / "experiments" / "h2_calibration_recipe.py")
h2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h2)


def _synthetic(n=96, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({
        "age": rng.uniform(30, 75, n), "sex": rng.integers(0, 2, n), "cp": rng.integers(0, 4, n),
        "trestbps": rng.uniform(95, 190, n), "chol": rng.uniform(130, 400, n), "fbs": rng.integers(0, 2, n),
        "restecg": rng.integers(0, 3, n), "thalach": rng.uniform(80, 200, n), "exang": rng.integers(0, 2, n),
        "oldpeak": rng.uniform(0, 5, n), "slope": rng.integers(0, 3, n), "ca": rng.choice([0, 1, 2, 3, 4], n, p=[.5, .2, .15, .1, .05]),
        "thal": rng.integers(0, 4, n),
    })[h2.r4.FEATURES].astype(float)
    logit = -1 + 0.9 * X["exang"] + 0.6 * X["oldpeak"] + 0.6 * np.minimum(X["ca"], 3) - 0.02 * (X["thalach"] - 150)
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit.to_numpy()))).astype(int)
    X.iloc[1] = X.iloc[0]
    y[1] = y[0]
    groups = X.groupby(h2.r4.FEATURES).ngroup().to_numpy()
    return X, y, groups


SMALL = dict(n_repeats=2, c_grid=(0.1, 1.0), n_outer=3, n_inner=3, n_inner_cal=2, n_cal=3)


# --- Metrics --------------------------------------------------------------------

def _calibrated_sample(n=20000, seed=1):
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.02, 0.98, n)
    return (rng.uniform(size=n) < p).astype(int), p


def test_slope_estimator_emits_no_deprecation_warning():
    y, p = _calibrated_sample(2000)
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # any FutureWarning/DeprecationWarning fails the test
        h2.calibration_slope(y, p)
    src = (ROOT / "experiments" / "h2_calibration_recipe.py").read_text(encoding="utf-8")
    assert "penalty=None" not in src.replace("deprecated penalty=None", "")


def test_slope_detects_under_and_over_confidence():
    y, p = _calibrated_sample()
    logit = np.log(p / (1 - p))
    under = 1 / (1 + np.exp(-0.6 * logit))       # compressed toward 0.5 -> slope > 1
    over = 1 / (1 + np.exp(-1.6 * logit))        # too extreme -> slope < 1
    assert h2.calibration_slope(y, p) == pytest.approx(1.0, abs=0.06)
    assert h2.calibration_slope(y, under) > 1.4
    assert h2.calibration_slope(y, over) < 0.75


def test_calibration_intercept_and_in_the_large():
    y, p = _calibrated_sample()
    assert h2.calibration_intercept(y, p) == pytest.approx(0.0, abs=0.06)
    logit = np.log(p / (1 - p))
    too_low = 1 / (1 + np.exp(-(logit - 0.7)))   # systematically under-predicts -> intercept ~ +0.7
    assert h2.calibration_intercept(y, too_low) == pytest.approx(0.7, abs=0.08)
    m = h2.metrics(y, too_low)
    assert m["calibration_in_the_large"] > 0 and m["abs_slope_minus_1"] == pytest.approx(abs(m["calibration_slope"] - 1))


# --- Arms --------------------------------------------------------------------------

@pytest.mark.parametrize("arm,weight,n_members", [
    ("A_production", "balanced", 3), ("B_no_class_weight", None, 3),
    ("C_pooled_oof_calibration", "balanced", 1), ("D_both", None, 1),
])
def test_arm_configuration(arm, weight, n_members):
    X, y, g = _synthetic()
    model = h2.fit_arm(arm, 0.1, X, y, g, n_splits=3, seed=7)
    assert len(model.calibrated_classifiers_) == n_members          # ensemble=True -> one member per fold
    base = model.calibrated_classifiers_[0].estimator.named_steps["model"]
    assert base.class_weight == weight and base.C == 0.1
    assert model.method == "sigmoid"


def test_calibration_never_uses_outer_test_labels():
    """Predictions for an outer test fold must not change when that fold's labels change."""
    from sklearn.model_selection import StratifiedGroupKFold
    X, y, g = _synthetic()
    tr, te = next(StratifiedGroupKFold(3, shuffle=True, random_state=1000).split(X, y, g))
    y_perturbed = y.copy()
    y_perturbed[te] = 1 - y_perturbed[te]
    for arm in h2.ARMS:
        a = h2.fit_arm(arm, 0.1, X.iloc[tr], y[tr], g[tr], 3, 3000).predict_proba(X.iloc[te])[:, 1]
        b = h2.fit_arm(arm, 0.1, X.iloc[tr], y_perturbed[tr], g[tr], 3, 3000).predict_proba(X.iloc[te])[:, 1]
        assert np.array_equal(a, b), arm
        c = h2.select_C(arm, X.iloc[tr], y[tr], g[tr], (0.1, 1.0), 2000, 3, 2)
        d = h2.select_C(arm, X.iloc[tr], y_perturbed[tr], g[tr], (0.1, 1.0), 2000, 3, 2)
        assert c == d


# --- Repeated CV -------------------------------------------------------------------

def test_repeated_cv_identical_splits_complete_and_deterministic():
    X, y, g = _synthetic()
    a = h2.run_repeated_cv(X, y, g, **SMALL)
    b = h2.run_repeated_cv(X, y, g, **SMALL)
    assert a["outer_test_folds"] == b["outer_test_folds"]
    for arm in h2.ARMS:
        assert not np.isnan(a["oof"][arm]).any()                      # every patient predicted in every repeat
        assert np.array_equal(a["oof"][arm], b["oof"][arm]) and a["chosen_C"][arm] == b["chosen_C"][arm]
    for folds in a["outer_test_folds"]:                               # outer folds partition the patients
        flat = sorted(i for f in folds for i in f)
        assert flat == list(range(len(y)))
        for f in folds:                                               # duplicates never split
            assert not ({0, 1} & set(f)) or {0, 1} <= set(f)


def test_fixed_C_analysis_uses_production_C():
    X, y, g = _synthetic()
    run = h2.run_repeated_cv(X, y, g, tune=False, fixed_C=0.1, **{k: v for k, v in SMALL.items() if k != "c_grid"})
    assert all(set(c) == {0.1} for c in run["chosen_C"].values())


def test_summary_bootstrap_and_verdict_structure():
    X, y, g = _synthetic()
    run = h2.run_repeated_cv(X, y, g, **SMALL)
    s = h2.summarise(y, g, run, bootstrap=True, n_bootstrap=30)
    diffs = s["paired_group_bootstrap"]["differences"]
    assert set(diffs) == {"B_no_class_weight", "C_pooled_oof_calibration", "D_both"}
    for arm, d in diffs.items():
        for k in ("roc_auc", "log_loss", "abs_slope_minus_1"):
            assert d[k]["ci_bonferroni_low"] <= d[k]["ci95_low"] <= d[k]["mean"] <= d[k]["ci95_high"] <= d[k]["ci_bonferroni_high"]
        assert len(s["per_repeat_differences_vs_baseline"][arm]["log_loss"]["per_repeat"]) == SMALL["n_repeats"]
    assert set(s["verdict"]["per_arm"]) == set(diffs)


def _d(auc_low, slope_mean, slope_high, ll_mean, ll_high):
    return {"roc_auc": {"ci95_low": auc_low}, "abs_slope_minus_1": {"mean": slope_mean, "ci95_high": slope_high},
            "log_loss": {"mean": ll_mean, "ci95_high": ll_high}}


@pytest.mark.parametrize("d,expected", [
    (_d(-0.005, -0.10, -0.02, -0.004, 0.003), True),     # slope improved, log loss not worse
    (_d(-0.005, -0.01, 0.05, -0.006, -0.001), True),     # log loss improved
    (_d(-0.020, -0.10, -0.02, -0.004, -0.001), False),   # AUC guardrail fails
    (_d(-0.005, -0.10, -0.02, 0.002, 0.010), False),     # log loss worsened (point estimate)
    (_d(-0.005, 0.01, 0.05, 0.001, 0.004), False),       # nothing improved
])
def test_preregistered_rule(d, expected):
    assert h2.arm_verdict(d)["improves_calibration"] is expected


# --- Isolation ---------------------------------------------------------------------

def test_reuses_r4_loader_and_never_touches_production():
    assert h2.r4.load_development_data is not None and h2.r4.CONTINUOUS == ["age", "trestbps", "chol", "thalach", "oldpeak"]
    tree = ast.parse((ROOT / "experiments" / "h2_calibration_recipe.py").read_text(encoding="utf-8"))
    calls = {f"{n.func.value.id}.{n.func.attr}" for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)}
    assert not {"joblib.dump", "joblib.load", "pickle.dump", "pickle.load"} & calls
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not any(m.startswith(("cardiovanta_ml.registry", "cardiovanta_ml.inference", "backend")) for m in modules)
    assert h2.RESULTS == ROOT / "experiments" / "results" / "h2_calibration_recipe.json"
