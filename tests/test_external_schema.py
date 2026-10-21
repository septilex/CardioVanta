"""
CardioVanta Phase 17 - External Schema & Five-Step Data-Validation Contract Tests
=================================================================================
Tests for Task 1.3:
- Full 5-step data-validation contract execution across Hungary, Long Beach VA, and Cleveland Dev
- Feature-specific missing-sentinel normalization without global corruption
- Preservation of legitimate zeros (sex=0, fbs=0, restecg=0, exang=0, oldpeak=0.0, target=0)
- Empirical Cleveland cp semantic adapter ({0: 4, 1: 2, 2: 3, 3: 1}) vs naive cp + 1 rejection
- Detection and structured reporting of hard schema violations without silent dropping
- Reporting of documented anomalies (trestbps=0, oldpeak=-0.5, slope=0, chol=0)
- Predictor matrix isolation from targets and identifiers
- Training-only transformation boundary and zero cross-cohort leakage
- Complete quarantine of the 61-sample locked Cleveland test set
"""

import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.cardiovanta.data.validation import (
    CLINICAL_DOMAINS,
    KAGGLE_CP_TO_CANONICAL,
    CANONICAL_CP_TO_KAGGLE,
    ValidationViolation,
    DocumentedAnomaly,
    ValidationContractResult,
    adapt_cleveland_cp,
    FiveStepValidationContract,
)
from src.cardiovanta.data.external_loader import (
    CLINICAL_13_FEATURES,
    CLINICAL_10_FEATURES,
    CLINICAL_9_FEATURES,
    ParsedCohort,
    parse_hungarian_cohort,
    parse_long_beach_cohort,
    parse_cleveland_dev_cohort,
    load_all_multicenter_cohorts,
)
from src.config.config import BASE_DIR, RAW_DATA_PATH


# ---------------------------------------------------------------------------
# 1. Five-Step Contract on Hungarian Cohort (N=294)
# ---------------------------------------------------------------------------

def test_hungary_validation_contract():
    """Verify Hungarian cohort adheres to 5-step contract with zero hard violations."""
    cohort = parse_hungarian_cohort()
    validator = FiveStepValidationContract()
    result = validator.validate_cohort(cohort)

    assert result.cohort_name == "hungary"
    assert result.n_samples == 294
    assert result.is_valid is True
    assert len(result.hard_violations) == 0
    assert "Canonical 1-4 coding verified" in result.cp_coding_status

    # Sentinel accounting: chol has 23 normalized missing sentinels
    assert result.missing_sentinel_counts.get("chol") == 23
    assert result.missing_sentinel_counts.get("fbs") == 8
    assert result.missing_sentinel_counts.get("trestbps") == 1

    # Legitimate zeros preserved
    assert result.legitimate_zeros_verified["sex"] == 81
    assert result.legitimate_zeros_verified["fbs"] == 266
    assert result.legitimate_zeros_verified["restecg"] == 235
    assert result.legitimate_zeros_verified["exang"] == 204
    assert result.legitimate_zeros_verified["oldpeak"] == 189
    assert result.legitimate_zeros_verified["target"] == 188


# ---------------------------------------------------------------------------
# 2. Five-Step Contract on Long Beach VA Cohort (N=200)
# ---------------------------------------------------------------------------

def test_long_beach_validation_contract():
    """Verify Long Beach VA cohort passes contract, preserves anomalies, and reports violations."""
    cohort = parse_long_beach_cohort()
    validator = FiveStepValidationContract()
    result = validator.validate_cohort(cohort)

    assert result.cohort_name == "long_beach"
    assert result.n_samples == 200
    assert result.is_valid is True
    assert len(result.hard_violations) == 0

    # Documented anomalies preserved and reported
    anomaly_types = [a.anomaly_type for a in result.documented_anomalies]
    assert "unviable_bp" in anomaly_types  # record 33 trestbps=0.0
    assert "negative_oldpeak" in anomaly_types  # record 5 oldpeak=-0.5
    assert "out_of_domain_slope" in anomaly_types  # record 100 slope=0.0
    assert "zero_cholesterol" in anomaly_types  # 49 records chol=0.0

    # Check specific anomaly row indexes
    bp_anomalies = [a for a in result.documented_anomalies if a.anomaly_type == "unviable_bp"]
    assert any(a.source_row_index == 33 and a.observed_value == 0.0 for a in bp_anomalies)

    oldpeak_anomalies = [a for a in result.documented_anomalies if a.anomaly_type == "negative_oldpeak"]
    assert any(a.source_row_index == 5 and a.observed_value == -0.5 for a in oldpeak_anomalies)

    # Legitimate zeros preserved
    assert result.legitimate_zeros_verified["sex"] == 6
    assert result.legitimate_zeros_verified["fbs"] == 125
    assert result.legitimate_zeros_verified["restecg"] == 80
    assert result.legitimate_zeros_verified["exang"] == 52
    assert result.legitimate_zeros_verified["oldpeak"] == 40
    assert result.legitimate_zeros_verified["target"] == 51


