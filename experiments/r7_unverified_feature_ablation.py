"""
CardioVanta R7 (research only): ablation of the unresolved categorical features slope, thal and ca.

Pre-registered design: openspec/changes/r7-unverified-feature-ablation/design.md

Arms (identical recipe, groups and outer splits; removed features are dropped before preprocessing):
  A_baseline           all 13 contract features (production recipe)
  B_no_slope           without slope
  C_no_thal            without thal
  D_no_ca              without ca
  E_no_slope_thal_ca   without all three

Protocol:
* Only the 242 development rows are used, through the R4 loader, which parses only
  development-row lines and verifies provenance hashes. Locked lines are never parsed.
* Disease-positive orientation (disease = 1 - heart.csv target), applied by the loader.
* Duplicate-aware StratifiedGroupKFold everywhere (groups from all 13 features, shared by every arm).
* Preprocessing, C tuning and sigmoid calibration are fitted only inside training partitions.
* Deterministic seeds. (repeat, arm) tasks may run in parallel processes; each task is a pure
  function of its seeds and results are assembled by index.
* No code is recoded or given a meaning. Writes only experiments/results/r7_unverified_feature_ablation.json.

Run:  python experiments/r7_unverified_feature_ablation.py [--jobs N]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


r4 = _load("r4_ca_count_encoding", "experiments/r4_ca_count_encoding.py")   # development-only loader, contract columns
h2 = _load("h2_calibration_recipe", "experiments/h2_calibration_recipe.py")  # metrics (non-deprecated slope estimator)

DESIGN = PROJECT_ROOT / "openspec" / "changes" / "r7-unverified-feature-ablation" / "design.md"
RESULTS = PROJECT_ROOT / "experiments" / "results" / "r7_unverified_feature_ablation.json"

UNRESOLVED = ("slope", "thal", "ca")
ARMS: Dict[str, Tuple[str, ...]] = {
    "A_baseline": (),
    "B_no_slope": ("slope",),
    "C_no_thal": ("thal",),
    "D_no_ca": ("ca",),
    "E_no_slope_thal_ca": ("slope", "thal", "ca"),
}
BASELINE = "A_baseline"
C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
N_REPEATS, N_OUTER, N_INNER, N_INNER_CAL, N_CAL = 10, 5, 5, 3, 5
PRODUCTION_C = 0.1
N_BOOTSTRAP, BOOTSTRAP_SEED = 2000, 42
NI_AUC_MARGIN, NI_LOGLOSS_MARGIN = -0.01, 0.01
METRIC_KEYS = h2.METRIC_KEYS
LOWER_IS_BETTER = h2.LOWER_IS_BETTER


# =============================================================================
# Arms
# =============================================================================

def arm_features(arm: str) -> List[str]:
    removed = ARMS[arm]
    return [f for f in r4.FEATURES if f not in removed]


def build_pipeline(arm: str, C: float) -> Pipeline:
    keep = arm_features(arm)
    pre = ColumnTransformer([
        ("num", StandardScaler(), [f for f in r4.CONTINUOUS if f in keep]),
        ("bin", "passthrough", [f for f in r4.BINARY if f in keep]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), [f for f in r4.CATEGORICAL if f in keep]),
    ], remainder="drop")
    model = LogisticRegression(C=C, class_weight="balanced", solver="lbfgs", max_iter=2000, random_state=42)
    return Pipeline([("preprocessor", pre), ("model", model)])


def fit_arm(arm: str, C: float, X, y, groups, n_splits: int, seed: int) -> CalibratedClassifierCV:
    """Production-recipe calibrated model for one arm, fitted only on (X, y); removed features dropped first."""
    X = X.reset_index(drop=True)
    splits = list(StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(X, y, groups))
    model = CalibratedClassifierCV(estimator=build_pipeline(arm, C), method="sigmoid", cv=splits, ensemble=True)
    return model.fit(X[arm_features(arm)], y)


def predict(model, arm: str, X) -> np.ndarray:
    return model.predict_proba(X[arm_features(arm)])[:, 1]


def select_C(arm: str, X, y, groups, c_grid: Iterable[float], seed: int, n_inner: int, n_inner_cal: int) -> float:
    """Inner CV on the outer-training partition: lowest OOF log loss; ties go to the smaller C."""
    X = X.reset_index(drop=True)
    y, groups = np.asarray(y), np.asarray(groups)
    inner = list(StratifiedGroupKFold(n_splits=n_inner, shuffle=True, random_state=seed).split(X, y, groups))
    scores = []
    for C in sorted(c_grid):
        oof = np.zeros(len(y))
        for tr, va in inner:
            oof[va] = predict(fit_arm(arm, C, X.iloc[tr], y[tr], groups[tr], n_inner_cal, seed), arm, X.iloc[va])
        scores.append((round(log_loss(y, np.clip(oof, 1e-15, 1 - 1e-15), labels=[0, 1]), 12), C))
    best = min(scores)[0]
    return min(C for s, C in scores if s == best)


# =============================================================================
# Repeated nested CV
# =============================================================================

def outer_splits(X, y, groups, r: int, n_outer: int):
    return list(StratifiedGroupKFold(n_splits=n_outer, shuffle=True, random_state=1000 + r).split(X, y, groups))


def fold_predictions(arm: str, X, y, groups, tr, te, r: int, *, tune: bool, fixed_C: float, c_grid,
                     n_inner: int, n_inner_cal: int, n_cal: int) -> Tuple[np.ndarray, float]:
    """Predictions for one outer test fold. Only training rows (tr) are used for tuning and fitting."""
    Xtr, ytr, gtr = X.iloc[tr], y[tr], groups[tr]
    C = select_C(arm, Xtr, ytr, gtr, c_grid, 2000 + r, n_inner, n_inner_cal) if tune else fixed_C
    return predict(fit_arm(arm, C, Xtr, ytr, gtr, n_cal, 3000 + r), arm, X.iloc[te]), C


def _task(payload) -> Tuple[int, str, List[Tuple[List[int], List[float]]], List[float]]:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    X, y, groups, r, arm, kw = payload
    folds, chosen = [], []
    for tr, te in outer_splits(X, y, groups, r, kw["n_outer"]):
        p, C = fold_predictions(arm, X, y, groups, tr, te, r, tune=kw["tune"], fixed_C=kw["fixed_C"], c_grid=kw["c_grid"],
                                n_inner=kw["n_inner"], n_inner_cal=kw["n_inner_cal"], n_cal=kw["n_cal"])
        folds.append((te.tolist(), p.tolist()))
        chosen.append(C)
    return r, arm, folds, chosen


def _map(fn, payloads: Sequence, n_jobs: int) -> List:
    if n_jobs <= 1:
        return [fn(p) for p in payloads]
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        return list(ex.map(fn, payloads))


def run_repeated_cv(X, y, groups, *, arms: Sequence[str] = tuple(ARMS), n_repeats: int = N_REPEATS, c_grid=C_GRID,
                    tune: bool = True, fixed_C: float = PRODUCTION_C, n_outer: int = N_OUTER, n_inner: int = N_INNER,
                    n_inner_cal: int = N_INNER_CAL, n_cal: int = N_CAL, n_jobs: int = 1) -> Dict:
    """OOF predictions per arm and repeat, on outer splits identical for every arm."""
    X = X.reset_index(drop=True)
    y, groups = np.asarray(y), np.asarray(groups)
    kw = dict(tune=tune, fixed_C=fixed_C, c_grid=tuple(c_grid), n_outer=n_outer, n_inner=n_inner,
              n_inner_cal=n_inner_cal, n_cal=n_cal)
    payloads = [(X, y, groups, r, arm, kw) for r in range(n_repeats) for arm in arms]
    oof = {arm: np.full((n_repeats, len(y)), np.nan) for arm in arms}
    chosen = {arm: [None] * n_repeats for arm in arms}
    for r, arm, folds, cs in _map(_task, payloads, n_jobs):
        for te, p in folds:
            oof[arm][r, te] = p
        chosen[arm][r] = cs
    if any(np.isnan(v).any() for v in oof.values()):
        raise RuntimeError("Incomplete out-of-fold predictions")
    folds = [[te.tolist() for _, te in outer_splits(X, y, groups, r, n_outer)] for r in range(n_repeats)]
    return {"oof": oof, "chosen_C": {a: [c for cs in v for c in cs] for a, v in chosen.items()}, "outer_test_folds": folds}


# =============================================================================
# Uncertainty and classification
# =============================================================================

def per_repeat_metrics(y, oof_arm) -> Dict[str, np.ndarray]:
    rows = [h2.metrics(y, oof_arm[r]) for r in range(oof_arm.shape[0])]
    return {k: np.array([m[k] for m in rows]) for k in METRIC_KEYS}


def _boot_chunk(payload) -> List[Dict[str, Dict[str, float]]]:
    y, oof, idx_list = payload
    out = []
    for idx in idx_list:
        yb = y[idx]
        out.append({arm: {k: float(np.mean([m[k] for m in (h2.metrics(yb, P[r, idx]) for r in range(P.shape[0]))]))
                          for k in METRIC_KEYS} for arm, P in oof.items()})
    return out


def paired_bootstrap(y, groups, oof: Dict[str, np.ndarray], baseline: str = BASELINE, n_bootstrap: int = N_BOOTSTRAP,
                     seed: int = BOOTSTRAP_SEED, n_jobs: int = 1) -> Dict:
    """
    Resample duplicate groups. Per resample, every metric is computed per repeat on the resampled
    patients, then averaged over repeats. Resample indices are drawn sequentially from one seeded
    generator, so the result does not depend on n_jobs.
    """
    y, groups = np.asarray(y), np.asarray(groups)
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    members = {g: np.flatnonzero(groups == g) for g in unique}
    idx_list = []
    for _ in range(n_bootstrap):
        idx = np.concatenate([members[g] for g in rng.choice(unique, size=len(unique), replace=True)])
        if y[idx].min() != y[idx].max():
            idx_list.append(idx)
    n_chunks = max(1, min(len(idx_list), 4 * max(1, n_jobs)))
    chunks = [idx_list[i::n_chunks] for i in range(n_chunks)]
    order = [i for c in range(n_chunks) for i in range(c, len(idx_list), n_chunks)]
    flat = [d for res in _map(_boot_chunk, [(y, oof, c) for c in chunks], n_jobs) for d in res]
    draws = [None] * len(idx_list)
    for pos, d in zip(order, flat):
        draws[pos] = d
    n_comp = max(1, len(oof) - 1)
    bonf = 100 * (0.05 / n_comp) / 2

    def ci(v):
        v = np.asarray(v)
        return {"mean": float(v.mean()), "ci95_low": float(np.percentile(v, 2.5)), "ci95_high": float(np.percentile(v, 97.5)),
                "ci_bonferroni_low": float(np.percentile(v, bonf)), "ci_bonferroni_high": float(np.percentile(v, 100 - bonf))}

    absolute = {arm: {k: ci([d[arm][k] for d in draws]) for k in METRIC_KEYS} for arm in oof}
    diffs = {arm: {k: ci([d[arm][k] - d[baseline][k] for d in draws]) for k in METRIC_KEYS}
             for arm in oof if arm != baseline}
    return {"n_resamples": len(draws), "bonferroni_level": 1 - 0.05 / n_comp, "absolute": absolute, "differences": diffs}


def classify(d: Dict, low: str = "ci95_low", high: str = "ci95_high") -> Dict:
    """Pre-registered rule (design.md). d holds Δ = ablated − baseline intervals."""
    dependence = d["roc_auc"][high] < 0 or d["log_loss"][low] > 0
    non_inferior = d["roc_auc"][low] >= NI_AUC_MARGIN and d["log_loss"][high] <= NI_LOGLOSS_MARGIN
    label = {(True, False): "material_dependence", (True, True): "dependence_within_margin",
             (False, True): "non_inferior", (False, False): "inconclusive"}[(bool(dependence), bool(non_inferior))]
    return {"dependence_detected": bool(dependence), "non_inferior": bool(non_inferior), "label": label}


def classifications(boot: Dict, per_repeat_diffs: Dict[str, Dict]) -> Dict:
    per_arm = {}
    for arm, d in boot["differences"].items():
        c95 = classify(d)
        cb = classify(d, "ci_bonferroni_low", "ci_bonferroni_high")
        c95["label_bonferroni"] = cb["label"]
        c95["robust_to_multiplicity"] = cb["label"] == c95["label"]
        per_arm[arm] = c95
    single = [a for a in ("B_no_slope", "C_no_thal", "D_no_ca") if a in per_repeat_diffs]
    hyp = {}
    if "C_no_thal" in per_arm:
        hyp["H7_1_thal_dependence"] = {"supported": per_arm["C_no_thal"]["label"] in ("material_dependence", "dependence_within_margin"),
                                       "label": per_arm["C_no_thal"]["label"]}
    if "E_no_slope_thal_ca" in per_repeat_diffs and single:
        e = per_repeat_diffs["E_no_slope_thal_ca"]["log_loss"]["mean"]
        mx = max(per_repeat_diffs[a]["log_loss"]["mean"] for a in single)
        hyp["H7_4_combined_at_least_max_single"] = {"supported": bool(e >= mx), "delta_log_loss_E": e,
                                                    "max_single_delta_log_loss": mx,
                                                    "point_estimate": "mean of per-repeat paired differences"}
    return {"per_arm": per_arm, "hypotheses": hyp,
            "rule": "dependence: dAUC CI high < 0 OR dLogLoss CI low > 0; non-inferior: dAUC CI low >= -0.01 AND "
                    "dLogLoss CI high <= +0.01; label from the pair (95%), robustness from Bonferroni 98.75%"}


def summarise(y, groups, run: Dict, *, bootstrap: bool, n_bootstrap: int = N_BOOTSTRAP, n_jobs: int = 1) -> Dict:
    oof = run["oof"]
    arms = list(oof)
    per_rep = {arm: per_repeat_metrics(y, oof[arm]) for arm in arms}
    summary = {"arms": {}, "per_repeat_differences_vs_baseline": {}}
    for arm in arms:
        summary["arms"][arm] = {
            "removed_features": list(ARMS[arm]), "n_inputs": len(arm_features(arm)),
            "mean": {k: float(v.mean()) for k, v in per_rep[arm].items()},
            "p2_5": {k: float(np.percentile(v, 2.5)) for k, v in per_rep[arm].items()},
            "p97_5": {k: float(np.percentile(v, 97.5)) for k, v in per_rep[arm].items()},
            "per_repeat": {k: [float(x) for x in v] for k, v in per_rep[arm].items()},
            "prediction_stability_mean_sd": float(np.std(oof[arm], axis=0).mean()),
            "chosen_C_counts": {str(c): int(n) for c, n in zip(*np.unique(run["chosen_C"][arm], return_counts=True))},
        }
        if arm != BASELINE:
            diffs = {}
            for k in METRIC_KEYS:
                d = per_rep[arm][k] - per_rep[BASELINE][k]
                worse = (d > 0) if k in LOWER_IS_BETTER else (d < 0)
                diffs[k] = {"mean": float(d.mean()), "p2_5": float(np.percentile(d, 2.5)), "p97_5": float(np.percentile(d, 97.5)),
                            "repeats_ablation_worse": int(worse.sum()), "per_repeat": [float(x) for x in d]}
            summary["per_repeat_differences_vs_baseline"][arm] = diffs
            summary["arms"][arm]["mean_abs_probability_change_vs_baseline"] = float(np.abs(oof[arm] - oof[BASELINE]).mean())
    if bootstrap:
        boot = paired_bootstrap(y, groups, oof, BASELINE, n_bootstrap, n_jobs=n_jobs)
        summary["paired_group_bootstrap"] = boot
        summary["classification"] = classifications(boot, summary["per_repeat_differences_vs_baseline"])
    return summary


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=RESULTS)
    ap.add_argument("--jobs", type=int, default=max(1, min(10, (os.cpu_count() or 2) - 2)))
    args = ap.parse_args(argv)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"            # inherited by worker processes; avoids oversubscription
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    t0 = time.time()
    X, y, groups = r4.load_development_data()
    if len(y) != 242:
        raise RuntimeError("Expected 242 development rows")
    primary = run_repeated_cv(X, y, groups, tune=True, n_jobs=args.jobs)
    secondary = run_repeated_cv(X, y, groups, tune=False, fixed_C=PRODUCTION_C, n_jobs=args.jobs)
    if primary["outer_test_folds"] != secondary["outer_test_folds"]:
        raise RuntimeError("Outer splits differ between analyses")
    result = {
        "experiment": "R7: ablation of unresolved categorical features slope, thal, ca (research only)",
        "preregistered_design": {"path": "openspec/changes/r7-unverified-feature-ablation/design.md", "sha256": sha256_file(DESIGN)},
        "data": {"development_rows": int(len(y)), "locked_rows_parsed": 0,
                 "unique_duplicate_groups": int(len(np.unique(groups))), "disease_prevalence": float(np.mean(y)),
                 "target_orientation": "disease = 1 - heart.csv target", "loader": "experiments/r4_ca_count_encoding.py"},
        "protocol": {"arms": {a: {"removed": list(r), "inputs": arm_features(a)} for a, r in ARMS.items()},
                     "baseline": BASELINE, "recipe": "production: StandardScaler / passthrough / OneHotEncoder(ignore); "
                     "LR(class_weight='balanced', lbfgs); CalibratedClassifierCV(sigmoid, ensemble=True)",
                     "repeats": N_REPEATS, "outer_folds": N_OUTER, "inner_folds": N_INNER, "inner_calibration_folds": N_INNER_CAL,
                     "final_calibration_folds": N_CAL, "C_grid": list(C_GRID), "outer_splits_identical_across_arms": True,
                     "outer_test_folds_sha256": hashlib.sha256(json.dumps(primary["outer_test_folds"]).encode()).hexdigest(),
                     "bootstrap": {"n": N_BOOTSTRAP, "seed": BOOTSTRAP_SEED, "unit": "duplicate group",
                                   "metric_aggregation": "per repeat, then averaged over repeats"},
                     "non_inferiority_margins": {"roc_auc": NI_AUC_MARGIN, "log_loss": NI_LOGLOSS_MARGIN},
                     "slope_estimator": "LogisticRegression(C=np.inf) on logit(p)"},
        "primary_nested_tuned_C": summarise(y, groups, primary, bootstrap=True, n_jobs=args.jobs),
        "secondary_fixed_C_0_1": summarise(y, groups, secondary, bootstrap=False),
        "interpretation_guard": "Statistical dependence on the Kaggle training encoding only; no clinical meaning is assigned to any code.",
        "runtime_seconds": round(time.time() - t0, 1),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"classification": result["primary_nested_tuned_C"]["classification"], "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
