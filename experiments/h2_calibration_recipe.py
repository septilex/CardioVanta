"""
CardioVanta H2 (research only): calibration of the production training recipe.

Pre-registered design: openspec/changes/h2-calibration-recipe/design.md

Arms (identical preprocessing and outer splits):
  A  production  class_weight="balanced", CalibratedClassifierCV(sigmoid, ensemble=True)
  B  no weight   class_weight=None,       ensemble=True
  C  pooled OOF  class_weight="balanced", ensemble=False (one sigmoid on pooled OOF decision values)
  D  both        class_weight=None,       ensemble=False

Protocol:
* Only the 242 development rows are used, through the R4 loader, which parses only
  development-row lines and verifies provenance hashes. Locked lines are never parsed.
* Duplicate-aware StratifiedGroupKFold everywhere. Preprocessing, C tuning and calibration
  are fitted inside training data only, so calibration never sees outer-test labels.
* Deterministic seeds. Writes only experiments/results/h2_calibration_recipe.json.

Run:  python experiments/h2_calibration_recipe.py
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, Iterable, Sequence

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("r4_ca_count_encoding", PROJECT_ROOT / "experiments" / "r4_ca_count_encoding.py")
r4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r4)          # reuse the verified development-only loader and contract-derived columns

DESIGN = PROJECT_ROOT / "openspec" / "changes" / "h2-calibration-recipe" / "design.md"
RESULTS = PROJECT_ROOT / "experiments" / "results" / "h2_calibration_recipe.json"

ARMS: Dict[str, Dict] = {
    "A_production": {"class_weight": "balanced", "ensemble": True},
    "B_no_class_weight": {"class_weight": None, "ensemble": True},
    "C_pooled_oof_calibration": {"class_weight": "balanced", "ensemble": False},
    "D_both": {"class_weight": None, "ensemble": False},
}
BASELINE = "A_production"
C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
N_REPEATS, N_OUTER, N_INNER, N_INNER_CAL, N_CAL = 10, 5, 5, 3, 5
PRODUCTION_C = 0.1
N_BOOTSTRAP, BOOTSTRAP_SEED = 2000, 42
NON_INFERIORITY_AUC = -0.01
METRIC_KEYS = ("roc_auc", "pr_auc", "brier", "log_loss", "ece_10", "calibration_slope",
               "abs_slope_minus_1", "calibration_intercept", "calibration_in_the_large")
LOWER_IS_BETTER = {"brier", "log_loss", "ece_10", "abs_slope_minus_1"}


# =============================================================================
# Arms
# =============================================================================

def build_pipeline(class_weight, C: float) -> Pipeline:
    pre = ColumnTransformer([
        ("num", StandardScaler(), r4.CONTINUOUS),
        ("bin", "passthrough", r4.BINARY),
        ("cat", OneHotEncoder(handle_unknown="ignore"), r4.CATEGORICAL),
    ], remainder="drop")
    model = LogisticRegression(C=C, class_weight=class_weight, solver="lbfgs", max_iter=2000, random_state=42)
    return Pipeline([("preprocessor", pre), ("model", model)])


def fit_arm(arm: str, C: float, X, y, groups, n_splits: int, seed: int) -> CalibratedClassifierCV:
    """Calibrated model for one arm, fitted ONLY on (X, y). Calibration splits are duplicate-aware."""
    cfg = ARMS[arm]
    X = X.reset_index(drop=True)
    splits = list(StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(X, y, groups))
    model = CalibratedClassifierCV(estimator=build_pipeline(cfg["class_weight"], C), method="sigmoid",
                                   cv=splits, ensemble=cfg["ensemble"])
    return model.fit(X, y)


# =============================================================================
# Metrics
# =============================================================================

def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    return np.log(p / (1 - p))


def calibration_slope(y, p) -> float:
    """Slope of an unpenalized logistic regression of y on logit(p).

    Uses C=np.inf, the scikit-learn 1.9 replacement for the deprecated penalty=None.
    """
    lr = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=5000).fit(_logit(p).reshape(-1, 1), np.asarray(y))
    return float(lr.coef_[0][0])


def calibration_intercept(y, p, iters: int = 50) -> float:
    """Intercept a maximising the likelihood of sigmoid(a + logit p) with slope fixed at 1 (Newton-Raphson)."""
    y, z, a = np.asarray(y, dtype=float), _logit(p), 0.0
    for _ in range(iters):
        q = 1 / (1 + np.exp(-(a + z)))
        grad, hess = np.sum(y - q), np.sum(q * (1 - q))
        step = grad / hess
        a += step
        if abs(step) < 1e-12:
            break
    return float(a)


def expected_calibration_error(y, p, n_bins: int = 10) -> float:
    y, p = np.asarray(y), np.asarray(p)
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    return float(sum((bins == b).mean() * abs(y[bins == b].mean() - p[bins == b].mean())
                     for b in range(n_bins) if (bins == b).any()))


def metrics(y, p) -> Dict[str, float]:
    y, p = np.asarray(y), np.asarray(p)
    slope = calibration_slope(y, p)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.clip(p, 1e-15, 1 - 1e-15), labels=[0, 1])),
        "ece_10": expected_calibration_error(y, p),
        "calibration_slope": slope,
        "abs_slope_minus_1": abs(slope - 1.0),
        "calibration_intercept": calibration_intercept(y, p),
        "calibration_in_the_large": float(y.mean() - p.mean()),
    }


# =============================================================================
# Repeated nested CV
# =============================================================================

def select_C(arm: str, X, y, groups, c_grid: Iterable[float], seed: int, n_inner: int, n_inner_cal: int) -> float:
    """Inner CV on the outer-training partition: lowest OOF log loss of the arm's calibrated model."""
    X = X.reset_index(drop=True)
    y, groups = np.asarray(y), np.asarray(groups)
    inner = list(StratifiedGroupKFold(n_splits=n_inner, shuffle=True, random_state=seed).split(X, y, groups))
    scores = []
    for C in sorted(c_grid):
        oof = np.zeros(len(y))
        for tr, va in inner:
            oof[va] = fit_arm(arm, C, X.iloc[tr], y[tr], groups[tr], n_inner_cal, seed).predict_proba(X.iloc[va])[:, 1]
        scores.append((round(log_loss(y, np.clip(oof, 1e-15, 1 - 1e-15), labels=[0, 1]), 12), C))
    best = min(scores)[0]
    return min(C for s, C in scores if s == best)


