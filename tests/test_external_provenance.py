"""
CardioVanta Phase 17 - External Dataset Provenance & Integrity Tests
====================================================================
Tests for Task 1.1:
- Cryptographic SHA-256 verification and corruption detection
- Embedded CC BY 4.0 metadata, citations, and regulatory disclaimer
- Programmatic parsing of raw 76-attribute record structure
- Empirical inspection of canonical cp coding (1–4)
- Sentinel token inventory ('?' vs '-9')
- Empirical cholesterol zero accounting
- Protection of legitimate zero clinical measurements
- Strict quarantine and preservation of locked Cleveland data
"""

import hashlib
import json
import pytest
import pandas as pd
from pathlib import Path

from src.cardiovanta.data.external_loader import (
    LICENSE_METADATA,
    INVESTIGATOR_ATTRIBUTION,
    AUTHORITATIVE_SOURCES,
    RAW_76_ATTRIBUTE_MAPPING,
    STANDARD_14_FEATURES,
    CLINICAL_13_FEATURES,
    CLINICAL_10_FEATURES,
    CLINICAL_9_FEATURES,
    ParsedCohort,
    calculate_sha256,
    verify_file_integrity,
    download_external_datasets,
    parse_raw_76_record_file,
    profile_raw_cohort,
    generate_multicenter_profiling_report,
    parse_hungarian_cohort,
    parse_long_beach_cohort,
    parse_cleveland_dev_cohort,
    load_all_multicenter_cohorts,
)
from src.config.config import BASE_DIR, RAW_DATA_PATH

DATA_EXTERNAL_RAW = BASE_DIR / "data" / "external" / "raw"
HUNGARIAN_PATH = DATA_EXTERNAL_RAW / "hungarian.data"
VA_PATH = DATA_EXTERNAL_RAW / "long-beach-va.data"
NAMES_PATH = DATA_EXTERNAL_RAW / "heart-disease.names"


# ---------------------------------------------------------------------------
# 1. License, Citation, and Regulatory Disclaimer Tests
# ---------------------------------------------------------------------------

def test_license_metadata_and_regulatory_disclaimer():
    """Assert CC BY 4.0 license metadata, DOI, and regulatory disclaimer are embedded."""
    assert LICENSE_METADATA["license_spdx"] == "CC-BY-4.0"
    assert "10.24432/C56327" in LICENSE_METADATA["doi"]
    assert "FDA 510(k)" in LICENSE_METADATA["regulatory_disclaimer"]
    assert "clinical validation" in LICENSE_METADATA["regulatory_disclaimer"].lower()


def test_investigator_citations_and_attribution():
    """Assert attribution to Dr. Janosi, Dr. Detrano, Dr. Steinbrunn, Dr. Pfisterer, and David Aha."""
    assert "Janosi" in INVESTIGATOR_ATTRIBUTION["hungary"]["investigator"]
    assert "Detrano" in INVESTIGATOR_ATTRIBUTION["long_beach"]["investigator"]
    assert "Detrano" in INVESTIGATOR_ATTRIBUTION["cleveland"]["investigator"]
    assert "Steinbrunn" in INVESTIGATOR_ATTRIBUTION["switzerland"]["investigator"]
    assert INVESTIGATOR_ATTRIBUTION["hungary"]["expected_n"] == 294
    assert INVESTIGATOR_ATTRIBUTION["long_beach"]["expected_n"] == 200


# ---------------------------------------------------------------------------
# 2. Cryptographic SHA-256 Integrity Tests
# ---------------------------------------------------------------------------

