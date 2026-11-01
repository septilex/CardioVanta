"""
CardioVanta R4 (research only): count encoding of `ca` versus the production one-hot recipe.

Pre-registered design: openspec/changes/r4-ca-count-encoding/design.md

Protocol
--------
* Uses ONLY the 242 Cleveland development rows (data/processed/dev_indices.json).
  The raw CSV is read line by line; lines of non-development rows are discarded
  WITHOUT being parsed, so the 61 locked observations are never parsed or used.
* Target harmonised to clinical orientation: disease = 1 - target (Phase 17 / R0.3).
* Duplicate-aware groups (identical feature rows), StratifiedGroupKFold everywhere.
* All preprocessing, C tuning and sigmoid calibration are fitted inside training folds.
* Deterministic seeds. Writes only experiments/results/r4_ca_count_encoding.json.
* Never touches production artifacts, the registry or the clinical contract.

Run:  python experiments/r4_ca_count_encoding.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Feature definitions come from the canonical clinical contract (read-only).
from cardiovanta_ml.contracts import generated_features as contract  # noqa: E402

RAW_CSV = PROJECT_ROOT / "data" / "raw" / "heart.csv"
DEV_INDICES = PROJECT_ROOT / "data" / "processed" / "dev_indices.json"
PRODUCTION_METADATA = PROJECT_ROOT / "artifacts" / "model" / "metadata.json"
DESIGN = PROJECT_ROOT / "openspec" / "changes" / "r4-ca-count-encoding" / "design.md"
RESULTS = PROJECT_ROOT / "experiments" / "results" / "r4_ca_count_encoding.json"

FEATURES: List[str] = list(contract.FEATURE_ORDER)
CONTINUOUS = [f for f in FEATURES if contract.FEATURES[f]["type"] == "continuous"]
BINARY = [f for f in FEATURES if contract.FEATURES[f]["type"] == "binary"]
CATEGORICAL = [f for f in FEATURES if contract.FEATURES[f]["type"] == "categorical"]
CA_CODES = tuple(o["code"] for o in contract.FEATURES["ca"]["options"])   # (0, 1, 2, 3, 4)
CA_UNDEFINED_CODE = 4                                                     # undefined_in_codebook

C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
N_REPEATS = 10
N_OUTER, N_INNER, N_INNER_CAL, N_CAL = 5, 5, 3, 5
PRODUCTION_C = 0.1
N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 42
ARMS = ("baseline_onehot_ca", "candidate_count_ca")


# =============================================================================
# Development-only data loading
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def load_dev_rows(csv_path: Path, dev_indices: Sequence[int], expected_columns: Sequence[str]) -> pd.DataFrame:
    """
    Parse ONLY the header and the rows whose 0-based data index is in ``dev_indices``.

    Every other line is skipped before parsing, so its values are never
    tokenised, converted or stored.
    """
    wanted = set(int(i) for i in dev_indices)
    if len(wanted) != len(dev_indices):
        raise ValueError("dev_indices contains duplicates")
    rows: Dict[int, List[str]] = {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        header = next(csv.reader([fh.readline()]))
        if [h.strip() for h in header] != list(expected_columns):
            raise ValueError(f"Unexpected header {header}")
        for data_index, line in enumerate(fh):
            if data_index in wanted:                       # locked lines never reach the parser
                rows[data_index] = next(csv.reader([line]))
    if set(rows) != wanted:
        raise ValueError(f"Missing development rows: {sorted(wanted - set(rows))[:5]}")
    ordered = [rows[i] for i in sorted(wanted)]
    df = pd.DataFrame(ordered, columns=list(expected_columns), index=sorted(wanted)).apply(pd.to_numeric)
    return df


def load_development_data():
    """Load the 242 development rows, after verifying provenance hashes against production metadata."""
    provenance = json.loads(PRODUCTION_METADATA.read_text())["training_data_provenance"]
    if sha256_file(RAW_CSV) != provenance["raw_dataset_sha256"]:
        raise RuntimeError("heart.csv SHA-256 does not match production provenance")
    if sha256_file(DEV_INDICES) != provenance["development_indices_sha256"]:
        raise RuntimeError("dev_indices.json SHA-256 does not match production provenance")
    dev_indices = json.loads(DEV_INDICES.read_text())
    df = load_dev_rows(RAW_CSV, dev_indices, FEATURES + ["target"])
    if len(df) != 242:
        raise RuntimeError(f"Expected 242 development rows, got {len(df)}")
    X = df[FEATURES].astype(float)
    y = (1 - df["target"].astype(int)).to_numpy()          # disease = 1 (harmonised)
    groups = X.groupby(FEATURES).ngroup().to_numpy()       # duplicate-aware groups
    return X.reset_index(drop=True), y, groups


# =============================================================================
# Arms
# =============================================================================

class CaCountEncoder(BaseEstimator, TransformerMixin):
    """
    ``ca`` -> [ca_count (standardized, fold-local), ca_code4 indicator].

    Codes 0-3 are vessel counts (UCI codebook). Code 4 has no defined meaning, so it
    gets its own indicator and count 0. Its effect is learned only through the
    indicator, and no clinical meaning is assumed.
    """

    def fit(self, X, y=None):
        count, _ = self._split(X)
        self.mean_ = float(np.mean(count))
        std = float(np.std(count))
        self.scale_ = std if std > 0 else 1.0
        return self

    def transform(self, X):
        count, code4 = self._split(X)
        return np.column_stack([(count - self.mean_) / self.scale_, code4])

    def get_feature_names_out(self, input_features=None):
        return np.array(["ca_count", "ca_code4"], dtype=object)

    @staticmethod
    def _split(X):
        values = np.asarray(X, dtype=float).reshape(-1)
        if not np.isin(values, CA_CODES).all():
            raise ValueError(f"ca codes outside contract {CA_CODES}: {sorted(set(values) - set(CA_CODES))}")
        code4 = (values == CA_UNDEFINED_CODE).astype(float)
        count = np.where(code4 == 1.0, 0.0, values)
        return count, code4


def build_pipeline(arm: str, C: float) -> Pipeline:
    model = LogisticRegression(C=C, class_weight="balanced", solver="lbfgs", max_iter=2000, random_state=42)
    if arm == "baseline_onehot_ca":   # production recipe (src/preprocessing/preprocessor.py, linear family)
        pre = ColumnTransformer([
            ("num", StandardScaler(), CONTINUOUS),
            ("bin", "passthrough", BINARY),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ], remainder="drop")
    elif arm == "candidate_count_ca":
        pre = ColumnTransformer([
            ("num", StandardScaler(), CONTINUOUS),
            ("bin", "passthrough", BINARY),
            ("cat", OneHotEncoder(handle_unknown="ignore"), [c for c in CATEGORICAL if c != "ca"]),
            ("ca", CaCountEncoder(), ["ca"]),
        ], remainder="drop")
    else:
        raise ValueError(f"Unknown arm {arm!r}")
    return Pipeline([("preprocessor", pre), ("model", model)])


def calibrated(arm: str, C: float, X, y, groups, n_splits: int, seed: int) -> CalibratedClassifierCV:
    X = X.reset_index(drop=True)   # positional split indices must match a 0..n-1 index
    splits = list(StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(X, y, groups))
    return CalibratedClassifierCV(estimator=build_pipeline(arm, C), method="sigmoid", cv=splits).fit(X, y)


# =============================================================================
# Metrics
# =============================================================================

def expected_calibration_error(y, p, n_bins: int = 10) -> float:
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        mask = bins == b
        if mask.any():
            ece += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(ece)


def calibration_slope(y, p) -> float:
    logit = np.log(np.clip(p, 1e-12, 1 - 1e-12) / np.clip(1 - p, 1e-12, 1))
    lr = LogisticRegression(penalty=None, solver="lbfgs", max_iter=2000).fit(logit.reshape(-1, 1), y)
    return float(lr.coef_[0][0])


def metrics(y, p) -> Dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.clip(p, 1e-15, 1 - 1e-15), labels=[0, 1])),
        "ece_10": expected_calibration_error(y, p),
        "calibration_slope": calibration_slope(y, p),
        "calibration_in_the_large": float(np.mean(y) - np.mean(p)),
    }


# =============================================================================
# Repeated nested cross-validation
# =============================================================================

def select_C(arm: str, X, y, groups, c_grid: Iterable[float], seed: int, n_inner: int, n_inner_cal: int) -> float:
    """Inner CV: lowest OOF log loss of a sigmoid-calibrated model; ties -> smaller C."""
    X = X.reset_index(drop=True)
    y, groups = np.asarray(y), np.asarray(groups)
    inner = list(StratifiedGroupKFold(n_splits=n_inner, shuffle=True, random_state=seed).split(X, y, groups))
    scores = []
    for C in sorted(c_grid):
        oof = np.zeros(len(y))
        for tr, va in inner:
            model = calibrated(arm, C, X.iloc[tr], y[tr], groups[tr], n_inner_cal, seed)
            oof[va] = model.predict_proba(X.iloc[va])[:, 1]
        scores.append((round(log_loss(y, np.clip(oof, 1e-15, 1 - 1e-15), labels=[0, 1]), 12), C))
    best = min(scores)[0]
    return min(C for s, C in scores if s == best)


def run_repeated_cv(X, y, groups, *, n_repeats: int = N_REPEATS, c_grid=C_GRID, tune: bool = True,
                    fixed_C: float = PRODUCTION_C, n_outer: int = N_OUTER, n_inner: int = N_INNER,
                    n_inner_cal: int = N_INNER_CAL, n_cal: int = N_CAL) -> Dict:
    """OOF predictions per arm and repeat, on identical outer splits for both arms."""
    X = X.reset_index(drop=True)
    y, groups = np.asarray(y), np.asarray(groups)   # positional indexing throughout
    oof = {arm: np.zeros((n_repeats, len(y))) for arm in ARMS}
    chosen = {arm: [] for arm in ARMS}
    for r in range(n_repeats):
        outer = StratifiedGroupKFold(n_splits=n_outer, shuffle=True, random_state=1000 + r)
        for tr, te in outer.split(X, y, groups):
            Xtr, ytr, gtr = X.iloc[tr], y[tr], groups[tr]
            for arm in ARMS:
                C = select_C(arm, Xtr, ytr, gtr, c_grid, 2000 + r, n_inner, n_inner_cal) if tune else fixed_C
                chosen[arm].append(C)
                model = calibrated(arm, C, Xtr, ytr, gtr, n_cal, 3000 + r)
                oof[arm][r, te] = model.predict_proba(X.iloc[te])[:, 1]
    return {"oof": oof, "chosen_C": chosen}


def summarise(y, groups, run: Dict, n_bootstrap: int = N_BOOTSTRAP) -> Dict:
    y, groups = np.asarray(y), np.asarray(groups)
    oof, out = run["oof"], {"arms": {}, "difference_candidate_minus_baseline": {}}
    per_repeat = {arm: [metrics(y, oof[arm][r]) for r in range(oof[arm].shape[0])] for arm in ARMS}
    keys = list(per_repeat[ARMS[0]][0])
    for arm in ARMS:
        values = {k: np.array([m[k] for m in per_repeat[arm]]) for k in keys}
        out["arms"][arm] = {
            "per_repeat_mean": {k: float(v.mean()) for k, v in values.items()},
            "per_repeat_p2_5": {k: float(np.percentile(v, 2.5)) for k, v in values.items()},
            "per_repeat_p97_5": {k: float(np.percentile(v, 97.5)) for k, v in values.items()},
            "repeat_averaged_oof": metrics(y, oof[arm].mean(axis=0)),
            "prediction_stability_mean_sd": float(oof[arm].std(axis=0).mean()),
            "chosen_C_counts": {str(c): int(n) for c, n in zip(*np.unique(run["chosen_C"][arm], return_counts=True))},
        }
    diffs = {k: np.array([per_repeat[ARMS[1]][r][k] - per_repeat[ARMS[0]][r][k] for r in range(len(per_repeat[ARMS[0]]))])
             for k in keys}
    out["difference_candidate_minus_baseline"]["per_repeat"] = {
        k: {"mean": float(v.mean()), "p2_5": float(np.percentile(v, 2.5)), "p97_5": float(np.percentile(v, 97.5)),
            "n_repeats_candidate_better": int((v < 0).sum() if k in ("brier", "log_loss", "ece_10") else (v > 0).sum())}
        for k, v in diffs.items() if k in ("roc_auc", "pr_auc", "brier", "log_loss", "ece_10")
    }
    out["difference_candidate_minus_baseline"]["paired_group_bootstrap"] = paired_bootstrap(
        y, groups, oof[ARMS[0]].mean(axis=0), oof[ARMS[1]].mean(axis=0), n_bootstrap)
    out["difference_candidate_minus_baseline"]["mean_abs_probability_difference"] = float(
        np.abs(oof[ARMS[1]].mean(axis=0) - oof[ARMS[0]].mean(axis=0)).mean())
    return out


def paired_bootstrap(y, groups, p_base, p_cand, n_bootstrap: int, seed: int = BOOTSTRAP_SEED) -> Dict:
    """Resample duplicate groups with replacement; paired differences on the same resample."""
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    members = {g: np.flatnonzero(groups == g) for g in unique}
    stats = {"roc_auc": [], "brier": [], "log_loss": [], "ece_10": []}
    for _ in range(n_bootstrap):
        idx = np.concatenate([members[g] for g in rng.choice(unique, size=len(unique), replace=True)])
        yb = y[idx]
        if yb.min() == yb.max():
            continue
        mb, mc = metrics(yb, p_base[idx]), metrics(yb, p_cand[idx])
        for k in stats:
            stats[k].append(mc[k] - mb[k])
    return {k: {"mean": float(np.mean(v)), "ci95_low": float(np.percentile(v, 2.5)),
                "ci95_high": float(np.percentile(v, 97.5)), "n": len(v)} for k, v in stats.items()}


def verdict(primary: Dict) -> Dict:
    """Pre-registered rule (design.md): non-inferior AUC AND improved log loss or Brier score."""
    boot = primary["difference_candidate_minus_baseline"]["paired_group_bootstrap"]
    non_inferior = boot["roc_auc"]["ci95_low"] >= -0.01
    calibration_better = boot["log_loss"]["ci95_high"] < 0 or boot["brier"]["ci95_high"] < 0
    return {"non_inferior_auc": bool(non_inferior), "calibration_improved": bool(calibration_better),
            "h1_supported": bool(non_inferior and calibration_better),
            "rule": "dAUC CI low >= -0.01 AND (dLogLoss CI high < 0 OR dBrier CI high < 0)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=RESULTS)
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    t0 = time.time()
    X, y, groups = load_development_data()
    primary_run = run_repeated_cv(X, y, groups, tune=True)
    secondary_run = run_repeated_cv(X, y, groups, tune=False, fixed_C=PRODUCTION_C)
    primary = summarise(y, groups, primary_run)
    secondary = summarise(y, groups, secondary_run)
    result = {
        "experiment": "R4: count encoding of ca vs production one-hot recipe (research only)",
        "preregistered_design": {"path": str(DESIGN.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                                 "sha256": sha256_file(DESIGN)},
        "data": {"development_rows": int(len(y)), "locked_rows_parsed": 0, "unique_duplicate_groups": int(len(np.unique(groups))),
                 "disease_prevalence": float(y.mean()), "target_orientation": "disease = 1 - heart.csv target",
                 "ca_code_counts": {str(int(k)): int(v) for k, v in pd.Series(X["ca"]).value_counts().sort_index().items()}},
        "protocol": {"repeats": N_REPEATS, "outer_folds": N_OUTER, "inner_folds": N_INNER,
                     "inner_calibration_folds": N_INNER_CAL, "final_calibration_folds": N_CAL, "C_grid": list(C_GRID),
                     "class_weight": "balanced", "calibration": "sigmoid (CalibratedClassifierCV, duplicate-aware splits)",
                     "bootstrap": {"n": N_BOOTSTRAP, "seed": BOOTSTRAP_SEED, "unit": "duplicate group"}},
        "parameters": {"baseline_ca_columns": len(CA_CODES), "candidate_ca_columns": 2},
        "primary_nested_tuned_C": primary,
        "secondary_fixed_C_0_1": secondary,
        "verdict": verdict(primary),
        "verdict_secondary_fixed_C": verdict(secondary),
        "runtime_seconds": round(time.time() - t0, 1),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"verdict": result["verdict"], "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