def run_repeated_cv(X, y, groups, *, arms: Sequence[str] = tuple(ARMS), n_repeats: int = N_REPEATS,
                    c_grid=C_GRID, tune: bool = True, fixed_C: float = PRODUCTION_C, n_outer: int = N_OUTER,
                    n_inner: int = N_INNER, n_inner_cal: int = N_INNER_CAL, n_cal: int = N_CAL) -> Dict:
    """Out-of-fold predictions per arm and repeat. Outer splits are identical for every arm."""
    X = X.reset_index(drop=True)
    y, groups = np.asarray(y), np.asarray(groups)
    oof = {arm: np.full((n_repeats, len(y)), np.nan) for arm in arms}
    chosen = {arm: [] for arm in arms}
    outer_splits = []
    for r in range(n_repeats):
        splits = list(StratifiedGroupKFold(n_splits=n_outer, shuffle=True, random_state=1000 + r).split(X, y, groups))
        outer_splits.append([te.tolist() for _, te in splits])
        for tr, te in splits:
            Xtr, ytr, gtr = X.iloc[tr], y[tr], groups[tr]
            for arm in arms:
                C = select_C(arm, Xtr, ytr, gtr, c_grid, 2000 + r, n_inner, n_inner_cal) if tune else fixed_C
                chosen[arm].append(C)
                oof[arm][r, te] = fit_arm(arm, C, Xtr, ytr, gtr, n_cal, 3000 + r).predict_proba(X.iloc[te])[:, 1]
    return {"oof": oof, "chosen_C": chosen, "outer_test_folds": outer_splits}


