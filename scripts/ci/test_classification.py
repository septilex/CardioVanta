"""
Explicit classification of every test module for CI (research-data quarantine).

Classes
-------
ci_safe                 synthetic / documentation-only; runs in every default CI job under the quarantine
ci_safe_research_deps   same, but needs the research dependency stack (requirements.txt); runs only in the
                        quarantined research job
research_data           reads quarantined data (heart.csv including locked rows, development indices,
                        external cohorts, locked-derived results) and/or retrains models or rewrites research
                        outputs; NEVER run in CI

Evidence (2026-11-01): each module was run in a checkout without any quarantined file, with the runtime
guard active (Python 3.12 dev stack and Python 3.11 research stack). ``ci_safe`` modules passed with zero
refused accesses; ``research_data`` modules attempted quarantined access (recorded below) or, for
helpers without tests, reference raw data paths. New test modules must be added here (CI fails otherwise).

CLI:  python scripts/ci/test_classification.py --list ci_safe [--list ci_safe_research_deps]
      python scripts/ci/test_classification.py --check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
CLASSES = ("ci_safe", "ci_safe_research_deps", "research_data")
TEST_DIRS = ("tests", "backend/tests")

CLASSIFICATION: Dict[str, Dict[str, str]] = {
    # ---- backend synthetic suite (512 tests passed under quarantine, 0 refused accesses) ----
    **{f"backend/tests/{n}.py": {"class": "ci_safe", "reason": "synthetic backend/registry/contract/deployment test"}
       for n in ("test_phase13_shap", "test_r0_outcome_semantics", "test_r1_feature_contract", "test_r2_registry",
                 "test_r3_deployment", "test_stage1", "test_stage2", "test_stage3", "test_stage4",
                 "test_stage5_contract", "test_stage6_security")},
    # ---- tests/: safe ----
    "tests/test_artifact_integrity.py": {"class": "ci_safe", "reason": "hashes production artifacts (reference predictions are development rows)"},
    "tests/test_monitoring.py": {"class": "ci_safe", "reason": "synthetic telemetry tests"},
    "tests/test_data_quarantine.py": {"class": "ci_safe", "reason": "quarantine guard tests; runtime tests use a synthetic fake root"},
    "tests/test_r4_ca_count_encoding.py": {"class": "ci_safe", "reason": "synthetic data; loader tested on a synthetic CSV"},
    "tests/test_h2_calibration_recipe.py": {"class": "ci_safe", "reason": "synthetic data only"},
    "tests/test_h2_1_calibration_confirmation.py": {"class": "ci_safe", "reason": "synthetic data only"},
    "tests/test_r5_explanation_stability.py": {"class": "ci_safe", "reason": "synthetic profiles; production model loaded read-only via registry"},
    "tests/test_r6_codebook_resolution.py": {"class": "ci_safe", "reason": "reads documentation and project records only"},
    "tests/test_r7_unverified_feature_ablation.py": {"class": "ci_safe", "reason": "synthetic data only"},
    "tests/test_r7_slope_reporting_correction.py": {"class": "ci_safe", "reason": "reads saved development-only R7 aggregates"},
    "tests/test_phase3.py": {"class": "ci_safe_research_deps", "reason": "passed with 0 refused accesses; imports matplotlib via src.experiment.phase3"},
    # ---- tests/: research data (never run in CI) ----
    "tests/test_drift_data_gen.py": {"class": "research_data", "reason": "helper without tests; builds drift data from RAW_DATA_PATH"},
    "tests/test_drift_detection.py": {"class": "research_data", "reason": "refused: data/processed/dev_indices.json"},
    "tests/test_error_analysis.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv (load_dev_data); locked error-analysis module"},
    "tests/test_experiment.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv"},
    "tests/test_external_provenance.py": {"class": "research_data", "reason": "requires external cohort raw files and development indices"},
    "tests/test_external_schema.py": {"class": "research_data", "reason": "refused: data/external/raw/hungarian.data"},
    "tests/test_foundation.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv; rebuilds the split"},
    "tests/test_global_leakage.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv (load_dev_data)"},
    "tests/test_loco_evaluation.py": {"class": "research_data", "reason": "refused: data/external/raw/hungarian.data; refits LOCO pipelines"},
    "tests/test_multicenter_comparison.py": {"class": "research_data", "reason": "refused: data/processed/dev_indices.json"},
    "tests/test_multicenter_leakage.py": {"class": "research_data", "reason": "requires development indices; refits pipelines on cohort data"},
    "tests/test_multicenter_pipelines.py": {"class": "research_data", "reason": "refused: data/external/raw/hungarian.data; refits pipelines"},
    "tests/test_nested_lda_evaluation.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv and locked-derived nested_lda_evaluation.json"},
    "tests/test_nested_threshold_optimization.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv and locked-derived nested_threshold_optimization.json"},
    "tests/test_next_research_phase.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv and locked-derived nested_cv_90pct_results.json"},
    "tests/test_phase16_feature_engineering.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv; refits candidate pipelines"},
    "tests/test_phase4a.py": {"class": "research_data", "reason": "refused: data/processed/dev_indices.json"},
    "tests/test_phase4b.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv; run_phase4b() retrains and rewrites reports/phase4b_*"},
    "tests/test_phase5.py": {"class": "research_data", "reason": "refused: data/raw/heart.csv; checks production training provenance"},
}


def of_class(name: str) -> List[str]:
    return sorted(p for p, v in CLASSIFICATION.items() if v["class"] == name)


def ci_safe() -> List[str]:
    return of_class("ci_safe")


def research_data() -> List[str]:
    return of_class("research_data")


def discovered(root: Path = REPO_ROOT) -> List[str]:
    out = []
    for d in TEST_DIRS:
        out += [p.relative_to(root).as_posix() for p in (root / d).glob("test_*.py")]
    return sorted(out)


def check(root: Path = REPO_ROOT) -> List[str]:
    problems = []
    found = set(discovered(root))
    for p in sorted(found - set(CLASSIFICATION)):
        problems.append(f"UNCLASSIFIED test module: {p} (add it to scripts/ci/test_classification.py)")
    for p in sorted(set(CLASSIFICATION) - found):
        problems.append(f"STALE classification: {p} does not exist")
    for p, v in CLASSIFICATION.items():
        if v.get("class") not in CLASSES or not v.get("reason"):
            problems.append(f"INVALID classification entry: {p}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="append", choices=CLASSES)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        problems = check()
        for p in problems:
            print(f"::error::{p}")
        print(f"Test classification: {len(CLASSIFICATION)} module(s), {len(problems)} problem(s).")
        return 1 if problems else 0
    if args.list:
        print(" ".join(p for c in args.list for p in of_class(c)))
        return 0
    ap.error("use --list CLASS or --check")


if __name__ == "__main__":
    sys.exit(main())
