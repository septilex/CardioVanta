"""
CardioVanta H2.1 (research only): prospective confirmation of the pooled OOF calibration finding.

Pre-registered design: openspec/changes/h2-1-calibration-confirmation/design.md

Arms: A = production recipe (ensemble sigmoid calibration), C = pooled OOF sigmoid calibration.
Primary endpoint: signed paired difference in calibration slope, slope(C) - slope(A); expected < 0.

* Only the 242 Cleveland development rows, through the R4 loader (locked lines never parsed).
* New seeds disjoint from H2: outer 5000+r, inner 6000+r, calibration 7000+r, bootstrap 4242; 20 repeats.
* Duplicate-aware StratifiedGroupKFold. Preprocessing, tuning and calibration are fitted only
  on outer-training data, so calibration never uses outer-test labels.
* External cohorts are NOT parsed (pre-registered exclusion: incompatible feature mappings).
* Writes only experiments/results/h2_1_calibration_confirmation.json.

Run:  python experiments/h2_1_calibration_confirmation.py
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
from typing import Dict

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import StratifiedGroupKFold

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("h2_calibration_recipe", PROJECT_ROOT / "experiments" / "h2_calibration_recipe.py")
h2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h2)          # reuse: arm builder, metrics (C=np.inf slope), bootstrap, R4 loader

DESIGN = PROJECT_ROOT / "openspec" / "changes" / "h2-1-calibration-confirmation" / "design.md"
PROPOSAL = PROJECT_ROOT / "openspec" / "changes" / "h2-1-calibration-confirmation" / "proposal.md"
RESULTS = PROJECT_ROOT / "experiments" / "results" / "h2_1_calibration_confirmation.json"

ARMS = ("A_production", "C_pooled_oof_calibration")
BASELINE, CANDIDATE = ARMS
N_REPEATS = 20
SEED_OUTER, SEED_INNER, SEED_CAL, SEED_BOOT = 5000, 6000, 7000, 4242
N_BOOTSTRAP = 2000
SECONDARY = ("log_loss", "brier", "ece_10")
ACCEPT = {"slope_ci_high_below": 0.0, "auc_ci_low_at_least": -0.01, "candidate_slope_range": (0.90, 1.10),
          "min_repeats_expected_direction": 16}

EXTERNAL_EXCLUSION = {
    "evaluated": False,
    "cohorts": ["Hungary (Budapest)", "Long Beach VA"],
    "reason": "Existing feature mappings are incompatible with the production 13-feature recipe; evaluating "
              "would require inventing code mappings or imputing values.",
    "evidence": {
        "unverified_code_mappings": "slope and thal canonical->training mappings are 'unverified' in "
                                    "cardiovanta_ml/contracts/feature_schema.v2.json",
        "documented_missing_counts_-9_sentinel": {
            "hungary_n294": {"ca": 290, "thal": 266, "slope": 190, "chol": 23},
            "long_beach_n200": {"ca": 198, "thal": 159, "slope": 101, "trestbps": 56, "oldpeak": 56,
                                "thalach": 53, "exang": 53},
            "source": "reports/external_data_profiling.json",
        },
        "missing_value_policy": "production contract rejects missing values",
        "outcome_mapping": "compatible (UCI num > 0), but insufficient on its own",
    },
    "reuse_disclosure": "These cohorts were already used in Phase 17 (LOCO validation of other candidate models); "
                        "they are not untouched independent validation data.",
    "external_data_parsed": False,
}


def run(X, y, groups, *, n_repeats: int = N_REPEATS, c_grid=h2.C_GRID, n_outer: int = 5, n_inner: int = 5,
        n_inner_cal: int = 3, n_cal: int = 5) -> Dict:
    """OOF predictions for arms A and C on identical outer splits, with H2-disjoint seeds."""
    X = X.reset_index(drop=True)
    y, groups = np.asarray(y), np.asarray(groups)
    oof = {arm: np.full((n_repeats, len(y)), np.nan) for arm in ARMS}
    chosen = {arm: [] for arm in ARMS}
    folds = []
    for r in range(n_repeats):
        splits = list(StratifiedGroupKFold(n_splits=n_outer, shuffle=True, random_state=SEED_OUTER + r).split(X, y, groups))
        folds.append([te.tolist() for _, te in splits])
        for tr, te in splits:
            Xtr, ytr, gtr = X.iloc[tr], y[tr], groups[tr]
            for arm in ARMS:
                C = h2.select_C(arm, Xtr, ytr, gtr, c_grid, SEED_INNER + r, n_inner, n_inner_cal)
                chosen[arm].append(C)
                oof[arm][r, te] = h2.fit_arm(arm, C, Xtr, ytr, gtr, n_cal, SEED_CAL + r).predict_proba(X.iloc[te])[:, 1]
    return {"oof": oof, "chosen_C": chosen, "outer_test_folds": folds}


BOOT_KEYS = ("calibration_slope", "roc_auc", "log_loss", "brier", "ece_10", "calibration_intercept", "abs_slope_minus_1")


def paired_bootstrap(y, groups, oof: Dict[str, np.ndarray], n_bootstrap: int, seed: int,
                     secondary_level: float) -> Dict:
    """
    Paired group bootstrap of Δ = C − A. Each metric is computed per repeat on the resampled
    patients and averaged over repeats (same estimator as H2). Reports 95% intervals and, from
    the same draws, the pre-registered Bonferroni level for the secondary endpoints.
    """
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    members = {g: np.flatnonzero(groups == g) for g in unique}
    draws = {k: [] for k in BOOT_KEYS}
    for _ in range(n_bootstrap):
        idx = np.concatenate([members[g] for g in rng.choice(unique, size=len(unique), replace=True)])
        yb = y[idx]
        if yb.min() == yb.max():
            continue
        avg = {arm: {k: float(np.mean([h2.metrics(yb, oof[arm][r, idx])[k] for r in range(oof[arm].shape[0])]))
                     for k in BOOT_KEYS} for arm in ARMS}
        for k in BOOT_KEYS:
            draws[k].append(avg[CANDIDATE][k] - avg[BASELINE][k])
    tail = 100 * (1 - secondary_level) / 2
    out = {k: {"mean": float(np.mean(v)), "ci95_low": float(np.percentile(v, 2.5)), "ci95_high": float(np.percentile(v, 97.5)),
               "ci_bonferroni_low": float(np.percentile(v, tail)), "ci_bonferroni_high": float(np.percentile(v, 100 - tail))}
           for k, v in draws.items()}
    return {"n_resamples": len(draws["roc_auc"]), "differences": out}


def evaluate(y, groups, res: Dict, n_bootstrap: int = N_BOOTSTRAP) -> Dict:
    y, groups = np.asarray(y), np.asarray(groups)
    oof = res["oof"]
    per_rep = {arm: h2.per_repeat_metrics(y, oof[arm]) for arm in ARMS}
    # Bonferroni over the 3 secondary endpoints -> two-sided 98.33% intervals, from the same draws
    sec_level = 1 - 0.05 / len(SECONDARY)
    boot = paired_bootstrap(y, groups, oof, n_bootstrap, SEED_BOOT, sec_level)
    d = boot["differences"]
    rep_diff = {k: per_rep[CANDIDATE][k] - per_rep[BASELINE][k] for k in h2.METRIC_KEYS}
    n_dir = int((rep_diff["calibration_slope"] < 0).sum())
    cand_slope = float(per_rep[CANDIDATE]["calibration_slope"].mean())
    lo, hi = ACCEPT["candidate_slope_range"]
    criteria = {
        "1_primary_dslope_ci95_high_below_0": {"value": d["calibration_slope"]["ci95_high"],
                                               "pass": d["calibration_slope"]["ci95_high"] < ACCEPT["slope_ci_high_below"]},
        "2_guardrail_dauc_ci95_low_at_least_-0.01": {"value": d["roc_auc"]["ci95_low"],
                                                      "pass": d["roc_auc"]["ci95_low"] >= ACCEPT["auc_ci_low_at_least"]},
        "3_candidate_mean_slope_within_0.90_1.10": {"value": cand_slope, "pass": lo <= cand_slope <= hi},
        # 80% of repeats: 16 of the pre-registered 20 (scaled only when tests use fewer repeats)
        "4_dslope_negative_in_at_least_80pct_of_repeats": {
            "value": n_dir, "required": ACCEPT["min_repeats_expected_direction"] * len(rep_diff["calibration_slope"]) / N_REPEATS,
            "pass": n_dir >= ACCEPT["min_repeats_expected_direction"] * len(rep_diff["calibration_slope"]) / N_REPEATS},
    }
    confirmed = all(c["pass"] for c in criteria.values())
    secondary = {k: {"mean": d[k]["mean"], "ci95_low": d[k]["ci95_low"], "ci95_high": d[k]["ci95_high"],
                     "ci_bonferroni_low": d[k]["ci_bonferroni_low"], "ci_bonferroni_high": d[k]["ci_bonferroni_high"],
                     "supportive_bonferroni": bool(d[k]["ci_bonferroni_high"] < 0),
                     "repeats_expected_direction": int((rep_diff[k] < 0).sum())} for k in SECONDARY}
    return {
        "arms": {arm: {"mean": {k: float(v.mean()) for k, v in per_rep[arm].items()},
                       "p2_5": {k: float(np.percentile(v, 2.5)) for k, v in per_rep[arm].items()},
                       "p97_5": {k: float(np.percentile(v, 97.5)) for k, v in per_rep[arm].items()},
                       "per_repeat": {k: [float(x) for x in v] for k, v in per_rep[arm].items()},
                       "prediction_stability_mean_sd": float(np.nanstd(oof[arm], axis=0).mean()),
                       "chosen_C_counts": {str(c): int(n) for c, n in zip(*np.unique(res["chosen_C"][arm], return_counts=True))}}
                 for arm in ARMS},
        "primary": {"endpoint": "slope(C) - slope(A)", "expected_direction": "negative",
                    **d["calibration_slope"], "per_repeat_differences": [float(x) for x in rep_diff["calibration_slope"]],
                    "repeats_expected_direction": n_dir},
        "guardrail_roc_auc": {**d["roc_auc"], "repeats_candidate_not_worse": int((rep_diff["roc_auc"] >= 0).sum())},
        "secondary_bonferroni": {"level": sec_level, "adjustment": f"Bonferroni over {len(SECONDARY)} secondary endpoints",
                                 "endpoints": secondary},
        "descriptive_differences": {k: d[k] for k in ("calibration_intercept", "abs_slope_minus_1")},
        "bootstrap": {"n_resamples": boot["n_resamples"], "seed": SEED_BOOT, "unit": "duplicate group",
                      "aggregation": "metric per repeat on resampled patients, averaged over repeats"},
        "acceptance_criteria": criteria,
        "verdict": "confirmed" if confirmed else "not_confirmed",
    }


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=RESULTS)
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    t0 = time.time()
    X, y, groups = h2.r4.load_development_data()
    res = run(X, y, groups)
    result = {
        "experiment": "H2.1: prospective confirmation of pooled OOF calibration (research only)",
        "preregistration": {"design": {"path": "openspec/changes/h2-1-calibration-confirmation/design.md", "sha256": sha256_file(DESIGN)},
                            "proposal": {"path": "openspec/changes/h2-1-calibration-confirmation/proposal.md", "sha256": sha256_file(PROPOSAL)}},
        "data": {"development_rows": int(len(y)), "locked_rows_parsed": 0, "unique_duplicate_groups": int(len(np.unique(groups))),
                 "disease_prevalence": float(np.mean(y)), "same_patients_as_h2": True,
                 "independence_note": "Same 242 patients as H2; new partitions and a prospective endpoint, not new patients."},
        "protocol": {"arms": {a: h2.ARMS[a] for a in ARMS}, "repeats": N_REPEATS,
                     "seeds": {"outer": f"{SEED_OUTER}+r", "inner": f"{SEED_INNER}+r", "calibration": f"{SEED_CAL}+r", "bootstrap": SEED_BOOT},
                     "h2_seeds_disjoint": True, "C_grid": list(h2.C_GRID),
                     "outer_test_folds_sha256": hashlib.sha256(json.dumps(res["outer_test_folds"]).encode()).hexdigest(),
                     "slope_estimator": "LogisticRegression(C=np.inf) on logit(p)"},
        "results": evaluate(y, groups, res),
        "external_cohorts": EXTERNAL_EXCLUSION,
        "runtime_seconds": round(time.time() - t0, 1),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"verdict": result["results"]["verdict"], "criteria": result["results"]["acceptance_criteria"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
