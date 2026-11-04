"""
R4 synthetic regression tests (no dataset is read).

Covers the count encoder, the development-only loader (locked lines never parsed),
arm construction, duplicate-aware fold integrity, determinism, metric correctness,
the pre-registered decision rule, and isolation from production artifacts.
"""
import ast
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("r4", ROOT / "experiments" / "r4_ca_count_encoding.py")
r4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r4)

COLUMNS = r4.FEATURES + ["target"]


def _synthetic(n=90, seed=0):
    """Synthetic patients drawn from the contract's accepted codes and plausible ranges."""
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({
        "age": rng.uniform(30, 75, n), "sex": rng.integers(0, 2, n), "cp": rng.integers(0, 4, n),
        "trestbps": rng.uniform(95, 190, n), "chol": rng.uniform(130, 400, n), "fbs": rng.integers(0, 2, n),
        "restecg": rng.integers(0, 3, n), "thalach": rng.uniform(80, 200, n), "exang": rng.integers(0, 2, n),
        "oldpeak": rng.uniform(0, 5, n), "slope": rng.integers(0, 3, n), "ca": rng.choice([0, 1, 2, 3, 4], n, p=[.5, .2, .15, .1, .05]),
        "thal": rng.integers(0, 4, n),
    })[r4.FEATURES].astype(float)
    logit = -1 + 0.8 * X["exang"] + 0.6 * X["oldpeak"] + 0.7 * np.minimum(X["ca"], 3) - 0.02 * (X["thalach"] - 150)
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    X.iloc[1] = X.iloc[0]          # a duplicate pair, to exercise duplicate-aware grouping
    y[1] = y[0]
    groups = X.groupby(r4.FEATURES).ngroup().to_numpy()
    return X.reset_index(drop=True), y, groups


# --- Encoder ------------------------------------------------------------------

def test_ca_count_encoder_maps_codes_and_indicator():
    enc = r4.CaCountEncoder().fit(np.array([[0], [1], [2], [3], [4]], dtype=float))
    out = enc.transform(np.array([[0], [3], [4]], dtype=float))
    count_raw = np.array([0, 3, 0])                          # code 4 -> count 0 + indicator
    assert np.allclose(out[:, 0], (count_raw - enc.mean_) / enc.scale_)
    assert out[:, 1].tolist() == [0.0, 0.0, 1.0]
    assert enc.mean_ == pytest.approx(np.mean([0, 1, 2, 3, 0]))
    assert list(enc.get_feature_names_out()) == ["ca_count", "ca_code4"]


def test_ca_count_encoder_is_fit_on_training_data_only():
    enc = r4.CaCountEncoder().fit(np.array([[0], [0], [0], [1]], dtype=float))
    assert enc.mean_ == 0.25                                  # statistics from fit data, not transform data
    enc.transform(np.array([[3], [3]], dtype=float))
    assert enc.mean_ == 0.25


@pytest.mark.parametrize("bad", [5, -1, 2.5])
def test_ca_count_encoder_rejects_codes_outside_contract(bad):
    with pytest.raises(ValueError, match="outside contract"):
        r4.CaCountEncoder().fit(np.array([[0], [bad]], dtype=float))


# --- Development-only loader ------------------------------------------------

def _write_csv(path, n_rows, locked):
    lines = [",".join(COLUMNS)]
    for i in range(n_rows):
        if i in locked:
            lines.append("LOCKED,ROW,MUST,NEVER,BE,PARSED,x,x,x,x,x,x,x,x")   # would break numeric parsing
        else:
            lines.append(",".join(["50", "1", "2", "130", "240", "0", "1", "150", "0", "1.0", "1", str(i % 5), "2", "1"]))
    path.write_text("﻿" + "\n".join(lines) + "\n", encoding="utf-8")


def test_loader_never_parses_locked_lines(tmp_path):
    csv_path = tmp_path / "synthetic.csv"
    locked = {1, 4, 7}
    _write_csv(csv_path, 10, locked)
    dev = [i for i in range(10) if i not in locked]
    df = r4.load_dev_rows(csv_path, dev, COLUMNS)
    assert list(df.index) == dev and len(df) == 7
    assert df.dtypes.map(lambda t: np.issubdtype(t, np.number)).all()


def test_loader_rejects_bad_header_duplicates_and_missing_rows(tmp_path):
    csv_path = tmp_path / "synthetic.csv"
    _write_csv(csv_path, 5, set())
    with pytest.raises(ValueError, match="header"):
        r4.load_dev_rows(csv_path, [0], list(reversed(COLUMNS)))
    with pytest.raises(ValueError, match="duplicates"):
        r4.load_dev_rows(csv_path, [0, 0], COLUMNS)
    with pytest.raises(ValueError, match="Missing development rows"):
        r4.load_dev_rows(csv_path, [0, 99], COLUMNS)


# --- Arms ---------------------------------------------------------------------