# =============================================================================
# Uncertainty and verdicts
# =============================================================================

def per_repeat_metrics(y, oof_arm) -> Dict[str, np.ndarray]:
    rows = [metrics(y, oof_arm[r]) for r in range(oof_arm.shape[0])]
    return {k: np.array([m[k] for m in rows]) for k in METRIC_KEYS}


def paired_bootstrap(y, groups, oof: Dict[str, np.ndarray], arms: Sequence[str], baseline: str,
                     n_bootstrap: int = N_BOOTSTRAP, seed: int = BOOTSTRAP_SEED) -> Dict:
    """
    Resample duplicate groups. In each resample, compute every metric PER REPEAT on the
    resampled patients and average over repeats. Probabilities are not averaged across
    repeats, which avoids inflating the calibration slope. Differences are paired (arm - baseline).
    """
    y, groups = np.asarray(y), np.asarray(groups)
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    members = {g: np.flatnonzero(groups == g) for g in unique}
    keys = ("roc_auc", "log_loss", "abs_slope_minus_1", "calibration_slope", "brier", "ece_10", "calibration_intercept")
    draws = {arm: {k: [] for k in keys} for arm in arms if arm != baseline}
    n_used = 0
    for _ in range(n_bootstrap):
        idx = np.concatenate([members[g] for g in rng.choice(unique, size=len(unique), replace=True)])
        yb = y[idx]
        if yb.min() == yb.max():
            continue
        n_used += 1
        avg = {}
        for arm in arms:
            ms = [metrics(yb, oof[arm][r, idx]) for r in range(oof[arm].shape[0])]
            avg[arm] = {k: float(np.mean([m[k] for m in ms])) for k in keys}
        for arm in draws:
            for k in keys:
                draws[arm][k].append(avg[arm][k] - avg[baseline][k])
    bonf = 100 * (0.05 / max(1, len(draws))) / 2
    out = {}
    for arm, ks in draws.items():
        out[arm] = {k: {"mean": float(np.mean(v)), "ci95_low": float(np.percentile(v, 2.5)),
                        "ci95_high": float(np.percentile(v, 97.5)),
                        "ci_bonferroni_low": float(np.percentile(v, bonf)),
                        "ci_bonferroni_high": float(np.percentile(v, 100 - bonf))} for k, v in ks.items()}
    return {"n_resamples": n_used, "bonferroni_level": 1 - 0.05 / max(1, len(draws)), "differences": out}


def arm_verdict(d: Dict, low="ci95_low", high="ci95_high") -> Dict:
    """Pre-registered rule (design.md)."""
    guard = d["roc_auc"][low] >= NON_INFERIORITY_AUC
    improves = d["abs_slope_minus_1"][high] < 0 or d["log_loss"][high] < 0
    not_worse = d["abs_slope_minus_1"]["mean"] <= 0 and d["log_loss"]["mean"] <= 0
    return {"guardrail_auc_non_inferior": bool(guard), "primary_improved": bool(improves),
            "no_primary_worsened": bool(not_worse), "improves_calibration": bool(guard and improves and not_worse)}


def verdicts(boot: Dict, arm_means: Dict[str, Dict]) -> Dict:
    out = {}
    for arm, d in boot["differences"].items():
        v95 = arm_verdict(d)
        vb = arm_verdict(d, "ci_bonferroni_low", "ci_bonferroni_high")
        v95["robust_to_multiplicity"] = bool(v95["improves_calibration"] and vb["improves_calibration"])
        out[arm] = v95
    qualifying = [a for a, v in out.items() if v["improves_calibration"]]
    preferred = min(qualifying, key=lambda a: arm_means[a]["log_loss"]) if qualifying else None
    return {"per_arm": out, "qualifying_arms": qualifying, "preferred_arm": preferred,
            "rule": "dAUC CI low >= -0.01 AND (d|slope-1| CI high < 0 OR dLogLoss CI high < 0) "
                    "AND point estimates of d|slope-1| and dLogLoss <= 0"}