def test_authoritative_source_hashes():
    """Verify downloaded files match expected authoritative SHA-256 checksums."""
    assert HUNGARIAN_PATH.exists(), f"Missing raw file: {HUNGARIAN_PATH}"
    assert VA_PATH.exists(), f"Missing raw file: {VA_PATH}"
    assert NAMES_PATH.exists(), f"Missing raw file: {NAMES_PATH}"

    assert verify_file_integrity(HUNGARIAN_PATH, AUTHORITATIVE_SOURCES["hungarian.data"]["sha256"])
    assert verify_file_integrity(VA_PATH, AUTHORITATIVE_SOURCES["long-beach-va.data"]["sha256"])
    assert verify_file_integrity(NAMES_PATH, AUTHORITATIVE_SOURCES["heart-disease.names"]["sha256"])


def test_corruption_detection_raises_error(tmp_path):
    """Verify that any bit corruption triggers an immediate integrity failure."""
    corrupted_file = tmp_path / "corrupted.data"
    corrupted_file.write_bytes(b"tampered data content")

    expected_sha = AUTHORITATIVE_SOURCES["hungarian.data"]["sha256"]
    with pytest.raises(ValueError, match="Cryptographic integrity verification failed"):
        verify_file_integrity(corrupted_file, expected_sha)


# ---------------------------------------------------------------------------
# 3. Raw 76-Attribute Record Parsing Tests
# ---------------------------------------------------------------------------

def test_hungarian_raw_record_layout():
    """Assert hungarian.data has exactly 294 records, 10 lines/rec, and 76 tokens/rec."""
    df, diag = parse_raw_76_record_file(HUNGARIAN_PATH, extract_14_features=True)
    assert len(df) == 294
    assert diag["total_records_delimited"] == 294
    assert diag["is_uniform_76"] is True
    assert diag["token_counts_per_record"] == [76]
    assert diag["leftover_tokens"] == 0
    assert list(df.columns) == STANDARD_14_FEATURES


def test_long_beach_va_raw_record_layout():
    """Assert long-beach-va.data has exactly 200 records, 10 lines/rec, and 76 tokens/rec."""
    df, diag = parse_raw_76_record_file(VA_PATH, extract_14_features=True)
    assert len(df) == 200
    assert diag["total_records_delimited"] == 200
    assert diag["is_uniform_76"] is True
    assert diag["token_counts_per_record"] == [76]
    assert diag["leftover_tokens"] == 0
    assert list(df.columns) == STANDARD_14_FEATURES


# ---------------------------------------------------------------------------
# 4. Chest Pain (cp) Coding Inspection Tests
# ---------------------------------------------------------------------------

def test_canonical_cp_coding_verification():
    """Verify empirically that both cohorts use canonical 1–4 coding and zero '0' values exist."""
    df_h, _ = parse_raw_76_record_file(HUNGARIAN_PATH)
    df_va, _ = parse_raw_76_record_file(VA_PATH)

    for name, df in [("Hungary", df_h), ("Long Beach VA", df_va)]:
        cp_vals = set(df["cp"].unique())
        assert cp_vals.issubset({"1", "2", "3", "4"}), f"{name} contains non-canonical cp values: {cp_vals}"
        assert "0" not in cp_vals, f"{name} contains unexpected cp=0!"

    # Check exact counts
    h_counts = dict(df_h["cp"].value_counts())
    assert h_counts == {"1": 11, "2": 106, "3": 54, "4": 123}

    va_counts = dict(df_va["cp"].value_counts())
    assert va_counts == {"1": 8, "2": 14, "3": 47, "4": 131}


# ---------------------------------------------------------------------------
# 5. Sentinel Token Inventory Tests
# ---------------------------------------------------------------------------

def test_sentinel_accounting_in_raw_files():
    """Verify that '?' occurs 0 times in raw files and missing values are coded as '-9'."""
    df_h, _ = parse_raw_76_record_file(HUNGARIAN_PATH)
    df_va, _ = parse_raw_76_record_file(VA_PATH)

    for df in [df_h, df_va]:
        # '?' should not exist in raw 76-attribute files
        q_count = (df.values == "?").sum()
        assert q_count == 0, f"Found unexpected '?' in raw file: {q_count}"

    # Hungary has -9 sentinels in trestbps, chol, fbs, restecg, thalach, exang, slope, ca, thal
    assert (df_h["chol"] == "-9").sum() == 23
    assert (df_h["trestbps"] == "-9").sum() == 1
    assert (df_h["fbs"] == "-9").sum() == 8

    # Long Beach has -9 sentinels in trestbps, chol, fbs, thalach, exang, oldpeak, slope, ca, thal
    assert (df_va["chol"] == "-9").sum() == 7
    assert (df_va["trestbps"] == "-9").sum() == 56
    assert (df_va["oldpeak"] == "-9").sum() == 56


