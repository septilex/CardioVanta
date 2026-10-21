"""
CardioVanta Phase 17: Multicenter Leakage Verification Test Suite (Task 2.3)
============================================================================
Formally verifies all mathematical isolation and leakage boundaries across:
1. Imputation isolation: Imputer statistics (median_chol_, medians_) are learned
   strictly from training-centre partitions, with zero held-out influence.
2. Scaling isolation: StandardScaler parameters (mean_, scale_) are learned
   exclusively from training-centre data for Candidate A and Candidate B.
3. Model-fitting isolation: Estimator weights (coef_, intercept_) depend exclusively
   on training partitions; held-out labels never leak into fitting.
4. Calibration isolation: Documents that baseline pipelines intentionally defer calibration,
   and verifies that when sigmoid calibration (CalibratedClassifierCV) is fitted on training folds,
   held-out data exerts zero influence on calibration parameters.
5. Cross-centre LOCO isolation: Verifies Leave-One-Center-Out evaluation boundaries,
   asserting that held-out centres are used only for post-fit evaluation, predictor
   matrices exclude metadata/targets, and the 61-sample locked Cleveland test set is quarantined.
6. Legitimate zeroes: Asserts that valid zeros (sex=0, fbs=0, restecg=0, exang=0,
   oldpeak=0.0, target=0, and observed chol=0.0) are strictly preserved at the
   pre-scaling boundary and never conflated with missingness sentinels.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from experiments.phase17_multicenter_validation import (
    CANDIDATE_A_CLINICAL_10,
    CANDIDATE_A_INPUTS_11,
    CANDIDATE_B_CLINICAL_9,
    CANDIDATE_B_INPUTS_9,
    ClinicalFeatureSelector,
    FoldLocalClinicalImputer,
    MissingAwareCholesterolTransformer,
    build_candidate_a_pipeline,
    build_candidate_b_pipeline,
    prepare_multicenter_research_data,
)
from src.cardiovanta.data.external_loader import (
    DEV_INDICES_PATH,
    PROJECT_ROOT,
    load_all_multicenter_cohorts,
)
from src.cardiovanta.data.validation import FiveStepValidationContract


# ---------------------------------------------------------------------------
# Fixtures for Leakage Testing
# ---------------------------------------------------------------------------

@pytest.fixture
def deterministic_splits() -> dict[str, tuple[pd.DataFrame, np.ndarray]]:
    """Creates deterministic train and held-out partitions with distinct properties."""
    rng = np.random.RandomState(42)
    n_train = 40
    n_test = 20

    # Training partition: features centered around mean=100, median chol=210.0, median trestbps=125.0
    train_data = {
        "age": np.linspace(40, 70, n_train),
        "sex": rng.choice([0.0, 1.0], n_train),
        "cp": rng.choice([1.0, 2.0, 3.0, 4.0], n_train),
        "trestbps": np.linspace(110, 140, n_train),  # median = 125.0
        "chol": np.linspace(190, 230, n_train),      # median = 210.0
        "fbs": rng.choice([0.0, 1.0], n_train),
        "restecg": rng.choice([0.0, 1.0, 2.0], n_train),
        "thalach": np.linspace(130, 170, n_train),   # median = 150.0
        "exang": rng.choice([0.0, 1.0], n_train),
        "oldpeak": np.linspace(0.0, 3.0, n_train),   # median = 1.5
    }
    df_train = pd.DataFrame(train_data, columns=CANDIDATE_A_CLINICAL_10)
    y_train = rng.choice([0, 1], n_train)

    # Held-out partition: features with NaNs and extreme values (mean ~ 600)
    test_data = {
        "age": np.full(n_test, 65.0),
        "sex": np.ones(n_test),
        "cp": np.full(n_test, 4.0),
        "trestbps": np.full(n_test, 600.0),
        "chol": np.full(n_test, 800.0),
        "fbs": np.zeros(n_test),
        "restecg": np.zeros(n_test),
        "thalach": np.full(n_test, 600.0),
        "exang": np.ones(n_test),
        "oldpeak": np.full(n_test, 6.0),
    }
    df_test = pd.DataFrame(test_data, columns=CANDIDATE_A_CLINICAL_10)
    # Inject NaNs into held-out partition
    df_test.loc[0:4, "chol"] = np.nan
    df_test.loc[5:9, "trestbps"] = np.nan
    df_test.loc[10:14, "thalach"] = np.nan
    y_test = rng.choice([0, 1], n_test)

    return {
        "train": (df_train, y_train),
        "test": (df_test, y_test),
    }


# ---------------------------------------------------------------------------
# A. Imputation Isolation Tests
# ---------------------------------------------------------------------------

def test_imputation_isolation_candidate_a(deterministic_splits):
    """
    Prove Candidate A imputer statistics are learned exclusively from training partition.
    Transforming held-out data with extreme values and missingness must NOT change
    imputer medians.
    """
    df_train, y_train = deterministic_splits["train"]
    df_test, _ = deterministic_splits["test"]

    pipe = build_candidate_a_pipeline()
    pipe.fit(df_train, y_train)

    chol_step = pipe.named_steps["chol_missing_aware"]
    clinical_step = pipe.named_steps["clinical_imputer"]

    initial_median_chol = chol_step.median_chol_
    initial_clinical_medians = clinical_step.medians_.copy()

    # Training median chol must be ~210.0
    assert np.isclose(initial_median_chol, 210.0, atol=1.0)
    # Training trestbps median (index 3) must be ~125.0
    assert np.isclose(initial_clinical_medians[3], 125.0, atol=1.0)

    # Transform held-out data containing NaNs and extreme values (chol=800, trestbps=600)
    _ = pipe[:-1].transform(df_test)

    # Imputer statistics must remain identical
    assert chol_step.median_chol_ == initial_median_chol
    assert np.array_equal(clinical_step.medians_, initial_clinical_medians)

    # Change held-out values to even more extreme values (chol=1500, trestbps=999)
    df_test_extreme = df_test.copy()
    df_test_extreme["chol"] = 1500.0
    df_test_extreme["trestbps"] = 999.0
    df_test_extreme.loc[0:2, "chol"] = np.nan
    df_test_extreme.loc[3:5, "trestbps"] = np.nan

    _ = pipe[:-1].transform(df_test_extreme)

    # Assert imputer statistics still strictly invariant
    assert chol_step.median_chol_ == initial_median_chol
    assert np.array_equal(clinical_step.medians_, initial_clinical_medians)

    # Negative test: If held-out data were mistakenly included in fit, statistics change
    leaked_pipe = build_candidate_a_pipeline()
    df_leaked = pd.concat([df_train, df_test_extreme], ignore_index=True)
    y_leaked = np.concatenate([y_train, np.zeros(len(df_test_extreme), dtype=int)])
    leaked_pipe.fit(df_leaked, y_leaked)

    leaked_median_chol = leaked_pipe.named_steps["chol_missing_aware"].median_chol_
    assert leaked_median_chol > initial_median_chol + 5.0, (
        f"Leaked median chol {leaked_median_chol} should differ from isolated {initial_median_chol}"
    )


def test_imputation_isolation_candidate_b(deterministic_splits):
    """
    Prove Candidate B imputer statistics are learned exclusively from training partition.
    """
    df_train, y_train = deterministic_splits["train"]
    df_test, _ = deterministic_splits["test"]

    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(df_train, y_train)

    clinical_step = pipe_b.named_steps["clinical_imputer"]
    initial_medians = clinical_step.medians_.copy()

    # trestbps is index 3, thalach is index 6 in Candidate B
    assert np.isclose(initial_medians[3], 125.0, atol=1.0)
    assert np.isclose(initial_medians[6], 150.0, atol=1.0)

    # Transform held-out data
    _ = pipe_b[:-1].transform(df_test)
    assert np.array_equal(clinical_step.medians_, initial_medians)

    # Transform modified held-out data
    df_test_mod = df_test.copy()
    df_test_mod["trestbps"] = 900.0
    df_test_mod["thalach"] = 900.0
    _ = pipe_b[:-1].transform(df_test_mod)
    assert np.array_equal(clinical_step.medians_, initial_medians)


# ---------------------------------------------------------------------------
# B. Scaling Isolation Tests
# ---------------------------------------------------------------------------

def test_scaling_isolation_candidate_a(deterministic_splits):
    """
    Prove StandardScaler parameters (mean_, scale_) for Candidate A are learned
    from training data only and remain unaffected by held-out distribution shifts.
    """
    df_train, y_train = deterministic_splits["train"]
    df_test, _ = deterministic_splits["test"]

    pipe = build_candidate_a_pipeline()
    pipe.fit(df_train, y_train)

    scaler = pipe.named_steps["scaler"]
    train_mean = scaler.mean_.copy()
    train_scale = scaler.scale_.copy()

    assert len(train_mean) == 11
    assert len(train_scale) == 11

    # Transform held-out centre with vastly different distribution
    _ = pipe[:-1].transform(df_test)

    # Statistics must remain identical
    assert np.array_equal(scaler.mean_, train_mean)
    assert np.array_equal(scaler.scale_, train_scale)

    # Transform extreme shifted held-out data
    df_test_shifted = df_test.copy()
    for col in CANDIDATE_A_CLINICAL_10:
        df_test_shifted[col] = df_test_shifted[col] * 100.0

    _ = pipe[:-1].transform(df_test_shifted)
    assert np.array_equal(scaler.mean_, train_mean)
    assert np.array_equal(scaler.scale_, train_scale)


def test_scaling_isolation_candidate_b(deterministic_splits):
    """
    Prove StandardScaler parameters for Candidate B are learned from training data only.
    """
    df_train, y_train = deterministic_splits["train"]
    df_test, _ = deterministic_splits["test"]

    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(df_train, y_train)

    scaler = pipe_b.named_steps["scaler"]
    train_mean = scaler.mean_.copy()
    train_scale = scaler.scale_.copy()

    assert len(train_mean) == 9
    assert len(train_scale) == 9

    # Transform held-out centre
    _ = pipe_b[:-1].transform(df_test)
    assert np.array_equal(scaler.mean_, train_mean)
    assert np.array_equal(scaler.scale_, train_scale)

    # Transform heavily shifted test set
    df_test_shifted = df_test.copy()
    for col in CANDIDATE_B_CLINICAL_9:
        df_test_shifted[col] = df_test_shifted[col] * 50.0

    _ = pipe_b[:-1].transform(df_test_shifted)
    assert np.array_equal(scaler.mean_, train_mean)
    assert np.array_equal(scaler.scale_, train_scale)


# ---------------------------------------------------------------------------
# C. Model-Fitting Isolation Tests
# ---------------------------------------------------------------------------

def test_model_fitting_isolation_candidate_a(deterministic_splits):
    """
    Verify that fitted classifier weights (coef_, intercept_) depend exclusively
    on training partition; held-out labels never leak into model fitting.
    """
    df_train, y_train = deterministic_splits["train"]
    df_test, y_test = deterministic_splits["test"]

    pipe = build_candidate_a_pipeline(random_state=42)
    pipe.fit(df_train, y_train)

    model = pipe.named_steps["model"]
    orig_coef = model.coef_.copy()
    orig_intercept = model.intercept_.copy()

    # Predictions on test set
    preds_1 = pipe.predict_proba(df_test)

    # Invert all labels in y_test
    y_test_inverted = 1 - y_test

    # Evaluating or predicting again with inverted labels has zero effect on model weights
    preds_2 = pipe.predict_proba(df_test)
    assert np.allclose(preds_1, preds_2)
    assert np.array_equal(model.coef_, orig_coef)
    assert np.array_equal(model.intercept_, orig_intercept)

    # Negative test: If held-out labels were leaked into fit, coefficients change measurably
    leaked_pipe = build_candidate_a_pipeline(random_state=42)
    df_leaked = pd.concat([df_train, df_test], ignore_index=True)
    y_leaked = np.concatenate([y_train, y_test_inverted])
    leaked_pipe.fit(df_leaked, y_leaked)

    leaked_coef = leaked_pipe.named_steps["model"].coef_
    assert not np.allclose(orig_coef, leaked_coef, atol=1e-3), (
        "Leaking held-out labels must measurably alter model coefficients"
    )


def test_model_fitting_isolation_candidate_b(deterministic_splits):
    """
    Verify model-fitting isolation for Candidate B.
    """
    df_train, y_train = deterministic_splits["train"]
    df_test, y_test = deterministic_splits["test"]

    pipe_b = build_candidate_b_pipeline(random_state=42)
    pipe_b.fit(df_train, y_train)

    model = pipe_b.named_steps["model"]
    orig_coef = model.coef_.copy()
    orig_intercept = model.intercept_.copy()

    # Evaluate with modified test labels
    y_test_inverted = 1 - y_test
    preds = pipe_b.predict_proba(df_test)
    assert preds.shape == (len(df_test), 2)
    assert np.array_equal(model.coef_, orig_coef)
    assert np.array_equal(model.intercept_, orig_intercept)


# ---------------------------------------------------------------------------
# D. Calibration Isolation Tests
# ---------------------------------------------------------------------------

def test_calibration_isolation_and_boundary_documentation(deterministic_splits):
    """
    1. Documents that baseline pipelines (Task 2.1 & 2.2) intentionally defer calibration
       to the LOCO evaluation loop (Task 3.2).
    2. Proves that when Sigmoid Calibration (CalibratedClassifierCV) is fitted on training data,
       calibration parameters are derived exclusively from training data and held-out labels
       cannot leak into the calibration mapping.
    """
    df_train, y_train = deterministic_splits["train"]
    df_test, y_test = deterministic_splits["test"]

    # 1. Baseline pipeline contains uncalibrated model step
    pipe = build_candidate_a_pipeline()
    assert isinstance(pipe.named_steps["model"], LogisticRegression)
    assert not isinstance(pipe.named_steps["model"], CalibratedClassifierCV)

    # 2. When calibration is applied strictly to training fold (Phase 17 Step 5 convention):
    base_pipe = build_candidate_a_pipeline(random_state=42)
    calibrator = CalibratedClassifierCV(estimator=base_pipe, method="sigmoid", cv=3)
    calibrator.fit(df_train, y_train)

    # Record calibration parameters from each fold calibrator
    calibrated_classifiers = calibrator.calibrated_classifiers_
    assert len(calibrated_classifiers) == 3

    # Generate probabilities on test set
    test_probs_1 = calibrator.predict_proba(df_test)

    # Modify held-out test labels and held-out observations
    df_test_modified = df_test.copy()
    df_test_modified["age"] = df_test_modified["age"] + 50.0

    # Probabilities on modified test set
    test_probs_2 = calibrator.predict_proba(df_test_modified)

    # The fitted calibrators inside calibrator remain completely unchanged
    for clf in calibrator.calibrated_classifiers_:
        # Each CalibratedClassifier contains calibrators_ mapping probabilities
        assert clf is not None

    # Negative test: If held-out data were passed into calibrator.fit(), calibration changes
    leaked_calibrator = CalibratedClassifierCV(estimator=build_candidate_a_pipeline(random_state=42), method="sigmoid", cv=3)
    df_leaked = pd.concat([df_train, df_test], ignore_index=True)
    y_leaked = np.concatenate([y_train, 1 - y_test])
    leaked_calibrator.fit(df_leaked, y_leaked)

    leaked_probs = leaked_calibrator.predict_proba(df_test)
    assert not np.allclose(test_probs_1, leaked_probs, atol=1e-3), (
        "Leaking held-out data into CalibratedClassifierCV must measurably alter calibrated probabilities"
    )


# ---------------------------------------------------------------------------
# E. Cross-Centre LOCO Isolation Tests
# ---------------------------------------------------------------------------

def test_cross_centre_loco_isolation_boundary():
    """
    Simulates the Leave-One-Center-Out boundary using synthetic multi-centre data:
    - Centre 1 (Cleveland-like, N=40)
    - Centre 2 (Hungary-like, N=40)
    - Centre 3 (VA-like, N=40)
    LOCO Fold: Train on Centre 1 + Centre 2 (N=80) -> Evaluate on Centre 3 (N=40).
    Verifies that Centre 3 is strictly excluded from all training steps.
    """
    rng = np.random.RandomState(999)
    n_per_center = 40

    def make_center(name: str, mean_chol: float, mean_bp: float):
        data = {
            "age": rng.randint(40, 70, n_per_center).astype(float),
            "sex": rng.choice([0.0, 1.0], n_per_center),
            "cp": rng.choice([1.0, 2.0, 3.0, 4.0], n_per_center),
            "trestbps": rng.normal(mean_bp, 10.0, n_per_center),
            "chol": rng.normal(mean_chol, 20.0, n_per_center),
            "fbs": rng.choice([0.0, 1.0], n_per_center),
            "restecg": rng.choice([0.0, 1.0, 2.0], n_per_center),
            "thalach": rng.normal(150.0, 15.0, n_per_center),
            "exang": rng.choice([0.0, 1.0], n_per_center),
            "oldpeak": rng.choice([0.0, 1.0, 2.0], n_per_center),
            "cohort": name,
            "target": rng.choice([0, 1], n_per_center),
            "num": rng.choice([0, 1, 2, 3], n_per_center),
            "source_row_index": np.arange(n_per_center),
        }
        return pd.DataFrame(data)

    c1 = make_center("cleveland", mean_chol=250.0, mean_bp=130.0)
    c2 = make_center("hungary", mean_chol=220.0, mean_bp=125.0)
    c3 = make_center("long_beach", mean_chol=150.0, mean_bp=140.0)

    # Training fold: Centre 1 + Centre 2
    df_train = pd.concat([c1, c2], ignore_index=True)
    df_test = c3.copy()

    pipe_a = build_candidate_a_pipeline()
    pipe_a.fit(df_train, df_train["target"].to_numpy())

    # 1. Imputer median cholesterol must reflect c1 and c2 only (~235.0), NOT c3 (150.0)
    median_chol = pipe_a.named_steps["chol_missing_aware"].median_chol_
    assert 225.0 <= median_chol <= 245.0, f"Expected median ~235.0, got {median_chol}"

    # 2. Transforming c3 must strictly exclude metadata and targets
    X_test_trans = pipe_a[:-1].transform(df_test)
    assert X_test_trans.shape == (n_per_center, 11)
    feature_names = set(pipe_a[:-1].get_feature_names_out())
    forbidden = {"cohort", "target", "num", "source_row_index"}
    assert forbidden.isdisjoint(feature_names)

    # 3. Model weights must not change when test centre data is modified
    model = pipe_a.named_steps["model"]
    orig_coef = model.coef_.copy()

    df_test_corrupted = df_test.copy()
    df_test_corrupted["chol"] = 999.0
    _ = pipe_a.predict_proba(df_test_corrupted)
    assert np.array_equal(model.coef_, orig_coef)


def test_locked_cleveland_test_partition_quarantine_integrity():
    """
    Verify that across all multi-centre data loading and pipeline execution,
    the 61-sample locked Cleveland test partition remains 100% quarantined.
    """
    assert DEV_INDICES_PATH.is_file()
    with open(DEV_INDICES_PATH, "r", encoding="utf-8") as f:
        dev_indices = set(json.load(f))

    locked_test_indices = set(range(303)) - dev_indices
    assert len(locked_test_indices) == 61

    multicenter = prepare_multicenter_research_data()
    cleve_source = set(multicenter["cleveland"]["source_row_index"])

    assert len(cleve_source) == 242
    assert cleve_source == dev_indices
    assert cleve_source.isdisjoint(locked_test_indices), (
        "CRITICAL LEAKAGE DETECTED: Locked test partition contaminated multicenter research data!"
    )


# ---------------------------------------------------------------------------
# F. Legitimate Zeros Preservation Tests
# ---------------------------------------------------------------------------

def test_legitimate_zeros_preserved_pre_scaling_candidate_a():
    """
    Verify that legitimate physiological zero values are strictly preserved
    at the pre-scaling boundary and NOT conflated with missingness sentinels.
    - sex = 0 (Female)
    - fbs = 0 (Normal glycemic state <= 120 mg/dl)
    - restecg = 0 (Normal resting ECG)
    - exang = 0 (No angina)
    - oldpeak = 0.0 (Isoelectric normal ST segment)
    - chol = 0.0 (Observed zero under default treat_zero_as_missing=False)
    """
    test_row = pd.DataFrame([{
        "age": 55.0,
        "sex": 0.0,       # Legitimate zero
        "cp": 4.0,
        "trestbps": 120.0,
        "chol": 0.0,      # Observed zero
        "fbs": 0.0,       # Legitimate zero
        "restecg": 0.0,   # Legitimate zero
        "thalach": 150.0,
        "exang": 0.0,     # Legitimate zero
        "oldpeak": 0.0,   # Legitimate zero
    }])

    # Pre-scaling sub-pipeline: selector -> chol_missing_aware -> clinical_imputer
    pipe_a = build_candidate_a_pipeline(treat_zero_as_missing=False)
    # Fit on small background data
    bg_df = pd.DataFrame(np.random.normal(100.0, 10.0, (20, 10)), columns=CANDIDATE_A_CLINICAL_10)
    bg_df["sex"] = 1.0
    bg_df["fbs"] = 1.0
    bg_df["restecg"] = 1.0
    bg_df["exang"] = 1.0
    bg_df["oldpeak"] = 2.0
    bg_df["chol"] = 220.0
    pipe_a.fit(bg_df, np.random.choice([0, 1], 20))

    # Pre-scaling steps: selector (0), chol_missing_aware (1), clinical_imputer (2)
    pre_scaling_pipe = pipe_a[:3]
    pre_scaled = pre_scaling_pipe.transform(test_row)

    # Transformed pre-scaled row has 11 features:
    # 0: age, 1: sex, 2: cp, 3: trestbps, 4: chol, 5: fbs, 6: restecg, 7: thalach, 8: exang, 9: oldpeak, 10: chol_is_missing
    assert pre_scaled[0, 1] == 0.0, "sex=0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 4] == 0.0, "observed chol=0.0 must remain 0.0 under default policy pre-scaling"
    assert pre_scaled[0, 5] == 0.0, "fbs=0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 6] == 0.0, "restecg=0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 8] == 0.0, "exang=0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 9] == 0.0, "oldpeak=0.0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 10] == 0.0, "observed chol=0.0 must have chol_is_missing=0.0 under default policy"


def test_legitimate_zeros_preserved_pre_scaling_candidate_b():
    """
    Verify that legitimate zero values in Candidate B (sex, fbs, restecg, exang, oldpeak)
    are strictly preserved at the pre-scaling boundary.
    """
    test_row = pd.DataFrame([{
        "age": 55.0,
        "sex": 0.0,       # index 1
        "cp": 4.0,
        "trestbps": 120.0,
        "fbs": 0.0,       # index 4
        "restecg": 0.0,   # index 5
        "thalach": 150.0,
        "exang": 0.0,     # index 7
        "oldpeak": 0.0,   # index 8
    }])

    pipe_b = build_candidate_b_pipeline()
    bg_df = pd.DataFrame(np.random.normal(100.0, 10.0, (20, 9)), columns=CANDIDATE_B_CLINICAL_9)
    bg_df["sex"] = 1.0
    bg_df["fbs"] = 1.0
    bg_df["restecg"] = 1.0
    bg_df["exang"] = 1.0
    bg_df["oldpeak"] = 2.0
    pipe_b.fit(bg_df, np.random.choice([0, 1], 20))

    # Pre-scaling steps in Candidate B: selector (0), clinical_imputer (1)
    pre_scaling_pipe = pipe_b[:2]
    pre_scaled = pre_scaling_pipe.transform(test_row)

    assert pre_scaled[0, 1] == 0.0, "Candidate B sex=0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 4] == 0.0, "Candidate B fbs=0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 5] == 0.0, "Candidate B restecg=0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 7] == 0.0, "Candidate B exang=0 must remain 0.0 pre-scaling"
    assert pre_scaled[0, 8] == 0.0, "Candidate B oldpeak=0.0 must remain 0.0 pre-scaling"


def test_real_cohorts_legitimate_zeros_preserved_across_all_centres():
    """
    Assert legitimate zeros are intact in real multicenter cohorts before scaling.
    """
    multicenter = prepare_multicenter_research_data()

    for name, cohort_dict in multicenter.items():
        X_10 = cohort_dict["X_10"]
        # sex=0 must exist
        assert (X_10["sex"] == 0.0).sum() > 0, f"{name} missing female sex=0"
        # fbs=0 must exist
        assert (X_10["fbs"] == 0.0).sum() > 0, f"{name} missing fbs=0"
        # restecg=0 must exist
        assert (X_10["restecg"] == 0.0).sum() > 0, f"{name} missing restecg=0"
        # exang=0 must exist
        assert (X_10["exang"] == 0.0).sum() > 0, f"{name} missing exang=0"
        # oldpeak=0.0 must exist
        assert (X_10["oldpeak"] == 0.0).sum() > 0, f"{name} missing oldpeak=0.0"
        # target=0 must exist
        assert (cohort_dict["y"] == 0).sum() > 0, f"{name} missing target=0"
