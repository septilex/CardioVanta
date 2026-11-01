"""
R7 reporting correction (post hoc, documented): calibration-slope comparisons by |slope - 1|.

Problem
-------
In the saved R7 results, ``per_repeat_differences_vs_baseline.<arm>.calibration_slope.repeats_ablation_worse``
counted a *lower signed slope* as worse. For calibration slope, closer to 1 is better, so that count is
misleading when slopes are above 1 (all R7 arms) and wrong whenever a slope crosses below 1.
No pre-registered label used it.

Correction
----------
Reads ONLY the saved R7 results JSON (no dataset, no model fitting, no rerun) and adds a
``reporting_corrections`` block that:
  * compares arms by |slope - 1| (lower is better), per repeat and with the saved paired bootstrap;
  * reports signed slopes separately and flags any crossing below 1;
  * records the original misleading field values and the hash of the original content.
Every original field is left byte-for-byte unchanged; the step is deterministic and idempotent.

Run:  python experiments/r7_slope_reporting_correction.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "experiments" / "results" / "r7_unverified_feature_ablation.json"
BLOCK = "reporting_corrections"
BASELINE = "A_baseline"
ANALYSES = ("primary_nested_tuned_C", "secondary_fixed_C_0_1")
# Content hash (sort_keys JSON, excluding runtime) verified identical across the two R7 runs on 2026-10-31.
ORIGINAL_CONTENT_SHA256 = "7931f88cbd81214cf3c7245a5e695b45923f32469a00e76e2a66c665ac15e5dc"


def original_content_sha256(record: Dict) -> str:
    core = {k: v for k, v in record.items() if k not in ("runtime_seconds", BLOCK)}
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()


def _summary(values: List[float]) -> Dict:
    v = np.asarray(values, dtype=float)
    return {"mean": float(v.mean()), "min": float(v.min()), "max": float(v.max()),
            "p2_5": float(np.percentile(v, 2.5)), "p97_5": float(np.percentile(v, 97.5))}


def signed_slope_summary(slopes: List[float], bootstrap_abs: Dict | None) -> Dict:
    """Signed slopes with explicit flags for any crossing below 1 (over-confidence)."""
    s = np.asarray(slopes, dtype=float)
    out = {**_summary(slopes), "per_repeat": [float(x) for x in s],
           "repeats_below_1": int((s < 1).sum()), "mean_below_1": bool(s.mean() < 1)}
    if bootstrap_abs is not None:
        out["bootstrap_ci95"] = [bootstrap_abs["ci95_low"], bootstrap_abs["ci95_high"]]
        out["bootstrap_ci95_low_below_1"] = bool(bootstrap_abs["ci95_low"] < 1)
    out["crosses_below_1"] = bool(out["repeats_below_1"] > 0 or out.get("bootstrap_ci95_low_below_1", False))
    return out


def abs_deviation_comparison(base: List[float], arm: List[float]) -> Dict:
    """Per-repeat Δ|slope - 1| (arm - baseline). Negative = arm closer to 1 = better calibrated."""
    b, a = np.abs(np.asarray(base) - 1.0), np.abs(np.asarray(arm) - 1.0)
    d = a - b
    return {**{k: v for k, v in _summary(d.tolist()).items()}, "per_repeat": [float(x) for x in d],
            "repeats_ablation_worse": int((d > 0).sum()), "repeats_ablation_better": int((d < 0).sum()),
            "repeats_tied": int((d == 0).sum()),
            "convention": "worse = larger |slope - 1| (further from 1)"}


def build(record: Dict) -> Dict:
    corrections: Dict = {}
    for analysis in ANALYSES:
        s = record[analysis]
        boot = s.get("paired_group_bootstrap")
        base = s["arms"][BASELINE]["per_repeat"]["calibration_slope"]
        arms_out = {}
        for arm, v in s["arms"].items():
            slopes = v["per_repeat"]["calibration_slope"]
            saved_abs = v["per_repeat"]["abs_slope_minus_1"]
            if not np.allclose(np.abs(np.asarray(slopes) - 1), saved_abs, atol=1e-12):
                raise RuntimeError(f"{analysis}/{arm}: saved |slope-1| inconsistent with saved slopes")
            entry = {"signed_slope": signed_slope_summary(slopes, boot["absolute"][arm]["calibration_slope"] if boot else None),
                     "abs_slope_minus_1": _summary(saved_abs)}
            if arm != BASELINE:
                comp = abs_deviation_comparison(base, slopes)
                saved = s["per_repeat_differences_vs_baseline"][arm]
                if not np.allclose(comp["per_repeat"], saved["abs_slope_minus_1"]["per_repeat"], atol=1e-12):
                    raise RuntimeError(f"{analysis}/{arm}: recomputed Δ|slope-1| disagrees with saved values")
                entry["abs_slope_minus_1_vs_baseline"] = {"per_repeat": comp}
                if boot:
                    entry["abs_slope_minus_1_vs_baseline"]["paired_group_bootstrap"] = boot["differences"][arm]["abs_slope_minus_1"]
                entry["superseded_field"] = {
                    "path": f"{analysis}.per_repeat_differences_vs_baseline.{arm}.calibration_slope.repeats_ablation_worse",
                    "original_value": saved["calibration_slope"]["repeats_ablation_worse"],
                    "original_convention": "a lower signed slope was counted as worse (incorrect for calibration slope)",
                    "corrected_value": comp["repeats_ablation_worse"],
                    "corrected_convention": comp["convention"]}
            arms_out[arm] = entry
        corrections[analysis] = arms_out
    return {
        "id": "R7-C1",
        "date": "2026-11-01",
        "type": "post hoc reporting correction; no rerun, no change to any original field or pre-registered label",
        "issue": "calibration_slope.repeats_ablation_worse treated a lower signed slope as worse; for calibration slope, closer to 1 is better",
        "method": "recomputed from saved per-repeat slopes as |slope - 1| (lower is better); saved paired-bootstrap Δ|slope - 1| reused; "
                  "signed slopes reported separately with crossings below 1 flagged",
        "source_script": "experiments/r7_slope_reporting_correction.py",
        "original_content_sha256_excluding_runtime": original_content_sha256(record),
        "affects_preregistered_labels": False,
        "analyses": corrections,
    }


def apply(path: Path = RESULTS) -> Dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop(BLOCK, None)                       # idempotent: rebuild from the original fields only
    if original_content_sha256(record) != ORIGINAL_CONTENT_SHA256:
        raise RuntimeError("Original R7 result content differs from the verified reproducible content; refusing to annotate")
    record[BLOCK] = build(record)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record[BLOCK]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=RESULTS)
    args = ap.parse_args(argv)
    block = apply(args.results)
    print(json.dumps({"original_content_sha256_excluding_runtime": block["original_content_sha256_excluding_runtime"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