# ---------------------------------------------------------------------------
# 6. Empirical Cholesterol Zero Accounting Tests
# ---------------------------------------------------------------------------

def test_cholesterol_zero_reconciliation():
    """Verify empirical cholesterol counts against literature provisional estimates."""
    df_h, _ = parse_raw_76_record_file(HUNGARIAN_PATH)
    df_va, _ = parse_raw_76_record_file(VA_PATH)

    # In Hungary: literature said ~23 zeros; empirical inspection shows 0 zeros and 23 '-9' sentinels!
    h_zeros = (df_h["chol"] == "0").sum()
    h_neg9 = (df_h["chol"] == "-9").sum()
    assert h_zeros == 0
    assert h_neg9 == 23
    assert 294 - h_neg9 == 271  # 271 valid positive cholesterol values

    # In Long Beach VA: literature said ~131 zeros; empirical inspection shows 49 exact '0' and 7 '-9'
    va_zeros = (df_va["chol"] == "0").sum()
    va_neg9 = (df_va["chol"] == "-9").sum()
    assert va_zeros == 49
    assert va_neg9 == 7
    assert 200 - (va_zeros + va_neg9) == 144  # 144 valid positive cholesterol values


# ---------------------------------------------------------------------------
# 7. Preservation of Legitimate Zeros Tests
# ---------------------------------------------------------------------------

def test_legitimate_zeros_preserved():
    """Verify that legitimate zero measurements exist and are accounted for."""
    df_h, _ = parse_raw_76_record_file(HUNGARIAN_PATH)
    df_va, _ = parse_raw_76_record_file(VA_PATH)

    # Check that female sex (0), normal fbs (0), normal restecg (0), no angina (0), isoelectric oldpeak (0), target 0 exist
    for df in [df_h, df_va]:
        assert (df["sex"] == "0").sum() > 0
        assert (df["fbs"] == "0").sum() > 0
        assert (df["restecg"] == "0").sum() > 0
        assert (df["exang"] == "0").sum() > 0
        assert ((df["oldpeak"] == "0") | (df["oldpeak"] == "0.0")).sum() > 0
        assert (df["num"] == "0").sum() > 0


# ---------------------------------------------------------------------------
# 8. Detection of Documented Domain Anomalies
# ---------------------------------------------------------------------------

def test_detected_domain_anomalies():
    """Verify profiling detects known anomalies: trestbps=0 and oldpeak=-0.5 in VA."""
    profile_va = profile_raw_cohort(VA_PATH, "Long Beach VA")
    violations = profile_va.detected_domain_violations

    # Must detect trestbps=0 in record 33
    assert any("trestbps=0" in v for v in violations)
    # Must detect negative oldpeak (-0.5 mm)
    assert any("oldpeak=-0.5" in v for v in violations)
    # Must detect slope=0 in record 100
    assert any("slope=0" in v for v in violations)


# ---------------------------------------------------------------------------
# 9. Cleveland Baseline & Test Set Quarantine Tests
# ---------------------------------------------------------------------------

def test_cleveland_dev_and_locked_test_quarantine():
    """Verify that Cleveland raw data and dev split remain untouched and quarantined."""
    assert RAW_DATA_PATH.exists()
    cleveland_df = pd.read_csv(RAW_DATA_PATH)
    assert len(cleveland_df) == 303

    dev_indices_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    assert dev_indices_path.exists()
    with open(dev_indices_path) as f:
        dev_indices = json.load(f)
    assert len(dev_indices) == 242
    assert len(set(dev_indices)) == 242

    # The 61 locked test indices must have zero overlap with dev indices
    all_indices = set(range(303))
    test_indices = all_indices - set(dev_indices)
    assert len(test_indices) == 61
    assert set(dev_indices).isdisjoint(test_indices)