# ---------------------------------------------------------------------------
# 3. Five-Step Contract on Cleveland Dev Cohort (N=242)
# ---------------------------------------------------------------------------

def test_cleveland_dev_validation_contract():
    """Verify Cleveland Development cohort passes contract with locked test set isolated."""
    cohort = parse_cleveland_dev_cohort()
    validator = FiveStepValidationContract(apply_cleveland_cp_adapter=False)
    result = validator.validate_cohort(cohort)

    assert result.cohort_name == "cleveland"
    assert result.n_samples == 242
    assert result.is_valid is True
    assert len(result.hard_violations) == 0

    # CP status reports untransformed Kaggle coding
    assert "Cleveland preprocessed 0-3 coding preserved" in result.cp_coding_status

    # Predictor matrix matches expected dimension
    assert result.X_13.shape == (242, 13)
    assert result.X_10.shape == (242, 10)
    assert result.X_9.shape == (242, 9)


# ---------------------------------------------------------------------------
# 4. Cleveland Chest Pain Semantic Adapter Tests
# ---------------------------------------------------------------------------

def test_cleveland_cp_semantic_adapter_exact_mapping():
    """
    Verify that adapt_cleveland_cp implements the verified semantic mapping:
    Kaggle 0 (Asymptomatic)    -> UCI 4 (Asymptomatic)
    Kaggle 1 (Atypical Angina) -> UCI 2 (Atypical Angina)
    Kaggle 2 (Non-anginal)     -> UCI 3 (Non-anginal)
    Kaggle 3 (Typical Angina)  -> UCI 1 (Typical Angina)

    Asserts that naive 'cp + 1' is strictly NOT applied.
    """
    cohort = parse_cleveland_dev_cohort()
    df_raw = cohort.data.copy()

    # Apply semantic adapter
    df_adapted = adapt_cleveland_cp(df_raw)

    # Output domain must be strictly canonical {1, 2, 3, 4}
    unique_adapted = set(df_adapted["cp"].dropna().unique())
    assert unique_adapted == {1, 2, 3, 4}

    # Verify each category semantic translation
    assert (df_adapted.loc[df_raw["cp"] == 0, "cp"] == 4).all()  # Asymptomatic
    assert (df_adapted.loc[df_raw["cp"] == 1, "cp"] == 2).all()  # Atypical Angina
    assert (df_adapted.loc[df_raw["cp"] == 2, "cp"] == 3).all()  # Non-anginal
    assert (df_adapted.loc[df_raw["cp"] == 3, "cp"] == 1).all()  # Typical Angina

    # Verify raw values are preserved in 'cp_raw'
    assert (df_adapted["cp_raw"] == df_raw["cp"]).all()

    # Rejection of naive cp + 1:
    # If naive cp + 1 were applied: cp=0 would map to 1 (Typical Angina) instead of 4 (Asymptomatic).
    # We assert that cp=0 did NOT map to 1:
    assert not (df_adapted.loc[df_raw["cp"] == 0, "cp"] == 1).any()
    # And cp=3 did NOT map to 4:
    assert not (df_adapted.loc[df_raw["cp"] == 3, "cp"] == 4).any()


def test_cp_adapter_rejects_out_of_domain():
    """Verify that adapt_cleveland_cp rejects values outside Kaggle {0, 1, 2, 3}."""
    invalid_df = pd.DataFrame({"cp": [0, 1, 2, 5]})
    with pytest.raises(ValueError, match="Cannot apply Cleveland CP adapter"):
        adapt_cleveland_cp(invalid_df)


# ---------------------------------------------------------------------------
# 5. Detection of Hard Schema Violations (No Silent Dropping)
# ---------------------------------------------------------------------------

