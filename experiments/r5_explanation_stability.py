"""
CardioVanta R5 (research only): stability of feature explanations under one-feature perturbations.

Design: openspec/changes/r5-explanation-stability/design.md

* Frozen production model cardiovanta-lr13@1.0.0, loaded read-only through the SHA-256-verified
  registry. No retraining or recalibration.
* 100 deterministic synthetic profiles from the canonical 13-feature contract. No dataset, locked
  observation or external cohort is loaded.
* Categorical codes are reported only by number and contract verification level (no clinical meaning).
* Writes only experiments/results/r5_explanation_stability.json.

Run:  python experiments/r5_explanation_stability.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cardiovanta_ml import InferenceEngine, load_model                 # noqa: E402
from cardiovanta_ml.contracts import generated_features as contract    # noqa: E402

DESIGN = PROJECT_ROOT / "openspec" / "changes" / "r5-explanation-stability" / "design.md"
RESULTS = PROJECT_ROOT / "experiments" / "results" / "r5_explanation_stability.json"
REGISTRY_ROOT = PROJECT_ROOT / "artifacts"
MODEL_ID, MODEL_VERSION = "cardiovanta-lr13", "1.0.0"

FEATURES: List[str] = list(contract.FEATURE_ORDER)
CONTINUOUS = [f for f in FEATURES if contract.FEATURES[f]["type"] == "continuous"]
DISCRETE = [f for f in FEATURES if contract.FEATURES[f]["type"] != "continuous"]
N_PROFILES, SEED = 100, 20261031
FRACTIONS = (-0.10, -0.05, 0.05, 0.10)        # of the development-range width
ZERO_TOL, LOCALITY_TOL, DP_TOL = 1e-12, 1e-12, 1e-9
METHODS = ("linear", "shap_equivalent")
VERIFIED = {"verified_patient_matched", "codebook_and_project_contract"}


# =============================================================================
# Profiles and perturbations
# =============================================================================

def generate_profiles(n: int = N_PROFILES, seed: int = SEED) -> List[Dict[str, float]]:
    """Deterministic synthetic profiles: continuous uniform in the development range, discrete uniform over accepted codes."""
    rng = np.random.default_rng(seed)
    profiles = []
    for _ in range(n):
        p = {}
        for f in FEATURES:
            meta = contract.FEATURES[f]
            if meta["type"] == "continuous":
                lo, hi = meta["development_range"]["min"], meta["development_range"]["max"]
                p[f] = float(round(rng.uniform(lo, hi), 4))
            else:
                p[f] = int(rng.choice([o["code"] for o in meta["options"]]))
        profiles.append(p)
    return profiles


def perturbations(profile: Dict[str, float]):
    """Yield (feature, kind, label, perturbed profile). Out-of-range continuous shifts are skipped, not clipped."""
    for f in FEATURES:
        meta = contract.FEATURES[f]
        if meta["type"] == "continuous":
            lo, hi = meta["development_range"]["min"], meta["development_range"]["max"]
            for frac in FRACTIONS:
                new = profile[f] + frac * (hi - lo)
                if lo <= new <= hi:
                    yield f, "continuous", f"{frac:+.0%}", {**profile, f: float(new)}
                else:
                    yield f, "continuous", f"{frac:+.0%}", None
        else:
            for o in meta["options"]:
                if o["code"] != profile[f]:
                    yield f, "categorical", f"{profile[f]}->{o['code']}", {**profile, f: o["code"]}


def verification_level(feature: str, code: int) -> str:
    return next(o["verification"] for o in contract.FEATURES[feature]["options"] if o["code"] == code)


# =============================================================================
# Metrics
# =============================================================================

def _sign(x: float) -> int:
    return 0 if abs(x) <= ZERO_TOL else (1 if x > 0 else -1)


def top_k(contrib: Dict[str, float], k: int) -> List[str]:
    """Top-k features by |contribution|; ties broken deterministically by contract order."""
    return sorted(FEATURES, key=lambda f: (-abs(contrib[f]), FEATURES.index(f)))[:k]


def top_k_overlap(a: Dict[str, float], b: Dict[str, float], k: int) -> float:
    return len(set(top_k(a, k)) & set(top_k(b, k))) / k


def rank_correlation(a: Dict[str, float], b: Dict[str, float]) -> float:
    va, vb = [abs(a[f]) for f in FEATURES], [abs(b[f]) for f in FEATURES]
    if np.allclose(va, va[0]) or np.allclose(vb, vb[0]):
        return float("nan")
    return float(spearmanr(va, vb).statistic)


def additivity_error(exp: Dict, method: str) -> float:
    base = exp["intercept"] if method == "linear" else exp["expected_value"]
    return abs(base + sum(exp["contributions"].values()) - exp["decision_function_log_odds"])


def explain_all(engine: InferenceEngine, profile: Dict) -> Dict:
    return {"p": engine.predict(profile)["probability"],
            "linear": engine.explain(profile), "shap_equivalent": engine.explain_shap_equivalent(profile)}


def compare(base: Dict, pert: Dict, feature: str) -> Dict:
    out = {"dp": pert["p"] - base["p"]}
    for m in METHODS:
        cb, cp = base[m]["contributions"], pert[m]["contributions"]
        others = [f for f in FEATURES if f != feature]
        d_feat = cp[feature] - cb[feature]
        out[m] = {
            "rank_corr": rank_correlation(cb, cp),
            "top3": top_k_overlap(cb, cp, 3),
            "top5": top_k_overlap(cb, cp, 5),
            "own_sign_flip": _sign(cb[feature]) != _sign(cp[feature]),
            "other_sign_flips": sum(_sign(cb[f]) != _sign(cp[f]) for f in others),
            "max_other_change": max(abs(cp[f] - cb[f]) for f in others),
            "d_own_contribution": d_feat,
            "additivity_error": max(additivity_error(base[m], m), additivity_error(pert[m], m)),
            "direction_agrees": (None if abs(out["dp"]) <= DP_TOL else _sign(d_feat) == _sign(out["dp"])),
        }
    return out


# =============================================================================
# Aggregation
# =============================================================================

def _stats(values: Sequence[float]) -> Dict:
    v = np.asarray([x for x in values if x is not None and not (isinstance(x, float) and np.isnan(x))], dtype=float)
    if v.size == 0:
        return {"n": 0}
    return {"n": int(v.size), "mean": float(v.mean()), "median": float(np.median(v)),
            "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95)),
            "min": float(v.min()), "max": float(v.max())}


def _rate(values) -> Dict:
    v = [x for x in values if x is not None]
    return {"n": len(v), "rate": (float(np.mean(v)) if v else None)}


def summarise(rows: List[Dict]) -> Dict:
    if not rows:
        return {"n_perturbations": 0}
    out = {"n_perturbations": len(rows), "abs_dp": _stats([abs(r["dp"]) for r in rows])}
    for m in METHODS:
        out[m] = {
            "rank_corr": _stats([r[m]["rank_corr"] for r in rows]),
            "top3_overlap": _stats([r[m]["top3"] for r in rows]),
            "top5_overlap": _stats([r[m]["top5"] for r in rows]),
            "top3_identical_rate": float(np.mean([r[m]["top3"] == 1.0 for r in rows])),
            "own_sign_flip_rate": float(np.mean([r[m]["own_sign_flip"] for r in rows])),
            "other_sign_flips_total": int(sum(r[m]["other_sign_flips"] for r in rows)),
            "max_other_contribution_change": float(max(r[m]["max_other_change"] for r in rows)),
            "max_additivity_error": float(max(r[m]["additivity_error"] for r in rows)),
            "direction_agreement": _rate([r[m]["direction_agrees"] for r in rows]),
        }
    return out


def run(n_profiles: int = N_PROFILES, seed: int = SEED, registry_root: Path = REGISTRY_ROOT) -> Dict:
    model = load_model(MODEL_ID, MODEL_VERSION, registry_root=Path(registry_root).resolve())
    engine = InferenceEngine(model)
    profiles = generate_profiles(n_profiles, seed)
    rows, skipped = [], {f: 0 for f in CONTINUOUS}
    method_delta_max_diff = 0.0
    for i, prof in enumerate(profiles):
        base = explain_all(engine, prof)
        for feature, kind, label, new in perturbations(prof):
            if new is None:
                skipped[feature] += 1
                continue
            r = compare(base, explain_all(engine, new), feature)
            method_delta_max_diff = max(method_delta_max_diff,
                                        abs(r["linear"]["d_own_contribution"] - r["shap_equivalent"]["d_own_contribution"]))
            r.update({"profile": i, "feature": feature, "kind": kind, "perturbation": label})
            if kind == "categorical":
                old, newc = (int(x) for x in label.split("->"))
                r["verification"] = sorted({verification_level(feature, old), verification_level(feature, newc)})
            rows.append(r)

    cont = [r for r in rows if r["kind"] == "continuous"]
    cat = [r for r in rows if r["kind"] == "categorical"]
    result = {
        "continuous": summarise(cont),
        "categorical": summarise(cat),
        "per_feature": {f: summarise([r for r in rows if r["feature"] == f]) for f in FEATURES},
        "continuous_by_magnitude": {lab: summarise([r for r in cont if r["perturbation"] == lab])
                                    for lab in sorted({r["perturbation"] for r in cont})},
        # Categorical perturbations grouped by the verification level of the codes involved:
        #   verified_only          both codes have an established meaning
        #   unverified             at least one code is 'unverified' (slope, thal 1-3)
        #   undefined_in_codebook  at least one code is undefined in the UCI codebook (ca=4, thal=0)
        "categorical_by_verification": {
            "verified_only": summarise([r for r in cat if set(r["verification"]) <= VERIFIED]),
            "unverified": summarise([r for r in cat if "unverified" in r["verification"]]),
            "undefined_in_codebook": summarise([r for r in cat if "undefined_in_codebook" in r["verification"]]),
        },
        "skipped_out_of_range": skipped,
    }
    result["expectation_checks"] = {
        "locality_max_other_contribution_change": max(result[k][m]["max_other_contribution_change"]
                                                      for k in ("continuous", "categorical") for m in METHODS),
        "locality_holds": all(result[k][m]["max_other_contribution_change"] <= LOCALITY_TOL and result[k][m]["other_sign_flips_total"] == 0
                              for k in ("continuous", "categorical") for m in METHODS),
        "max_additivity_error": max(result[k][m]["max_additivity_error"] for k in ("continuous", "categorical") for m in METHODS),
        "additivity_holds": all(result[k][m]["max_additivity_error"] < 1e-9 for k in ("continuous", "categorical") for m in METHODS),
        "linear_vs_shap_delta_max_abs_difference": method_delta_max_diff,
        "methods_share_deltas": method_delta_max_diff < 1e-9,
    }
    result["counts"] = {"profiles": len(profiles), "perturbations_evaluated": len(rows),
                        "continuous": len(cont), "categorical": len(cat), "skipped_out_of_range": int(sum(skipped.values()))}
    result["profiles_sha256"] = hashlib.sha256(json.dumps(profiles, sort_keys=True).encode()).hexdigest()
    result["model"] = {"id": model.model_id, "version": model.model_version,
                       "outcome_mapping": model.metadata.outcome.mapping_status, "registry_verified": True}
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=RESULTS)
    args = ap.parse_args(argv)
    t0 = time.time()
    res = run()
    out = {"experiment": "R5: explanation stability under one-feature perturbations (research only)",
           "design": {"path": "openspec/changes/r5-explanation-stability/design.md",
                      "sha256": hashlib.sha256(DESIGN.read_bytes()).hexdigest()},
           "protocol": {"profiles": N_PROFILES, "seed": SEED, "continuous_shift_fractions_of_dev_range": list(FRACTIONS),
                        "categorical": "every other accepted code", "data_loaded": "none (synthetic only)"},
           **res, "runtime_seconds": round(time.time() - t0, 2)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2))
    print(json.dumps({"counts": res["counts"], "expectation_checks": res["expectation_checks"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