# ---------------------------------------------------------------------------
# 10. Profiling Report Artifact Generation Tests
# ---------------------------------------------------------------------------

def test_profiling_report_artifacts_exist():
    """Verify that markdown and JSON profiling reports exist and are non-empty."""
    md_report = BASE_DIR / "reports" / "external_data_profiling.md"
    json_report = BASE_DIR / "reports" / "external_data_profiling.json"

    assert md_report.exists()
    assert json_report.exists()

    md_text = md_report.read_text(encoding="utf-8")
    assert "CardioVanta Phase 17: External Dataset Profiling" in md_text
    assert "b8e4bbd06b9bf9ec831c992ba397639f22815e525c43b489e1a6e75b3be29a75" in md_text

    with open(json_report, encoding="utf-8") as f:
        json_data = json.load(f)
    assert "metadata" in json_data
    assert "profiles" in json_data
    assert len(json_data["profiles"]) == 2


# ---------------------------------------------------------------------------
# 11. Task 1.2: Raw Attribute Position and Index Tests
# ---------------------------------------------------------------------------

def test_raw_attribute_mapping_exact_indices():
    """Verify that all 14 clinical features map to the exact 1-based and 0-based positions."""
    expected_mapping = {
        "age": (3, 2),
        "sex": (4, 3),
        "cp": (9, 8),
        "trestbps": (10, 9),
        "chol": (12, 11),
        "fbs": (16, 15),
        "restecg": (19, 18),
        "thalach": (32, 31),
        "exang": (38, 37),
        "oldpeak": (40, 39),
        "slope": (41, 40),
        "ca": (44, 43),
        "thal": (51, 50),
        "num": (58, 57),
    }

    for feat, (one_idx, zero_idx) in expected_mapping.items():
        assert RAW_76_ATTRIBUTE_MAPPING[feat]["one_indexed"] == one_idx, f"Mismatch for {feat} 1-index"
        assert RAW_76_ATTRIBUTE_MAPPING[feat]["zero_indexed"] == zero_idx, f"Mismatch for {feat} 0-index"
        assert zero_idx == one_idx - 1, f"0-index is not 1-index minus 1 for {feat}"


def test_malformed_record_rejection(tmp_path):
    """Verify that malformed records (wrong token count or missing 'name' delimiter) are rejected."""
    bad_file = tmp_path / "bad.data"
    # Create 5 lines without 'name'
    bad_file.write_text("1 2 3 4 5\n6 7 8 9 10\n11 12 13 14 15\n")

    with pytest.raises(ValueError, match="Raw record parsing failed"):
        parse_raw_76_record_file(bad_file)


# ---------------------------------------------------------------------------
# 12. Task 1.2: External Cohort Parsers & Schemas
# ---------------------------------------------------------------------------

def test_parse_hungarian_cohort_schema_and_counts():
    """Verify Hungarian cohort parsing produces exactly N=294 with consistent schema and target."""
    parsed = parse_hungarian_cohort()

    assert parsed.cohort_name == "hungary"
    assert parsed.n_samples == 294
    assert len(parsed.data) == 294
    assert parsed.data["cohort"].unique().tolist() == ["hungary"]

    # Check 13 clinical features
    for col in CLINICAL_13_FEATURES:
        assert col in parsed.data.columns

    # Check outcome preservation
    assert "num" in parsed.data.columns
    assert "target" in parsed.data.columns
    assert set(parsed.data["num"].unique()).issubset({0, 1, 2, 3, 4})
    assert set(parsed.data["target"].unique()).issubset({0, 1})

    # Assert binary target derivation: target == (num > 0)
    expected_target = (parsed.data["num"] > 0).astype(int)
    assert (parsed.data["target"] == expected_target).all()

    # Predictor matrix isolation
    assert parsed.X_13.shape == (294, 13)
    assert parsed.X_10.shape == (294, 10)
    assert parsed.X_9.shape == (294, 9)
    assert "num" not in parsed.X_13.columns
    assert "target" not in parsed.X_13.columns
    assert "cohort" not in parsed.X_13.columns

    # Check sentinel normalization: -9 mapped to NaN
    assert parsed.data["chol"].isna().sum() == 23
    assert (parsed.data["chol"] == -9).sum() == 0