def summarise(y, groups, run: Dict, *, bootstrap: bool, n_bootstrap: int = N_BOOTSTRAP) -> Dict:
    oof = run["oof"]
    arms = list(oof)
    per_rep = {arm: per_repeat_metrics(y, oof[arm]) for arm in arms}
    summary = {"arms": {}, "per_repeat_differences_vs_baseline": {}}
    for arm in arms:
        summary["arms"][arm] = {
            "config": ARMS[arm],
            "mean": {k: float(v.mean()) for k, v in per_rep[arm].items()},
            "p2_5": {k: float(np.percentile(v, 2.5)) for k, v in per_rep[arm].items()},
            "p97_5": {k: float(np.percentile(v, 97.5)) for k, v in per_rep[arm].items()},
            "per_repeat": {k: [float(x) for x in v] for k, v in per_rep[arm].items()},
            "prediction_stability_mean_sd": float(np.nanstd(oof[arm], axis=0).mean()),
            "chosen_C_counts": {str(c): int(n) for c, n in zip(*np.unique(run["chosen_C"][arm], return_counts=True))},
        }
        if arm != BASELINE and BASELINE in per_rep:
            diffs = {}
            for k in METRIC_KEYS:
                d = per_rep[arm][k] - per_rep[BASELINE][k]
                better = (d < 0) if k in LOWER_IS_BETTER else (d > 0)
                diffs[k] = {"mean": float(d.mean()), "p2_5": float(np.percentile(d, 2.5)),
                            "p97_5": float(np.percentile(d, 97.5)), "repeats_favouring_arm": int(better.sum()),
                            "per_repeat": [float(x) for x in d]}
            summary["per_repeat_differences_vs_baseline"][arm] = diffs
    if bootstrap:
        boot = paired_bootstrap(y, groups, oof, arms, BASELINE, n_bootstrap)
        summary["paired_group_bootstrap"] = boot
        summary["verdict"] = verdicts(boot, {a: summary["arms"][a]["mean"] for a in arms})
    return summary


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=RESULTS)
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    t0 = time.time()
    X, y, groups = r4.load_development_data()
    primary = run_repeated_cv(X, y, groups, tune=True)
    secondary = run_repeated_cv(X, y, groups, tune=False, fixed_C=PRODUCTION_C)
    if primary["outer_test_folds"] != secondary["outer_test_folds"]:
        raise RuntimeError("Outer splits differ between analyses")
    result = {
        "experiment": "H2: calibration of the production recipe (research only)",
        "preregistered_design": {"path": "openspec/changes/h2-calibration-recipe/design.md", "sha256": sha256_file(DESIGN)},
        "data": {"development_rows": int(len(y)), "locked_rows_parsed": 0,
                 "unique_duplicate_groups": int(len(np.unique(groups))), "disease_prevalence": float(np.mean(y)),
                 "target_orientation": "disease = 1 - heart.csv target", "loader": "experiments/r4_ca_count_encoding.py"},
        "protocol": {"arms": ARMS, "baseline": BASELINE, "repeats": N_REPEATS, "outer_folds": N_OUTER,
                     "inner_folds": N_INNER, "inner_calibration_folds": N_INNER_CAL, "final_calibration_folds": N_CAL,
                     "C_grid": list(C_GRID), "outer_splits_identical_across_arms": True,
                     "outer_test_folds_sha256": hashlib.sha256(json.dumps(primary["outer_test_folds"]).encode()).hexdigest(),
                     "bootstrap": {"n": N_BOOTSTRAP, "seed": BOOTSTRAP_SEED, "unit": "duplicate group",
                                   "metric_aggregation": "per repeat, then averaged over repeats"},
                     "slope_estimator": "LogisticRegression(C=np.inf) on logit(p)  (replaces deprecated penalty=None)"},
        "primary_nested_tuned_C": summarise(y, groups, primary, bootstrap=True),
        "secondary_fixed_C_0_1": summarise(y, groups, secondary, bootstrap=False),
        "runtime_seconds": round(time.time() - t0, 1),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"verdict": result["primary_nested_tuned_C"]["verdict"], "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