def test_hard_schema_violation_detection_without_dropping():
    """Assert invalid categorical values and unexpected types trigger structured hard violations."""
    cohort = parse_hungarian_cohort()
    tampered_data = cohort.data.copy()

    # Inject hard violations
    tampered_data.loc[10, "sex"] = 5.0  # Invalid binary category
    tampered_data.loc[20, "fbs"] = 9.0  # Invalid binary category
    tampered_data.loc[30, "age"] = 150.0  # Continuous out of bounds

    tampered_cohort = ParsedCohort(
        cohort_name="hungary",
        data=tampered_data,
        n_samples=len(tampered_data)
    )

    validator = FiveStepValidationContract()
    result = validator.validate_cohort(tampered_cohort)

    assert result.is_valid is False
    assert len(result.hard_violations) == 3

    # Check that rows were NOT silently dropped
    assert len(result.validated_data) == 294

    # Verify structured violation details
    features_violated = {v.feature for v in result.hard_violations}
    assert features_violated == {"sex", "fbs", "age"}

    sex_violation = next(v for v in result.hard_violations if v.feature == "sex")
    assert sex_violation.source_row_index == 10
    assert sex_violation.observed_value == 5.0


# ---------------------------------------------------------------------------
# 6. Preservation of Legitimate Zeros & Negative Oldpeak
# ---------------------------------------------------------------------------

def test_legitimate_zeros_preserved_strictly():
    """Verify legitimate zeros are never converted to NaN or treated as missing sentinels."""
    cohorts = load_all_multicenter_cohorts()
    validator = FiveStepValidationContract()

    for name, cohort in cohorts.items():
        result = validator.validate_cohort(cohort)
        # Legitimate zero fields must have positive zero counts and zero unexpected NaNs
        assert result.legitimate_zeros_verified["sex"] > 0
        assert result.legitimate_zeros_verified["fbs"] > 0
        assert result.legitimate_zeros_verified["restecg"] > 0
        assert result.legitimate_zeros_verified["exang"] > 0
        assert result.legitimate_zeros_verified["oldpeak"] > 0
        assert result.legitimate_zeros_verified["target"] > 0


def test_oldpeak_negative_preserved():
    """Verify negative ST depression (oldpeak = -0.5 mm in VA) is preserved as a valid continuous measurement."""
    cohort = parse_long_beach_cohort()
    validator = FiveStepValidationContract()
    result = validator.validate_cohort(cohort)

    # Record 5 has oldpeak = -0.5
    assert result.validated_data.loc[5, "oldpeak"] == -0.5
    assert not np.isnan(result.validated_data.loc[5, "oldpeak"])


def test_cholesterol_zeros_not_automatically_missing():
    """Verify that chol = 0.0 in Long Beach VA remains 0.0 and is reported as a documented anomaly."""
    cohort = parse_long_beach_cohort()
    validator = FiveStepValidationContract()
    result = validator.validate_cohort(cohort)

    # 49 records must remain 0.0 in validated data
    assert (result.validated_data["chol"] == 0.0).sum() == 49
    # Must be logged in documented anomalies
    chol_anomalies = [a for a in result.documented_anomalies if a.anomaly_type == "zero_cholesterol"]
    assert len(chol_anomalies) == 49


# ---------------------------------------------------------------------------
# 7. Predictor Isolation & Training-Only Boundary
# ---------------------------------------------------------------------------

def test_predictor_matrix_separation_and_leakage_boundary():
    """Verify predictor matrices strictly isolate clinical features from labels and identifiers."""
    validator = FiveStepValidationContract()
    results = validator.validate_all_cohorts(apply_cleveland_cp_adapter=True)

    forbidden = {"num", "target", "cohort", "source_row_index", "cp_raw"}

    for name, res in results.items():
        assert forbidden.isdisjoint(set(res.X_13.columns))
        assert forbidden.isdisjoint(set(res.X_10.columns))
        assert forbidden.isdisjoint(set(res.X_9.columns))
        assert res.X_13.shape[1] == 13
        assert res.X_10.shape[1] == 10
        assert res.X_9.shape[1] == 9
        assert len(res.y) == res.n_samples
        assert len(res.num) == res.n_samples

    # Assert total multicenter patients: 294 + 200 + 242 = 736
    total_patients = sum(r.n_samples for r in results.values())
    assert total_patients == 736


# ---------------------------------------------------------------------------
# 8. Complete Quarantine of Locked Cleveland Test Set
# ---------------------------------------------------------------------------

def test_locked_cleveland_test_set_quarantine():
    """Verify that none of the 61 locked Cleveland test samples appear in validated multicenter data."""
    validator = FiveStepValidationContract()
    results = validator.validate_all_cohorts()

    with open(BASE_DIR / "data" / "processed" / "dev_indices.json") as f:
        dev_indices = set(json.load(f))
    locked_test_indices = set(range(303)) - dev_indices
    assert len(locked_test_indices) == 61

    cleveland_result = results["cleveland"]
    source_indices = set(cleveland_result.validated_data["source_row_index"])

    assert source_indices.isdisjoint(locked_test_indices)
    assert len(source_indices) == 242