def test_parse_long_beach_cohort_schema_and_counts():
    """Verify Long Beach VA cohort parsing produces exactly N=200 with consistent schema and target."""
    parsed = parse_long_beach_cohort()

    assert parsed.cohort_name == "long_beach"
    assert parsed.n_samples == 200
    assert len(parsed.data) == 200
    assert parsed.data["cohort"].unique().tolist() == ["long_beach"]

    # Check 13 clinical features
    for col in CLINICAL_13_FEATURES:
        assert col in parsed.data.columns

    # Check outcome preservation
    assert "num" in parsed.data.columns
    assert "target" in parsed.data.columns
    assert set(parsed.data["num"].unique()).issubset({0, 1, 2, 3, 4})
    assert set(parsed.data["target"].unique()).issubset({0, 1})

    # Assert binary target derivation: target == (num > 0)
    expected_target = (parsed.data["num"] > 0).astype(int)
    assert (parsed.data["target"] == expected_target).all()

    # Predictor matrix isolation
    assert parsed.X_13.shape == (200, 13)
    assert parsed.X_10.shape == (200, 10)
    assert parsed.X_9.shape == (200, 9)
    assert "num" not in parsed.X_13.columns
    assert "target" not in parsed.X_13.columns
    assert "cohort" not in parsed.X_13.columns


def test_long_beach_va_anomalies_preserved_and_reported():
    """Assert observed anomalies in Long Beach VA are preserved in data and reported."""
    parsed = parse_long_beach_cohort()

    # Record 33 has trestbps = 0.0 (preserved, not dropped)
    assert parsed.data.loc[33, "trestbps"] == 0.0
    assert any("trestbps=0.0" in a for a in parsed.anomalies)

    # Record 5 has oldpeak = -0.5 (preserved, not dropped or forced >= 0)
    assert parsed.data.loc[5, "oldpeak"] == -0.5
    assert any("oldpeak=-0.5" in a for a in parsed.anomalies)

    # Record 100 has slope = 0.0 (preserved, not dropped)
    assert parsed.data.loc[100, "slope"] == 0.0
    assert any("slope=0.0" in a for a in parsed.anomalies)

    # 49 records have chol = 0.0 (preserved, not automatically converted to NaN)
    assert (parsed.data["chol"] == 0.0).sum() == 49
    assert any("chol=0.0" in a for a in parsed.anomalies)


# ---------------------------------------------------------------------------
# 13. Task 1.2: Cleveland Development Cohort & Locked Test Isolation
# ---------------------------------------------------------------------------

