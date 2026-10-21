"""
CardioVanta Phase 17: Multicenter Validation Pipelines Test Suite (Task 2.1)
============================================================================
Focuses strictly on verifying the Missing-Aware 10-Clinical-Feature Pipeline:
1. Baseline pipeline exposes exactly 11 model inputs.
2. 'chol_is_missing' correctly distinguishes missing cholesterol from observed zero cholesterol.
3. Cholesterol imputation uses training-fold statistics, not held-out data.
4. Scaling is fitted on training data only.
5. Estimator uses L2-regularized Logistic Regression.
6. All missing predictors are handled without dropping rows.
7. Pipeline can fit and predict probabilities on a controlled fixture.
8. Targets and identifiers cannot enter the predictor matrix.
9. Cleveland locked test partition remains isolated.
10. Existing semantic chest-pain mapping is applied correctly where required.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone
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
from src.cardiovanta.data.validation import (
    KAGGLE_CP_TO_CANONICAL,
    adapt_cleveland_cp,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def controlled_fixture() -> tuple[pd.DataFrame, np.ndarray]:
    """Generates a small, controlled 10-feature fixture with controlled missingness."""
    rng = np.random.RandomState(42)
    n_samples = 30

    data = {
        "age": rng.randint(35, 75, n_samples).astype(float),
        "sex": rng.choice([0.0, 1.0], n_samples),
        "cp": rng.choice([1.0, 2.0, 3.0, 4.0], n_samples),
        "trestbps": rng.normal(130, 15, n_samples),
        "chol": rng.normal(240, 40, n_samples),
        "fbs": rng.choice([0.0, 1.0], n_samples),
        "restecg": rng.choice([0.0, 1.0, 2.0], n_samples),
        "thalach": rng.normal(150, 20, n_samples),
        "exang": rng.choice([0.0, 1.0], n_samples),
        "oldpeak": rng.choice([0.0, 0.5, 1.0, 2.0, 3.0], n_samples),
    }
    df = pd.DataFrame(data, columns=CANDIDATE_A_CLINICAL_10)

    # Inject specific controlled missing values
    df.loc[0, "chol"] = np.nan   # Missing cholesterol
    df.loc[1, "chol"] = 0.0      # Observed zero cholesterol
    df.loc[2, "trestbps"] = np.nan
    df.loc[3, "thalach"] = np.nan
    df.loc[4, "oldpeak"] = np.nan
    df.loc[5, "fbs"] = np.nan

    # Target
    y = rng.choice([0, 1], n_samples)
    return df, y


# ---------------------------------------------------------------------------
# Test 1: The baseline pipeline exposes exactly 11 model inputs
# ---------------------------------------------------------------------------

def test_baseline_pipeline_exposes_11_model_inputs(controlled_fixture):
    """Verify that the baseline pipeline takes 10 clinical features and exposes exactly 11 inputs."""
    X, y = controlled_fixture
    pipe = build_candidate_a_pipeline()

    # Fit pipeline
    pipe.fit(X, y)

    # Preprocessor (all steps prior to model)
    preprocessor = pipe[:-1]
    X_trans = preprocessor.transform(X)

    # Output dimensionality must be exactly 11
    assert X_trans.shape[1] == 11, f"Expected 11 transformed model inputs, got {X_trans.shape[1]}"
    assert X_trans.shape[0] == len(X)

    # Output feature names must match CANDIDATE_A_INPUTS_11
    names_out = list(preprocessor.get_feature_names_out())
    assert names_out == CANDIDATE_A_INPUTS_11, f"Feature names mismatch: {names_out}"
    assert "chol_is_missing" == names_out[-1]


def test_baseline_pipeline_real_cohort_11_inputs():
    """Verify 11-input transformation on real clinical cohort data."""
    multicenter = prepare_multicenter_research_data()
    cleve_X = multicenter["cleveland"]["X_10"]
    cleve_y = multicenter["cleveland"]["y"]

    pipe = build_candidate_a_pipeline()
    pipe.fit(cleve_X, cleve_y)

    for cohort_name in ["cleveland", "hungary", "long_beach"]:
        X_cohort = multicenter[cohort_name]["X_10"]
        X_trans = pipe[:-1].transform(X_cohort)
        assert X_trans.shape[1] == 11, f"{cohort_name} expected 11 features, got {X_trans.shape[1]}"
        assert X_trans.shape[0] == len(X_cohort)


# ---------------------------------------------------------------------------
# Test 2: 'chol_is_missing' distinguishes missing cholesterol from observed zero
# ---------------------------------------------------------------------------

def test_chol_is_missing_distinguishes_missing_from_observed_zero():
    """Verify chol_is_missing separates missing (NaN) from observed zero (0.0)."""
    # 3-patient synthetic test case
    # Patient 0: observed positive cholesterol (220.0)
    # Patient 1: missing cholesterol (NaN)
    # Patient 2: observed zero cholesterol (0.0)
    X = np.array([
        [50.0, 1.0, 4.0, 120.0, 220.0, 0.0, 0.0, 150.0, 0.0, 1.0],
        [60.0, 0.0, 2.0, 130.0, np.nan, 0.0, 0.0, 140.0, 1.0, 0.0],
        [55.0, 1.0, 3.0, 110.0, 0.0, 1.0, 1.0, 160.0, 0.0, 0.5],
    ])

    # Mode 1: treat_zero_as_missing=False (default: 0.0 is observed zero)
    trans_default = MissingAwareCholesterolTransformer(treat_zero_as_missing=False)
    out_default = trans_default.fit_transform(X)

    # chol_is_missing is column index 10
    assert out_default[0, 10] == 0.0, "Observed positive chol must have chol_is_missing = 0.0"
    assert out_default[1, 10] == 1.0, "Missing NaN chol must have chol_is_missing = 1.0"
    assert out_default[2, 10] == 0.0, "Observed zero chol must have chol_is_missing = 0.0 under default policy"

    # Row 1 (missing) must be imputed with positive median (220.0)
    assert out_default[1, 4] == 220.0
    # Row 2 (observed zero) must stay 0.0 under default policy
    assert out_default[2, 4] == 0.0

    # Mode 2: treat_zero_as_missing=True (both NaN and <= 0.0 treated as missing)
    trans_zero_as_missing = MissingAwareCholesterolTransformer(treat_zero_as_missing=True)
    out_zero_as_missing = trans_zero_as_missing.fit_transform(X)

    assert out_zero_as_missing[0, 10] == 0.0
    assert out_zero_as_missing[1, 10] == 1.0
    assert out_zero_as_missing[2, 10] == 1.0, "Observed zero chol must have chol_is_missing = 1.0 when treat_zero_as_missing=True"
    assert out_zero_as_missing[2, 4] == 220.0, "Zero chol must be imputed with median when treat_zero_as_missing=True"


# ---------------------------------------------------------------------------
# Test 3: Cholesterol imputation uses training-fold statistics, not held-out data
# ---------------------------------------------------------------------------

def test_cholesterol_imputation_training_fold_statistics_only():
    """Verify that cholesterol imputation is strictly fold-local and unaffected by held-out data."""
    # Training fold with median chol = 200.0
    X_train = pd.DataFrame({
        "age": [50.0, 52.0, 54.0],
        "sex": [1.0, 1.0, 1.0],
        "cp": [4.0, 4.0, 4.0],
        "trestbps": [120.0, 120.0, 120.0],
        "chol": [190.0, 200.0, 210.0],  # Median = 200.0
        "fbs": [0.0, 0.0, 0.0],
        "restecg": [0.0, 0.0, 0.0],
        "thalach": [150.0, 150.0, 150.0],
        "exang": [0.0, 0.0, 0.0],
        "oldpeak": [0.0, 0.0, 0.0],
    })

    # Held-out fold with missing chol and extreme values
    X_held_out_1 = pd.DataFrame({
        "age": [60.0, 62.0],
        "sex": [0.0, 0.0],
        "cp": [2.0, 2.0],
        "trestbps": [130.0, 130.0],
        "chol": [np.nan, 500.0],  # Extreme held-out value
        "fbs": [0.0, 0.0],
        "restecg": [0.0, 0.0],
        "thalach": [140.0, 140.0],
        "exang": [1.0, 1.0],
        "oldpeak": [1.0, 1.0],
    })

    X_held_out_2 = pd.DataFrame({
        "age": [60.0, 62.0],
        "sex": [0.0, 0.0],
        "cp": [2.0, 2.0],
        "trestbps": [130.0, 130.0],
        "chol": [np.nan, 900.0],  # Different extreme held-out value
        "fbs": [0.0, 0.0],
        "restecg": [0.0, 0.0],
        "thalach": [140.0, 140.0],
        "exang": [1.0, 1.0],
        "oldpeak": [1.0, 1.0],
    })

    trans = MissingAwareCholesterolTransformer()
    trans.fit(X_train)

    assert trans.median_chol_ == 200.0, f"Expected training median 200.0, got {trans.median_chol_}"

    # Transform both held-out sets: the missing chol must be imputed with exactly 200.0 in both
    out_1 = trans.transform(X_held_out_1)
    out_2 = trans.transform(X_held_out_2)

    assert out_1[0, 4] == 200.0, f"Held-out 1 missing chol should be 200.0, got {out_1[0, 4]}"
    assert out_2[0, 4] == 200.0, f"Held-out 2 missing chol should be 200.0, got {out_2[0, 4]}"
    assert out_1[0, 10] == 1.0
    assert out_2[0, 10] == 1.0


# ---------------------------------------------------------------------------
# Test 4: Scaling is fitted on training data only
# ---------------------------------------------------------------------------

def test_scaling_fitted_on_training_data_only():
    """Verify that StandardScaler parameters (mean_, scale_) reflect training data only."""
    rng = np.random.RandomState(123)
    n_train = 50
    n_test = 25

    # Training distribution: mean ~ 100
    X_train = pd.DataFrame(rng.normal(100.0, 10.0, (n_train, 10)), columns=CANDIDATE_A_CLINICAL_10)
    y_train = rng.randint(0, 2, n_train)

    # Test distribution: mean ~ 500 (completely different distribution)
    X_test = pd.DataFrame(rng.normal(500.0, 50.0, (n_test, 10)), columns=CANDIDATE_A_CLINICAL_10)

    pipe = build_candidate_a_pipeline()
    pipe.fit(X_train, y_train)

    scaler = pipe.named_steps["scaler"]

    # Scaler mean_ must have 11 features
    assert len(scaler.mean_) == 11

    # Scaler mean_ for the first 10 features should be near 100, NOT near 500
    for idx in range(10):
        assert 80.0 <= scaler.mean_[idx] <= 120.0, (
            f"Scaler feature {idx} mean is {scaler.mean_[idx]}, expected near 100.0"
        )

    # Transforming X_test must NOT change scaler.mean_
    _ = pipe.predict_proba(X_test)
    for idx in range(10):
        assert 80.0 <= scaler.mean_[idx] <= 120.0


# ---------------------------------------------------------------------------
# Test 5: Estimator uses L2-regularized Logistic Regression
# ---------------------------------------------------------------------------

def test_estimator_uses_l2_regularized_logistic_regression():
    """Verify that the model step uses L2-regularized LogisticRegression with lbfgs solver."""
    pipe = build_candidate_a_pipeline(C=1.0)
    model = pipe.named_steps["model"]

    assert isinstance(model, LogisticRegression), "Estimator must be an instance of LogisticRegression"
    # In scikit-learn, penalty is 'l2' (or 'deprecated' where l2 is the default)
    assert model.penalty in ("l2", "deprecated"), f"Penalty must be l2, got {model.penalty}"
    assert model.C == 1.0, f"Expected C=1.0, got {model.C}"
    assert model.solver == "lbfgs", f"Expected solver='lbfgs', got {model.solver}"
    assert model.max_iter >= 1000, f"Expected max_iter >= 1000, got {model.max_iter}"


# ---------------------------------------------------------------------------
# Test 6: All missing predictors are handled without dropping rows
# ---------------------------------------------------------------------------

def test_all_missing_predictors_handled_without_dropping_rows():
    """Verify that rows with missing values across multiple predictors are imputed, never dropped."""
    # Create fixture with NaNs in every column
    rows = [
        {"age": np.nan, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "chol": 200.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": np.nan, "cp": 4.0, "trestbps": 120.0, "chol": 200.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": np.nan, "trestbps": 120.0, "chol": 200.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": np.nan, "chol": 200.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "chol": np.nan, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "chol": 200.0, "fbs": np.nan, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "chol": 200.0, "fbs": 0.0, "restecg": np.nan, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "chol": 200.0, "fbs": 0.0, "restecg": 0.0, "thalach": np.nan, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "chol": 200.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": np.nan, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "chol": 200.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": np.nan},
        {"age": 60.0, "sex": 0.0, "cp": 2.0, "trestbps": np.nan, "chol": np.nan, "fbs": np.nan, "restecg": np.nan, "thalach": np.nan, "exang": np.nan, "oldpeak": np.nan},
    ]
    df = pd.DataFrame(rows, columns=CANDIDATE_A_CLINICAL_10)
    y = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0])

    pipe = build_candidate_a_pipeline()
    pipe.fit(df, y)

    X_trans = pipe[:-1].transform(df)
    assert X_trans.shape == (len(rows), 11), f"Expected ({len(rows)}, 11), got {X_trans.shape}"
    assert not np.isnan(X_trans).any(), "No NaNs may remain in transformed matrix"

    preds = pipe.predict(df)
    assert len(preds) == len(rows), f"Expected {len(rows)} predictions, got {len(preds)}"


def test_real_long_beach_va_missingness_processed_without_dropping():
    """Verify that Long Beach VA (N=200, severe missingness) is fully processed without dropping rows."""
    multicenter = prepare_multicenter_research_data()
    va_X = multicenter["long_beach"]["X_10"]
    cleve_X = multicenter["cleveland"]["X_10"]
    cleve_y = multicenter["cleveland"]["y"]

    pipe = build_candidate_a_pipeline()
    pipe.fit(cleve_X, cleve_y)

    va_trans = pipe[:-1].transform(va_X)
    assert va_trans.shape == (200, 11), f"Expected (200, 11), got {va_trans.shape}"
    assert not np.isnan(va_trans).any(), "Zero NaNs must reach estimator after fold-local imputation"

    va_probs = pipe.predict_proba(va_X)
    assert len(va_probs) == 200, f"Expected 200 predictions, got {len(va_probs)}"


# ---------------------------------------------------------------------------
# Test 7: Pipeline fits and predicts probabilities on a controlled fixture
# ---------------------------------------------------------------------------

def test_pipeline_fit_and_predict_probabilities_on_controlled_fixture(controlled_fixture):
    """Verify that pipeline fits and produces well-formed probabilities on controlled fixture."""
    X, y = controlled_fixture
    pipe = build_candidate_a_pipeline(random_state=42)

    pipe.fit(X, y)

    # Probabilities
    probs = pipe.predict_proba(X)
    assert probs.shape == (len(X), 2), f"Expected shape ({len(X)}, 2), got {probs.shape}"
    assert (probs >= 0.0).all() and (probs <= 1.0).all(), "Probabilities must be in [0, 1]"
    assert np.allclose(probs.sum(axis=1), 1.0), "Probabilities must sum to 1.0 per row"

    # Discrete predictions
    preds = pipe.predict(X)
    assert set(preds).issubset({0, 1}), "Predictions must be binary {0, 1}"
    assert len(preds) == len(X)


# ---------------------------------------------------------------------------
# Test 8: Targets and identifiers cannot enter the predictor matrix
# ---------------------------------------------------------------------------

def test_targets_and_identifiers_cannot_enter_predictor_matrix():
    """Verify that target ('target', 'num') and metadata columns are completely excluded."""
    # Create DataFrame containing clinical predictors + metadata + targets
    df = pd.DataFrame(np.random.randn(20, 10), columns=CANDIDATE_A_CLINICAL_10)
    df["target"] = np.random.choice([0, 1], 20)
    df["num"] = np.random.choice([0, 1, 2, 3, 4], 20)
    df["cohort"] = "cleveland"
    df["source_row_index"] = np.arange(20)
    df["cp_raw"] = np.random.choice([0, 1, 2, 3], 20)
    df["patient_id"] = [f"P_{i}" for i in range(20)]

    pipe = build_candidate_a_pipeline()
    pipe.fit(df, df["target"].to_numpy())

    preprocessor = pipe[:-1]
    X_trans = preprocessor.transform(df)

    # Dimensionality must be exactly 11 (10 clinical features + 1 chol_is_missing)
    assert X_trans.shape == (20, 11), f"Expected (20, 11), got {X_trans.shape}"

    # Feature names must contain zero metadata or target columns
    names_out = set(preprocessor.get_feature_names_out())
    forbidden = {"num", "target", "cohort", "source_row_index", "cp_raw", "patient_id"}
    assert forbidden.isdisjoint(names_out), f"Forbidden columns leaked into features: {forbidden & names_out}"

    # Rejection check: passing a 2D array with 14 features (e.g. accidentally including target) must error
    X_14 = np.random.randn(10, 14)
    with pytest.raises(ValueError, match="Expected 2D array with 10 features"):
        pipe.fit(X_14, np.random.randint(0, 2, 10))


# ---------------------------------------------------------------------------
# Test 9: The Cleveland locked test partition remains isolated
# ---------------------------------------------------------------------------

def test_cleveland_locked_test_partition_remains_isolated():
    """Assert zero overlap with the 61-sample locked Cleveland test partition."""
    # 1. Load authoritative dev indices
    assert DEV_INDICES_PATH.is_file(), f"Missing dev_indices.json at {DEV_INDICES_PATH}"
    with open(DEV_INDICES_PATH, "r", encoding="utf-8") as f:
        dev_indices = set(json.load(f))

    assert len(dev_indices) == 242, f"Expected 242 dev indices, got {len(dev_indices)}"
    locked_test_indices = set(range(303)) - dev_indices
    assert len(locked_test_indices) == 61, f"Expected 61 locked test indices, got {len(locked_test_indices)}"

    # 2. Load multicenter research cohorts
    multicenter = prepare_multicenter_research_data()
    cleve_data = multicenter["cleveland"]

    cleve_source_idx = set(cleve_data["source_row_index"])
    assert len(cleve_source_idx) == 242, f"Expected 242 Cleveland dev rows, got {len(cleve_source_idx)}"
    assert cleve_source_idx == dev_indices, "Cleveland cohort source indices do not match dev_indices.json"
    assert cleve_source_idx.isdisjoint(locked_test_indices), (
        "CRITICAL LEAKAGE DETECTED: Cleveland cohort contains samples from locked test partition!"
    )

    # 3. Total cohort counts
    assert multicenter["hungary"]["n_samples"] == 294
    assert multicenter["long_beach"]["n_samples"] == 200
    assert multicenter["cleveland"]["n_samples"] == 242


# ---------------------------------------------------------------------------
# Test 10: Existing semantic chest-pain mapping is applied correctly
# ---------------------------------------------------------------------------

def test_semantic_chest_pain_mapping_applied_correctly():
    """Verify that adapt_cleveland_cp correctly maps Kaggle 0-3 to Canonical UCI 1-4."""
    # Test Kaggle Cleveland data
    raw_kaggle_df = pd.DataFrame({
        "age": [50.0, 55.0, 60.0, 65.0],
        "sex": [1.0, 0.0, 1.0, 0.0],
        "cp": [0.0, 1.0, 2.0, 3.0],  # Kaggle values
    })

    adapted = adapt_cleveland_cp(raw_kaggle_df)

    # Verified correspondence:
    # 0 (Asymptomatic) -> 4
    # 1 (Atypical)     -> 2
    # 2 (Non-anginal)  -> 3
    # 3 (Typical)      -> 1
    assert adapted.loc[0, "cp"] == 4.0, "Kaggle 0 must map to UCI 4 (Asymptomatic)"
    assert adapted.loc[1, "cp"] == 2.0, "Kaggle 1 must map to UCI 2 (Atypical)"
    assert adapted.loc[2, "cp"] == 3.0, "Kaggle 2 must map to UCI 3 (Non-anginal)"
    assert adapted.loc[3, "cp"] == 1.0, "Kaggle 3 must map to UCI 1 (Typical)"

    # Original value preserved in cp_raw
    assert list(adapted["cp_raw"]) == [0.0, 1.0, 2.0, 3.0]

    # Prohibit naive cp + 1 (which would produce 1, 2, 3, 4 and invert typical vs asymptomatic)
    assert adapted.loc[0, "cp"] != 1.0, "Naive 'cp + 1' error detected on Kaggle 0"
    assert adapted.loc[3, "cp"] != 4.0, "Naive 'cp + 1' error detected on Kaggle 3"


# ---------------------------------------------------------------------------
# Test 11: Pipeline cloneability (Required for cross-validation)
# ---------------------------------------------------------------------------

def test_pipeline_cloneability():
    """Verify that build_candidate_a_pipeline produces a cloneable scikit-learn Pipeline."""
    pipe = build_candidate_a_pipeline()
    cloned_pipe = clone(pipe)

    assert cloned_pipe is not pipe
    assert len(cloned_pipe.steps) == len(pipe.steps)
    assert [name for name, _ in cloned_pipe.steps] == [name for name, _ in pipe.steps]


# ===========================================================================
# Candidate B (Non-Invasive 9-Clinical-Feature Pipeline) Test Suite (Task 2.2)
# ===========================================================================

@pytest.fixture
def controlled_fixture_b() -> tuple[pd.DataFrame, np.ndarray]:
    """Generates a small controlled 9-feature fixture for Candidate B."""
    rng = np.random.RandomState(42)
    n_samples = 30

    data = {
        "age": rng.randint(35, 75, n_samples).astype(float),
        "sex": rng.choice([0.0, 1.0], n_samples),
        "cp": rng.choice([1.0, 2.0, 3.0, 4.0], n_samples),
        "trestbps": rng.normal(130, 15, n_samples),
        "fbs": rng.choice([0.0, 1.0], n_samples),
        "restecg": rng.choice([0.0, 1.0, 2.0], n_samples),
        "thalach": rng.normal(150, 20, n_samples),
        "exang": rng.choice([0.0, 1.0], n_samples),
        "oldpeak": rng.choice([0.0, 0.5, 1.0, 2.0, 3.0], n_samples),
    }
    df = pd.DataFrame(data, columns=CANDIDATE_B_CLINICAL_9)

    # Inject controlled missing values (non-cholesterol)
    df.loc[0, "trestbps"] = np.nan
    df.loc[1, "thalach"] = np.nan
    df.loc[2, "oldpeak"] = np.nan
    df.loc[3, "fbs"] = np.nan
    df.loc[4, "restecg"] = np.nan
    df.loc[5, "exang"] = np.nan

    y = rng.choice([0, 1], n_samples)
    return df, y


def test_candidate_b_uses_exactly_9_specified_features_in_order(controlled_fixture_b):
    """Verify Candidate B uses exactly the 9 specified features in documented order."""
    expected_order = [
        "age", "sex", "cp", "trestbps", "fbs", "restecg", "thalach", "exang", "oldpeak"
    ]
    assert CANDIDATE_B_CLINICAL_9 == expected_order, f"CANDIDATE_B_CLINICAL_9 mismatch: {CANDIDATE_B_CLINICAL_9}"
    assert CANDIDATE_B_INPUTS_9 == expected_order, f"CANDIDATE_B_INPUTS_9 mismatch: {CANDIDATE_B_INPUTS_9}"

    X, y = controlled_fixture_b
    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(X, y)

    names_out = list(pipe_b[:-1].get_feature_names_out())
    assert names_out == expected_order, f"Output feature names mismatch: {names_out}"
    assert len(names_out) == 9


def test_candidate_b_cholesterol_and_indicator_completely_absent(controlled_fixture):
    """Verify 'chol' and 'chol_is_missing' are completely absent from Candidate B."""
    # Pass fixture that contains 'chol'
    X_with_chol, y = controlled_fixture
    assert "chol" in X_with_chol.columns

    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(X_with_chol, y)

    X_trans = pipe_b[:-1].transform(X_with_chol)
    names_out = list(pipe_b[:-1].get_feature_names_out())

    assert "chol" not in names_out, "'chol' must be excluded from Candidate B"
    assert "chol_is_missing" not in names_out, "'chol_is_missing' must be excluded from Candidate B"
    assert len(names_out) == 9
    assert X_trans.shape[1] == 9

    # Pipeline steps must not contain any cholesterol transformer
    step_names = [name for name, _ in pipe_b.steps]
    assert "chol_missing_aware" not in step_names, "Candidate B must not include chol_missing_aware step"


def test_candidate_b_fbs_retained(controlled_fixture_b):
    """Verify 'fbs' is explicitly retained as a clinical glycemic check in Candidate B."""
    assert "fbs" in CANDIDATE_B_CLINICAL_9
    # In Candidate B, fbs is index 4
    assert CANDIDATE_B_CLINICAL_9.index("fbs") == 4

    X, y = controlled_fixture_b
    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(X, y)

    names_out = list(pipe_b[:-1].get_feature_names_out())
    assert "fbs" in names_out
    assert names_out.index("fbs") == 4


def test_candidate_b_target_and_metadata_cannot_leak():
    """Verify target and metadata columns cannot leak into Candidate B model inputs."""
    df = pd.DataFrame(np.random.randn(20, 9), columns=CANDIDATE_B_CLINICAL_9)
    df["target"] = np.random.choice([0, 1], 20)
    df["num"] = np.random.choice([0, 1, 2, 3, 4], 20)
    df["cohort"] = "cleveland"
    df["source_row_index"] = np.arange(20)
    df["chol"] = np.random.normal(240, 40, 20)  # Extra chol column
    df["cp_raw"] = np.random.choice([0, 1, 2, 3], 20)
    df["patient_id"] = [f"P_{i}" for i in range(20)]

    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(df, df["target"].to_numpy())

    preprocessor = pipe_b[:-1]
    X_trans = preprocessor.transform(df)

    assert X_trans.shape == (20, 9), f"Expected (20, 9), got {X_trans.shape}"
    names_out = set(preprocessor.get_feature_names_out())
    forbidden = {"num", "target", "cohort", "source_row_index", "chol", "chol_is_missing", "cp_raw", "patient_id"}
    assert forbidden.isdisjoint(names_out), f"Forbidden columns leaked into Candidate B: {forbidden & names_out}"

    # Rejection of invalid 2D array shapes
    X_10 = np.random.randn(10, 10)
    with pytest.raises(ValueError, match="Expected 2D array with 9 features"):
        pipe_b.fit(X_10, np.random.randint(0, 2, 10))


def test_candidate_b_missing_predictors_imputed_training_fold_only():
    """Verify fold-local imputation in Candidate B uses training-fold statistics only."""
    # Training fold with known medians
    X_train = pd.DataFrame({
        "age": [50.0, 52.0, 54.0],
        "sex": [1.0, 1.0, 1.0],
        "cp": [4.0, 4.0, 4.0],
        "trestbps": [120.0, 124.0, 128.0],  # Median = 124.0
        "fbs": [0.0, 0.0, 0.0],
        "restecg": [0.0, 0.0, 0.0],
        "thalach": [140.0, 150.0, 160.0],   # Median = 150.0
        "exang": [0.0, 0.0, 0.0],
        "oldpeak": [0.0, 0.0, 0.0],
    })
    y_train = np.array([0, 1, 0])

    # Held-out fold with missing trestbps and extreme thalach
    X_held_out_1 = pd.DataFrame({
        "age": [60.0, 62.0],
        "sex": [0.0, 0.0],
        "cp": [2.0, 2.0],
        "trestbps": [np.nan, 200.0],  # Extreme held-out value
        "fbs": [0.0, 0.0],
        "restecg": [0.0, 0.0],
        "thalach": [np.nan, 220.0],
        "exang": [1.0, 1.0],
        "oldpeak": [1.0, 1.0],
    })

    X_held_out_2 = pd.DataFrame({
        "age": [60.0, 62.0],
        "sex": [0.0, 0.0],
        "cp": [2.0, 2.0],
        "trestbps": [np.nan, 250.0],  # Different extreme held-out value
        "fbs": [0.0, 0.0],
        "restecg": [0.0, 0.0],
        "thalach": [np.nan, 240.0],
        "exang": [1.0, 1.0],
        "oldpeak": [1.0, 1.0],
    })

    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(X_train, y_train)

    # Imputer step
    imputer = pipe_b.named_steps["clinical_imputer"]
    # trestbps is index 3, thalach is index 6
    assert imputer.medians_[3] == 124.0
    assert imputer.medians_[6] == 150.0

    # Transform both held-out sets: the missing trestbps must be imputed with exactly 124.0
    out_1 = imputer.transform(X_held_out_1)
    out_2 = imputer.transform(X_held_out_2)

    assert out_1[0, 3] == 124.0, f"Held-out 1 missing trestbps should be 124.0, got {out_1[0, 3]}"
    assert out_2[0, 3] == 124.0, f"Held-out 2 missing trestbps should be 124.0, got {out_2[0, 3]}"
    assert out_1[0, 6] == 150.0, f"Held-out 1 missing thalach should be 150.0, got {out_1[0, 6]}"
    assert out_2[0, 6] == 150.0, f"Held-out 2 missing thalach should be 150.0, got {out_2[0, 6]}"


def test_candidate_b_scaling_learned_from_training_data_only():
    """Verify that Candidate B StandardScaler parameters reflect training data only."""
    rng = np.random.RandomState(456)
    n_train = 50
    n_test = 25

    X_train = pd.DataFrame(rng.normal(100.0, 10.0, (n_train, 9)), columns=CANDIDATE_B_CLINICAL_9)
    y_train = rng.randint(0, 2, n_train)
    X_test = pd.DataFrame(rng.normal(500.0, 50.0, (n_test, 9)), columns=CANDIDATE_B_CLINICAL_9)

    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(X_train, y_train)

    scaler = pipe_b.named_steps["scaler"]
    assert len(scaler.mean_) == 9
    assert len(scaler.scale_) == 9

    for idx in range(9):
        assert 80.0 <= scaler.mean_[idx] <= 120.0, f"Scaler mean {idx} unexpected: {scaler.mean_[idx]}"

    _ = pipe_b.predict_proba(X_test)
    for idx in range(9):
        assert 80.0 <= scaler.mean_[idx] <= 120.0


def test_candidate_b_clone_fit_and_predict_probabilities(controlled_fixture_b):
    """Verify Candidate B supports sklearn cloning, fitting, and valid probability prediction."""
    X, y = controlled_fixture_b
    pipe_b = build_candidate_b_pipeline(random_state=42)

    # 1. Cloneability
    cloned = clone(pipe_b)
    assert cloned is not pipe_b
    assert len(cloned.steps) == len(pipe_b.steps)
    assert [name for name, _ in cloned.steps] == [name for name, _ in pipe_b.steps]

    # 2. Fit and Predict
    pipe_b.fit(X, y)
    probs = pipe_b.predict_proba(X)
    assert probs.shape == (len(X), 2), f"Expected shape ({len(X)}, 2), got {probs.shape}"
    assert (probs >= 0.0).all() and (probs <= 1.0).all()
    assert np.allclose(probs.sum(axis=1), 1.0)

    preds = pipe_b.predict(X)
    assert set(preds).issubset({0, 1})
    assert len(preds) == len(X)


def test_candidate_b_output_dimensionality_exactly_9():
    """Verify Candidate B produces exactly 9 model inputs across synthetic and real cohorts."""
    multicenter = prepare_multicenter_research_data()
    cleve_X_9 = multicenter["cleveland"]["X_9"]
    cleve_y = multicenter["cleveland"]["y"]

    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(cleve_X_9, cleve_y)

    for cohort_name in ["cleveland", "hungary", "long_beach"]:
        X_cohort = multicenter[cohort_name]["X_9"]
        X_trans = pipe_b[:-1].transform(X_cohort)
        assert X_trans.shape[1] == 9, f"{cohort_name} expected 9 features, got {X_trans.shape[1]}"
        assert X_trans.shape[0] == len(X_cohort)

    # Also test when passed 10-feature DataFrame with chol: it must still output 9
    for cohort_name in ["cleveland", "hungary", "long_beach"]:
        X_10 = multicenter[cohort_name]["X_10"]
        X_trans_from_10 = pipe_b[:-1].transform(X_10)
        assert X_trans_from_10.shape[1] == 9


def test_candidate_b_patient_rows_not_silently_dropped():
    """Verify that rows with missing values in Candidate B predictors are imputed, never dropped."""
    # Synthetic fixture with NaNs across all 9 features
    rows = [
        {"age": np.nan, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": np.nan, "cp": 4.0, "trestbps": 120.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": np.nan, "trestbps": 120.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": np.nan, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "fbs": np.nan, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "fbs": 0.0, "restecg": np.nan, "thalach": 150.0, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "fbs": 0.0, "restecg": 0.0, "thalach": np.nan, "exang": 0.0, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": np.nan, "oldpeak": 0.0},
        {"age": 50.0, "sex": 1.0, "cp": 4.0, "trestbps": 120.0, "fbs": 0.0, "restecg": 0.0, "thalach": 150.0, "exang": 0.0, "oldpeak": np.nan},
        {"age": 60.0, "sex": 0.0, "cp": 2.0, "trestbps": np.nan, "fbs": np.nan, "restecg": np.nan, "thalach": np.nan, "exang": np.nan, "oldpeak": np.nan},
    ]
    df = pd.DataFrame(rows, columns=CANDIDATE_B_CLINICAL_9)
    y = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])

    pipe_b = build_candidate_b_pipeline()
    pipe_b.fit(df, y)

    X_trans = pipe_b[:-1].transform(df)
    assert X_trans.shape == (len(rows), 9), f"Expected ({len(rows)}, 9), got {X_trans.shape}"
    assert not np.isnan(X_trans).any(), "Zero NaNs must reach estimator"

    preds = pipe_b.predict(df)
    assert len(preds) == len(rows)

    # Real Long Beach VA cohort (N=200, severe missingness)
    multicenter = prepare_multicenter_research_data()
    va_X_9 = multicenter["long_beach"]["X_9"]
    va_trans = pipe_b[:-1].transform(va_X_9)
    assert va_trans.shape == (200, 9)
    assert not np.isnan(va_trans).any()


def test_candidate_b_cleveland_locked_test_partition_isolated():
    """Verify Candidate B preserves strict quarantine of the 61 locked Cleveland test samples."""
    assert DEV_INDICES_PATH.is_file()
    with open(DEV_INDICES_PATH, "r", encoding="utf-8") as f:
        dev_indices = set(json.load(f))
    locked_test_indices = set(range(303)) - dev_indices

    multicenter = prepare_multicenter_research_data()
    cleve_data = multicenter["cleveland"]

    cleve_source_idx = set(cleve_data["source_row_index"])
    assert len(cleve_source_idx) == 242
    assert cleve_source_idx == dev_indices
    assert cleve_source_idx.isdisjoint(locked_test_indices), (
        "CRITICAL LEAKAGE DETECTED: Locked test samples present in Candidate B Cleveland cohort!"
    )
    assert cleve_data["X_9"].shape == (242, 9)