def test_arms_differ_only_in_ca_encoding():
    X, y, _ = _synthetic()
    base = r4.build_pipeline("baseline_onehot_ca", 0.1).fit(X, y)
    cand = r4.build_pipeline("candidate_count_ca", 0.1).fit(X, y)
    bn = list(base.named_steps["preprocessor"].get_feature_names_out())
    cn = list(cand.named_steps["preprocessor"].get_feature_names_out())
    assert [n for n in bn if "ca_" not in n or n.startswith("cat__cp")] == [n for n in cn if not n.startswith("ca__")]
    assert sum(n.startswith("cat__ca_") for n in bn) == 5
    assert [n for n in cn if n.startswith("ca__")] == ["ca__ca_count", "ca__ca_code4"]
    for pipe in (base, cand):
        m = pipe.named_steps["model"]
        assert m.C == 0.1 and m.class_weight == "balanced"
    with pytest.raises(ValueError):
        r4.build_pipeline("unknown", 0.1)


# --- Nested CV ------------------------------------------------------------------

SMALL = dict(n_repeats=2, c_grid=(0.1, 1.0), n_outer=3, n_inner=3, n_inner_cal=2, n_cal=3)


def test_repeated_cv_is_deterministic_and_complete():
    X, y, g = _synthetic()
    a = r4.run_repeated_cv(X, y, g, **SMALL)
    b = r4.run_repeated_cv(X, y, g, **SMALL)
    for arm in r4.ARMS:
        assert np.array_equal(a["oof"][arm], b["oof"][arm])
        assert a["chosen_C"][arm] == b["chosen_C"][arm]
        assert np.all((a["oof"][arm] > 0) & (a["oof"][arm] < 1))   # every patient predicted in every repeat
        assert len(a["chosen_C"][arm]) == SMALL["n_repeats"] * SMALL["n_outer"]


def test_duplicate_rows_never_split_across_train_and_test():
    from sklearn.model_selection import StratifiedGroupKFold
    X, y, g = _synthetic()
    assert g[0] == g[1]
    for r in range(3):
        for tr, te in StratifiedGroupKFold(3, shuffle=True, random_state=1000 + r).split(X, y, g):
            assert set(g[tr]).isdisjoint(set(g[te]))


def test_fixed_C_arm_uses_production_value():
    X, y, g = _synthetic()
    run = r4.run_repeated_cv(X, y, g, tune=False, fixed_C=0.1, **{k: v for k, v in SMALL.items() if k != "c_grid"})
    assert set(run["chosen_C"]["baseline_onehot_ca"]) == {0.1} == set(run["chosen_C"]["candidate_count_ca"])


# --- Metrics and decision rule ---------------------------------------------------

def test_metrics_on_perfectly_calibrated_synthetic_scores():
    rng = np.random.default_rng(1)
    p = rng.uniform(0.02, 0.98, 20000)
    y = (rng.uniform(size=p.size) < p).astype(int)
    m = r4.metrics(y, p)
    assert m["calibration_slope"] == pytest.approx(1.0, abs=0.06)
    assert abs(m["calibration_in_the_large"]) < 0.01 and m["ece_10"] < 0.02
    assert 0.5 < m["roc_auc"] < 1


def test_summary_and_paired_bootstrap_shapes():
    X, y, g = _synthetic()
    run = r4.run_repeated_cv(X, y, g, **SMALL)
    s = r4.summarise(y, g, run, n_bootstrap=50)
    boot = s["difference_candidate_minus_baseline"]["paired_group_bootstrap"]
    assert set(boot) == {"roc_auc", "brier", "log_loss", "ece_10"}
    for v in boot.values():
        assert v["ci95_low"] <= v["mean"] <= v["ci95_high"]
    assert set(s["arms"]) == set(r4.ARMS)


@pytest.mark.parametrize("auc_low,ll_high,brier_high,expected", [
    (-0.005, -0.001, 0.002, True),     # non-inferior AUC, log loss improved
    (-0.005, 0.003, -0.0001, True),    # non-inferior AUC, Brier improved
    (-0.02, -0.01, -0.01, False),      # AUC not non-inferior
    (0.0, 0.001, 0.001, False),        # calibration not improved
])
def test_preregistered_decision_rule(auc_low, ll_high, brier_high, expected):
    fake = {"difference_candidate_minus_baseline": {"paired_group_bootstrap": {
        "roc_auc": {"ci95_low": auc_low}, "log_loss": {"ci95_high": ll_high}, "brier": {"ci95_high": brier_high}}}}
    assert r4.verdict(fake)["h1_supported"] is expected


# --- Isolation from production ------------------------------------------------------

def test_experiment_never_writes_or_loads_production_artifacts():
    src = (ROOT / "experiments" / "r4_ca_count_encoding.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = {f"{n.func.value.id}.{n.func.attr}" for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)}
    assert not {"joblib.dump", "joblib.load", "pickle.dump", "pickle.load"} & calls
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    modules |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m.startswith(("cardiovanta_ml.registry", "cardiovanta_ml.inference", "backend", "src.inference"))
                   for m in modules), modules
    assert "cardiovanta_ml.contracts" in modules  # read-only feature definitions only
    assert r4.RESULTS == ROOT / "experiments" / "results" / "r4_ca_count_encoding.json"
    assert r4.PRODUCTION_METADATA.name == "metadata.json"  # read-only provenance check only