def test_parse_cleveland_dev_cohort_isolation():
    """Verify Cleveland Dev parsing extracts exactly N=242 development samples with zero locked test leakage."""
    parsed = parse_cleveland_dev_cohort()

    assert parsed.cohort_name == "cleveland"
    assert parsed.n_samples == 242
    assert len(parsed.data) == 242

    with open(BASE_DIR / "data" / "processed" / "dev_indices.json") as f:
        dev_indices = json.load(f)

    # Assert source_row_index exactly matches dev_indices
    assert list(parsed.data["source_row_index"]) == dev_indices

    # Assert zero overlap with the 61 locked test indices
    locked_test_indices = set(range(303)) - set(dev_indices)
    assert len(locked_test_indices) == 61
    assert set(parsed.data["source_row_index"]).isdisjoint(locked_test_indices)

    # Check schema consistency
    for col in CLINICAL_13_FEATURES:
        assert col in parsed.data.columns
    assert "num" in parsed.data.columns
    assert "target" in parsed.data.columns
    assert set(parsed.data["target"].unique()).issubset({0, 1})

    # Predictor matrix excludes target, num, cohort, source_row_index
    assert parsed.X_13.shape == (242, 13)
    assert parsed.X_10.shape == (242, 10)
    assert parsed.X_9.shape == (242, 9)
    assert "num" not in parsed.X_13.columns
    assert "target" not in parsed.X_13.columns
    assert "cohort" not in parsed.X_13.columns
    assert "source_row_index" not in parsed.X_13.columns


def test_load_all_multicenter_cohorts_complete_triangulation():
    """Verify multi-centre loader returns all 3 cohorts with exactly N=736 total patients and quarantined test set."""
    cohorts = load_all_multicenter_cohorts()

    assert set(cohorts.keys()) == {"hungary", "long_beach", "cleveland"}
    n_h = len(cohorts["hungary"].data)
    n_va = len(cohorts["long_beach"].data)
    n_cl = len(cohorts["cleveland"].data)

    assert n_h == 294
    assert n_va == 200
    assert n_cl == 242
    assert n_h + n_va + n_cl == 736

    # Verify locked test quarantine across all cohorts
    with open(BASE_DIR / "data" / "processed" / "dev_indices.json") as f:
        dev_idx = set(json.load(f))
    locked_test_idx = set(range(303)) - dev_idx

    assert set(cohorts["cleveland"].data["source_row_index"]).isdisjoint(locked_test_idx)


def test_predictor_matrix_never_includes_labels_or_identifiers():
    """Verify that predictor matrices across all three cohorts strictly exclude labels and identifiers."""
    cohorts = load_all_multicenter_cohorts()

    forbidden_cols = {"num", "target", "cohort", "source_row_index"}

    for name, cohort in cohorts.items():
        assert forbidden_cols.isdisjoint(set(cohort.X_13.columns)), f"{name} X_13 contains forbidden columns!"
        assert forbidden_cols.isdisjoint(set(cohort.X_10.columns)), f"{name} X_10 contains forbidden columns!"
        assert forbidden_cols.isdisjoint(set(cohort.X_9.columns)), f"{name} X_9 contains forbidden columns!"
        assert len(cohort.y) == cohort.n_samples, f"{name} y length mismatch"
        assert len(cohort.num) == cohort.n_samples, f"{name} num length mismatch"


def test_cleveland_target_semantic_alignment_with_canonical_uci():
    """Verify Cleveland Dev binary target is harmonized with canonical UCI num > 0 semantics (1=disease, 0=healthy)."""
    import zipfile
    parsed = parse_cleveland_dev_cohort()
    dev_df = parsed.data

    zip_path = BASE_DIR / "data" / "external" / "raw" / "heart+disease.zip"
    with zipfile.ZipFile(zip_path) as z:
        with z.open("processed.cleveland.data") as f:
            uci_df = pd.read_csv(f, header=None, names=[
                "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
                "exang", "oldpeak", "slope", "ca", "thal", "num"
            ], na_values="?")

    for _, row in dev_df.iterrows():
        match = uci_df[
            (uci_df["age"] == row["age"]) &
            (uci_df["sex"] == row["sex"]) &
            (uci_df["trestbps"] == row["trestbps"]) &
            (uci_df["chol"] == row["chol"]) &
            (uci_df["thalach"] == row["thalach"])
        ]
        assert len(match) == 1, f"Ambiguous or missing match for patient age={row['age']}, chol={row['chol']}"
        expected_target = int(match["num"].values[0] > 0)
        assert int(row["target"]) == expected_target, f"Target mismatch: got {row['target']}, expected {expected_target}"

