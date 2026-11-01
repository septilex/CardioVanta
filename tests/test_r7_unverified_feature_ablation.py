"""
R7 synthetic tests (no dataset is read).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments"))     # importable by name so worker processes can unpickle tasks
import r7_unverified_feature_ablation as r7       # noqa: E402

SRC = (ROOT / "experiments" / "r7_unverified_feature_ablation.py").read_text(encoding="utf-8")


def _synthetic(n=96, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({
        "age": rng.uniform(30, 75, n), "sex": rng.integers(0, 2, n), "cp": rng.integers(0, 4, n),
        "trestbps": rng.uniform(95, 190, n), "chol": rng.uniform(130, 400, n), "fbs": rng.integers(0, 2, n),
        "restecg": rng.integers(0, 3, n), "thalach": rng.uniform(80, 200, n), "exang": rng.integers(0, 2, n),
        "oldpeak": rng.uniform(0, 5, n), "slope": rng.integers(0, 3, n), "ca": rng.choice([0, 1, 2, 3, 4], n, p=[.5, .2, .15, .1, .05]),
        "thal": rng.integers(0, 4, n),
    })[r7.r4.FEATURES].astype(float)
    logit = -1 + 0.9 * X["exang"] + 0.6 * X["oldpeak"] + 0.5 * (X["thal"] == 3) - 0.02 * (X["thalach"] - 150)
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit.to_numpy()))).astype(int)
    X.iloc[1] = X.iloc[0]
    y[1] = y[0]
    groups = X.groupby(r7.r4.FEATURES).ngroup().to_numpy()
    return X, y, groups


SMALL = dict(n_repeats=2, c_grid=(0.1, 1.0), n_outer=3, n_inner=3, n_inner_cal=2, n_cal=3)


@pytest.fixture(scope="module")
def data():
    return _synthetic()


@pytest.fixture(scope="module")
def small_run(data):
    X, y, g = data
    return r7.run_repeated_cv(X, y, g, **SMALL)


# --- Arms ------------------------------------------------------------------------

def test_arms_remove_only_the_preregistered_features():
    assert r7.arm_features("A_baseline") == list(r7.r4.FEATURES) and len(r7.r4.FEATURES) == 13
    expected = {"B_no_slope": {"slope"}, "C_no_thal": {"thal"}, "D_no_ca": {"ca"}, "E_no_slope_thal_ca": {"slope", "thal", "ca"}}
    for arm, removed in expected.items():
        assert set(r7.r4.FEATURES) - set(r7.arm_features(arm)) == removed
        assert set(removed) <= set(r7.UNRESOLVED)
    assert len(r7.arm_features("E_no_slope_thal_ca")) == 10
    assert r7.BASELINE == "A_baseline" and list(r7.ARMS) == ["A_baseline", *expected]


def test_baseline_uses_the_production_recipe(data):
    X, y, g = data
    pipe = r7.build_pipeline("A_baseline", 0.1).fit(X, y)
    model = pipe.named_steps["model"]
    assert model.class_weight == "balanced" and model.C == 0.1 and model.solver == "lbfgs"
    names = list(pipe.named_steps["preprocessor"].get_feature_names_out())
    assert len(names) == 5 + 3 + (4 + 3 + 3 + 5 + 4)          # one-hot keeps every code, including ca=4 and thal=0
    cal = r7.fit_arm("A_baseline", 0.1, X, y, g, 3, 0)
    assert cal.method == "sigmoid" and cal.ensemble is True


def test_ablated_pipeline_has_no_columns_of_removed_features(data):
    X, y, _ = data
    names = list(r7.build_pipeline("E_no_slope_thal_ca", 0.1).fit(X, y).named_steps["preprocessor"].get_feature_names_out())
    source_features = {n.split("__", 1)[1].rsplit("_", 1)[0] if n.startswith("cat__") else n.split("__", 1)[1] for n in names}
    assert not source_features & {"slope", "thal", "ca"} and "thalach" in source_features
    assert len(names) == 5 + 3 + (4 + 3)


@pytest.mark.parametrize("arm", ["B_no_slope", "C_no_thal", "D_no_ca", "E_no_slope_thal_ca"])
def test_predictions_invariant_to_removed_feature_values(data, arm):
    X, y, g = data
    tr, te = np.arange(0, 70), np.arange(70, len(y))
    base, _ = r7.fold_predictions(arm, X, y, g, tr, te, 0, tune=True, fixed_C=0.1, c_grid=(0.1, 1.0),
                                  n_inner=3, n_inner_cal=2, n_cal=3)
    Xp = X.copy()
    rng = np.random.default_rng(7)
    for f in r7.ARMS[arm]:
        Xp[f] = rng.permutation(Xp[f].to_numpy())
    pert, _ = r7.fold_predictions(arm, Xp, y, g, tr, te, 0, tune=True, fixed_C=0.1, c_grid=(0.1, 1.0),
                                  n_inner=3, n_inner_cal=2, n_cal=3)
    np.testing.assert_array_equal(base, pert)


def test_test_fold_labels_do_not_affect_its_predictions(data):
    X, y, g = data
    tr, te = r7.outer_splits(X, y, g, 0, 3)[0]
    a, _ = r7.fold_predictions("C_no_thal", X, y, g, tr, te, 0, tune=True, fixed_C=0.1, c_grid=(0.1, 1.0),
                               n_inner=3, n_inner_cal=2, n_cal=3)
    y2 = y.copy()
    y2[te] = 1 - y2[te]
    b, _ = r7.fold_predictions("C_no_thal", X, y2, g, tr, te, 0, tune=True, fixed_C=0.1, c_grid=(0.1, 1.0),
                               n_inner=3, n_inner_cal=2, n_cal=3)
    np.testing.assert_array_equal(a, b)


# --- Splits, determinism and parallel execution ------------------------------------

def test_outer_splits_are_duplicate_aware_and_shared(data, small_run):
    X, y, g = data
    for r, folds in enumerate(small_run["outer_test_folds"]):
        assert sorted(i for f in folds for i in f) == list(range(len(y)))
        for f in folds:
            assert not set(g[f]) & set(np.delete(g, f))       # no duplicate group straddles train/test
        assert folds == [te.tolist() for _, te in r7.outer_splits(X, y, g, r, 3)]
    assert set(small_run["oof"]) == set(r7.ARMS)
    for arm, P in small_run["oof"].items():
        assert P.shape == (2, len(y)) and np.isfinite(P).all() and ((P > 0) & (P < 1)).all()


def test_run_is_deterministic_and_parallel_equals_sequential(data, small_run):
    X, y, g = data
    par = r7.run_repeated_cv(X, y, g, n_jobs=2, **SMALL)
    for arm in r7.ARMS:
        np.testing.assert_array_equal(small_run["oof"][arm], par["oof"][arm])
    assert small_run["chosen_C"] == par["chosen_C"] and small_run["outer_test_folds"] == par["outer_test_folds"]


def test_bootstrap_is_job_independent_and_zero_for_identical_arms(data, small_run):
    X, y, g = data
    oof = {"A_baseline": small_run["oof"]["A_baseline"], "B_no_slope": small_run["oof"]["A_baseline"].copy(),
           "C_no_thal": small_run["oof"]["C_no_thal"]}
    b1 = r7.paired_bootstrap(y, g, oof, n_bootstrap=40, n_jobs=1)
    b2 = r7.paired_bootstrap(y, g, oof, n_bootstrap=40, n_jobs=3)
    assert b1 == b2
    for k in r7.METRIC_KEYS:
        d = b1["differences"]["B_no_slope"][k]
        assert d["ci95_low"] == d["ci95_high"] == 0.0
        c = b1["differences"]["C_no_thal"][k]
        assert c["ci_bonferroni_low"] <= c["ci95_low"] <= c["mean"] <= c["ci95_high"] <= c["ci_bonferroni_high"]
    assert b1["bonferroni_level"] == pytest.approx(0.975)


def test_summary_reports_every_required_metric_with_intervals(data, small_run):
    X, y, g = data
    s = r7.summarise(y, g, small_run, bootstrap=True, n_bootstrap=30)
    for k in ("roc_auc", "pr_auc", "log_loss", "brier", "calibration_slope"):
        for arm in r7.ARMS:
            assert {"ci95_low", "ci95_high"} <= set(s["paired_group_bootstrap"]["absolute"][arm][k])
        for arm in list(r7.ARMS)[1:]:
            assert {"ci95_low", "ci95_high", "ci_bonferroni_low"} <= set(s["paired_group_bootstrap"]["differences"][arm][k])
            assert len(s["per_repeat_differences_vs_baseline"][arm][k]["per_repeat"]) == 2
    assert set(s["classification"]["per_arm"]) == set(list(r7.ARMS)[1:])
    assert {"H7_1_thal_dependence", "H7_4_combined_at_least_max_single"} <= set(s["classification"]["hypotheses"])


# --- Pre-registered classification -------------------------------------------------

def _d(auc_lo, auc_hi, ll_lo, ll_hi):
    return {"roc_auc": {"ci95_low": auc_lo, "ci95_high": auc_hi}, "log_loss": {"ci95_low": ll_lo, "ci95_high": ll_hi}}


@pytest.mark.parametrize("d,label", [
    (_d(-0.06, -0.02, 0.01, 0.05), "material_dependence"),
    (_d(-0.03, 0.01, 0.002, 0.03), "material_dependence"),       # log-loss CI excludes 0 on the harmful side
    (_d(-0.008, -0.001, -0.002, 0.004), "dependence_within_margin"),
    (_d(-0.005, 0.006, -0.008, 0.009), "non_inferior"),
    (_d(-0.02, 0.01, -0.01, 0.02), "inconclusive"),
    (_d(-0.005, 0.006, -0.01, 0.0101), "inconclusive"),          # log-loss CI upper bound just above the +0.01 margin
])
def test_classification_rule(d, label):
    assert r7.classify(d)["label"] == label


# --- Isolation and orientation ---------------------------------------------------------

def test_uses_only_the_verified_development_loader_and_disease_orientation():
    loader_src = (ROOT / "experiments" / "r4_ca_count_encoding.py").read_text(encoding="utf-8")
    assert 'y = (1 - df["target"].astype(int))' in loader_src and "locked lines never reach the parser" in loader_src
    assert "r4.load_development_data()" in SRC
    for forbidden in ("read_csv", "open(", "heart.csv\"", "dev_indices.json", "joblib.dump", "artifacts/", "to_csv"):
        assert forbidden not in SRC, forbidden
    assert r7.RESULTS.name == "r7_unverified_feature_ablation.json"


def test_no_clinical_meaning_or_recoding_in_source():
    lowered = SRC.lower()
    for term in ("fixed defect", "reversable", "reversible", "upsloping", "downsloping", "missing value", "replace("):
        assert term not in lowered, term


def test_slope_estimator_emits_no_deprecation_warning():
    rng = np.random.default_rng(1)
    p = rng.uniform(0.05, 0.95, 500)
    y = (rng.uniform(size=500) < p).astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        r7.h2.calibration_slope(y, p)
