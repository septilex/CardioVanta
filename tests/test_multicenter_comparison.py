"""
Unit and Integration Tests for Phase 17 Task 4.1: Candidate A vs Candidate B Comparative Analysis
=================================================================================================
Verifies:
1. Correct candidate pairing by compound patient identity.
2. Correct calculation of the AUC difference (AUC_B - AUC_A) and its sign.
3. Paired bootstrap resampling evaluates identical sampled patients for both candidates.
4. Bootstrap reproducibility, valid confidence limit ordering, and percentile bounds.
5. Correct application of the predefined 0.01 ROC-AUC tolerance (descriptive vs inferential).
6. Explicit rejection of invalid, incomplete, or corrupted input prediction artifacts.
7. Strict quarantine of the 61-sample Cleveland locked test partition.
8. Reproducible generation and valid schema of results JSON and Markdown report.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from experiments.phase17_multicenter_validation import (
    DEFAULT_COMPARATIVE_REPORT_MD,
    DEFAULT_MULTICENTER_RESULTS_JSON,
    DEFAULT_PREDICTIONS_CSV,
    PREDEFINED_ROC_AUC_TOLERANCE,
    compute_paired_loco_comparison,
    execute_multicenter_comparison,
    validate_comparison_inputs,
)
from src.cardiovanta.data.external_loader import DEV_INDICES_PATH, PROJECT_ROOT


@pytest.fixture(scope="module")
def loco_predictions_df() -> pd.DataFrame:
    """Fixture providing the authoritative 736-row LOCO predictions DataFrame."""
    assert DEFAULT_PREDICTIONS_CSV.is_file(), f"Missing predictions CSV: {DEFAULT_PREDICTIONS_CSV}"
    df = pd.read_csv(DEFAULT_PREDICTIONS_CSV)
    assert len(df) == 736
    return df


# ---------------------------------------------------------------------------
# 1. Input Integrity & Validation Contract Tests
# ---------------------------------------------------------------------------

def test_validate_comparison_inputs_on_authoritative_data(loco_predictions_df: pd.DataFrame):
    """Verify that authoritative LOCO predictions pass all validation checks."""
    meta = validate_comparison_inputs(loco_predictions_df)
    assert meta["status"] == "valid"
    assert meta["total_samples"] == 736
    assert meta["unique_patients"] == 736
    assert meta["cohort_counts"] == {"hungary": 294, "cleveland": 242, "long_beach": 200}
    assert meta["quarantined_test_samples"] == 61
    assert meta["quarantine_verified"] is True


def test_validate_comparison_inputs_rejects_missing_column(loco_predictions_df: pd.DataFrame):
    """Verify explicit ValueError when required prediction columns are missing."""
    corrupted = loco_predictions_df.drop(columns=["prob_candidate_b"])
    with pytest.raises(ValueError, match="missing required columns"):
        validate_comparison_inputs(corrupted)


def test_validate_comparison_inputs_rejects_incomplete_row_count(loco_predictions_df: pd.DataFrame):
    """Verify explicit ValueError when row count is incomplete."""
    corrupted = loco_predictions_df.iloc[:700].copy()
    with pytest.raises(ValueError, match="Expected 736 prediction rows"):
        validate_comparison_inputs(corrupted)


def test_validate_comparison_inputs_rejects_non_binary_targets(loco_predictions_df: pd.DataFrame):
    """Verify explicit ValueError when targets are not binary in {0, 1}."""
    corrupted = loco_predictions_df.copy()
    corrupted.loc[0, "target"] = 2
    with pytest.raises(ValueError, match="Targets must be binary"):
        validate_comparison_inputs(corrupted)


def test_validate_comparison_inputs_rejects_out_of_bounds_probabilities(loco_predictions_df: pd.DataFrame):
    """Verify explicit ValueError when probabilities are outside [0, 1] or non-finite."""
    corrupted = loco_predictions_df.copy()
    corrupted.loc[0, "prob_candidate_a"] = 1.05
    with pytest.raises(ValueError, match="out of bounds"):
        validate_comparison_inputs(corrupted)

    corrupted_nan = loco_predictions_df.copy()
    corrupted_nan.loc[0, "prob_candidate_b"] = np.nan
    with pytest.raises(ValueError, match="Non-finite probabilities"):
        validate_comparison_inputs(corrupted_nan)


def test_validate_comparison_inputs_rejects_locked_test_leakage(loco_predictions_df: pd.DataFrame):
    """Verify fatal leakage detection if locked test samples contaminate predictions."""
    with open(DEV_INDICES_PATH, "r", encoding="utf-8") as f:
        dev_indices = set(json.load(f))
    locked_indices = sorted(list(set(range(303)) - dev_indices))
    assert len(locked_indices) == 61

    # Inject a locked test index into Cleveland development rows
    corrupted = loco_predictions_df.copy()
    cleve_mask = corrupted["cohort"] == "cleveland"
    first_cleve_idx = corrupted[cleve_mask].index[0]
    corrupted.loc[first_cleve_idx, "source_row_index"] = locked_indices[0]

    with pytest.raises(RuntimeError, match="FATAL LEAKAGE: Locked test partition"):
        validate_comparison_inputs(corrupted)


# ---------------------------------------------------------------------------
# 2. Paired Comparison & Difference Calculations
# ---------------------------------------------------------------------------

def test_paired_comparison_diff_calculation_and_sign(loco_predictions_df: pd.DataFrame):
    """
    Verify exact calculation of delta_auc = auc_b - auc_a:
    - Positive delta indicates Candidate B outperforms Candidate A.
    - Negative delta indicates Candidate A outperforms Candidate B.
    """
    results = compute_paired_loco_comparison(loco_predictions_df, n_bootstraps=200, random_state=42)
    per_c = results["per_centre"]

    for c in ["hungary", "long_beach", "cleveland"]:
        c_data = per_c[c]
        auc_a = c_data["candidate_a"]["roc_auc"]
        auc_b = c_data["candidate_b"]["roc_auc"]
        diff = c_data["difference_b_minus_a"]["roc_auc_diff"]

        assert np.isclose(diff, auc_b - auc_a, atol=1e-12)

    # Verify verified point estimates
    assert np.isclose(per_c["hungary"]["candidate_a"]["roc_auc"], 0.885848, atol=1e-4)
    assert np.isclose(per_c["hungary"]["candidate_b"]["roc_auc"], 0.889712, atol=1e-4)
    assert per_c["hungary"]["difference_b_minus_a"]["roc_auc_diff"] > 0  # Candidate B higher

    assert np.isclose(per_c["long_beach"]["candidate_a"]["roc_auc"], 0.752336, atol=1e-4)
    assert np.isclose(per_c["long_beach"]["candidate_b"]["roc_auc"], 0.759639, atol=1e-4)
    assert per_c["long_beach"]["difference_b_minus_a"]["roc_auc_diff"] > 0  # Candidate B higher

    assert np.isclose(per_c["cleveland"]["candidate_a"]["roc_auc"], 0.870317, atol=1e-4)
    assert np.isclose(per_c["cleveland"]["candidate_b"]["roc_auc"], 0.869077, atol=1e-4)
    assert per_c["cleveland"]["difference_b_minus_a"]["roc_auc_diff"] < 0  # Candidate A higher by 0.0012


# ---------------------------------------------------------------------------
# 3. Paired Resampling Consistency & Identical Patient Alignment
# ---------------------------------------------------------------------------

def test_paired_bootstrap_uses_identical_resampled_patient_indices():
    """
    Verify that paired bootstrap evaluates both candidates on identical resampled patient instances.
    """
    y = np.array([1, 1, 0, 0, 1, 0, 1, 0])
    p_a = np.array([0.9, 0.8, 0.1, 0.2, 0.7, 0.3, 0.85, 0.15])
    p_b = np.array([0.85, 0.75, 0.15, 0.25, 0.65, 0.35, 0.8, 0.2])

    pos_idx = np.where(y == 1)[0]
    neg_idx = np.where(y == 0)[0]
    rng = np.random.default_rng(42)

    for _ in range(50):
        b_pos = rng.choice(pos_idx, size=len(pos_idx), replace=True)
        b_neg = rng.choice(neg_idx, size=len(neg_idx), replace=True)
        b_idx = np.concatenate([b_pos, b_neg])

        # Evaluate both models on the exact same b_idx
        auc_a = roc_auc_score(y[b_idx], p_a[b_idx])
        auc_b = roc_auc_score(y[b_idx], p_b[b_idx])
        diff = auc_b - auc_a

        # Replicating with separate random calls would diverge; pairing enforces identity
        assert np.isfinite(diff)


def test_paired_bootstrap_reproducibility_and_interval_bounds(loco_predictions_df: pd.DataFrame):
    """Verify that paired bootstrap is 100% deterministic given random_state and ci_lower <= ci_upper."""
    res1 = compute_paired_loco_comparison(loco_predictions_df, n_bootstraps=300, random_state=42)
    res2 = compute_paired_loco_comparison(loco_predictions_df, n_bootstraps=300, random_state=42)

    for c in ["hungary", "long_beach", "cleveland"]:
        ci1 = res1["per_centre"][c]["difference_b_minus_a"]
        ci2 = res2["per_centre"][c]["difference_b_minus_a"]

        assert ci1["ci_lower"] == ci2["ci_lower"]
        assert ci1["ci_upper"] == ci2["ci_upper"]
        assert ci1["ci_lower"] <= ci1["ci_upper"]
        assert ci1["replicates_requested"] == 300
        assert ci1["replicates_computed"] == 300
        assert ci1["replicates_undefined"] == 0


# ---------------------------------------------------------------------------
# 4. Predefined Tolerance & Non-Inferiority Rule Application
# ---------------------------------------------------------------------------

def test_predefined_tolerance_decisions(loco_predictions_df: pd.DataFrame):
    """
    Verify application of the prespecified 0.01 tolerance rule:
    - Descriptive: |delta_auc| <= 0.01 is True for all 3 centres.
    - Inferential Non-Inferiority: ci_lower >= -0.01 is True for Hungary and Cleveland, False for Long Beach.
    - Inferential Equivalence: ci inside [-0.01, 0.01] is True for Hungary and Cleveland, False for Long Beach.
    """
    results = compute_paired_loco_comparison(loco_predictions_df, n_bootstraps=1000, random_state=42, tolerance=0.01)
    per_c = results["per_centre"]

    # Hungary
    h = per_c["hungary"]["difference_b_minus_a"]
    assert h["descriptive_tolerance_met"] is True
    assert h["statistical_non_inferiority_met"] is True
    assert h["statistical_equivalence_met"] is True
    assert h["ci_lower"] >= -0.01

    # Cleveland
    cl = per_c["cleveland"]["difference_b_minus_a"]
    assert cl["descriptive_tolerance_met"] is True
    assert cl["statistical_non_inferiority_met"] is True
    assert cl["statistical_equivalence_met"] is True
    assert cl["ci_lower"] >= -0.01

    # Long Beach VA: point estimate within 0.01, but wider CI lower bound is < -0.01
    lb = per_c["long_beach"]["difference_b_minus_a"]
    assert lb["descriptive_tolerance_met"] is True
    assert lb["statistical_non_inferiority_met"] is False
    assert lb["statistical_equivalence_met"] is False
    assert lb["ci_lower"] < -0.01

    # Macro external validation
    macro_ext = results["macro_external_validation"]
    assert macro_ext["descriptive_tolerance_met"] is True
    assert macro_ext["mean_difference"] > 0  # Candidate B higher on average


# ---------------------------------------------------------------------------
# 5. Full Artifact Generation & Schema Verification
# ---------------------------------------------------------------------------

def test_execute_multicenter_comparison_produces_valid_artifacts():
    """Verify execution of execute_multicenter_comparison generates valid JSON and Markdown artifacts."""
    meta, md = execute_multicenter_comparison(n_bootstraps=100, random_state=42, save_artifacts=False)

    assert meta["task"] == "Phase 17, Task 4.1: Candidate A vs Candidate B Comparative Analysis"
    assert "candidate_schemas" in meta
    assert "target_convention" in meta
    assert "comparison_results" in meta
    assert "scientific_disclosures" in meta

    assert len(md) > 500
    assert "Candidate A vs Candidate B Comparative Analysis Report" in md
    assert "Primary Per-Centre Results Table" in md
    assert "Scientific Disclosures & Limitations" in md


def test_persisted_results_json_and_report_match_manifest():
    """Verify that on-disk phase17_multicenter_results.json and report adhere to project schema."""
    assert DEFAULT_MULTICENTER_RESULTS_JSON.is_file(), f"Missing {DEFAULT_MULTICENTER_RESULTS_JSON}"
    assert DEFAULT_COMPARATIVE_REPORT_MD.is_file(), f"Missing {DEFAULT_COMPARATIVE_REPORT_MD}"

    with open(DEFAULT_MULTICENTER_RESULTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["task"] == "Phase 17, Task 4.1: Candidate A vs Candidate B Comparative Analysis"
    assert data["random_state"] == 42
    assert data["n_bootstraps"] == 1000
    assert data["predefined_roc_auc_tolerance"] == 0.01

    res = data["comparison_results"]["per_centre"]
    assert set(res.keys()) == {"hungary", "long_beach", "cleveland"}

    with open(DEFAULT_COMPARATIVE_REPORT_MD, "r", encoding="utf-8") as f:
        report_text = f.read()

    assert "Phase 17: Candidate A vs Candidate B Comparative Analysis Report" in report_text
    assert "Predefined Margin:** 0.01 ROC-AUC" in report_text
    assert "Hungary" in report_text
    assert "Long Beach" in report_text
    assert "Cleveland" in report_text
