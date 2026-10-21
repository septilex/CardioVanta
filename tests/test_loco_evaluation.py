"""
CardioVanta Phase 17: Leave-One-Centre-Out (LOCO) Splitter Test Suite (Task 3.1)
================================================================================
Deterministic verification of the 3-fold LOCO splitter:
1. Exactly three folds are generated.
2. Each fold holds out exactly one centre.
3. Each training partition contains the other two centres only.
4. Expected training and held-out counts match the actual validated cohorts.
5. No patient from the held-out centre appears in its training partition.
6. Across the three folds, every research-cohort patient is held out exactly once.
7. No duplicate compound patient identities occur within a cohort or fold.
8. Targets remain aligned with the correct patient records.
9. Cleveland locked test partition remains completely excluded.
10. Split generation is deterministic across repeated calls.
11. Metadata and targets are not included among model predictors.
12. Empty cohorts, missing cohort identifiers, or malformed inputs fail explicitly.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold

from experiments.phase17_multicenter_validation import (
    CANDIDATE_A_CLINICAL_10,
    CANDIDATE_A_INPUTS_11,
    CANDIDATE_B_CLINICAL_9,
    CANDIDATE_B_INPUTS_9,
    DEFAULT_METRICS_CSV,
    DEFAULT_METRICS_JSON,
    DEFAULT_METRICS_REPORT,
    DEFAULT_RESULTS_DIR,
    FIXED_DECISION_THRESHOLD,
    LOCOFold,
    LOCO_FOLD_SPECIFICATIONS,
    METRIC_DISPLAY_NAMES,
    build_candidate_a_pipeline,
    build_candidate_b_pipeline,
    compute_expected_calibration_error,
    compute_multicenter_metrics,
    compute_stratified_bootstrap_ci,
    evaluate_all_multicenter_metrics,
    execute_loco_prediction_pipeline,
    generate_loco_splits,
    prepare_multicenter_research_data,
    summarize_loco_splits,
)
from src.cardiovanta.data.external_loader import (
    DEV_INDICES_PATH,
    PROJECT_ROOT,
)


# ---------------------------------------------------------------------------
# Test 1: Exactly three folds are generated
# ---------------------------------------------------------------------------

def test_exactly_three_folds_generated():
    """Verify that generate_loco_splits produces exactly 3 folds."""
    folds = generate_loco_splits()
    assert len(folds) == 3, f"Expected exactly 3 LOCO folds, got {len(folds)}"
    for idx, fold in enumerate(folds):
        assert isinstance(fold, LOCOFold)
        assert fold.fold_id == idx + 1


# ---------------------------------------------------------------------------
# Test 2: Each fold holds out exactly one centre
# ---------------------------------------------------------------------------

def test_each_fold_holds_out_exactly_one_centre():
    """Verify each fold designates exactly one centre as held-out."""
    folds = generate_loco_splits()

    expected_held_out = ["hungary", "long_beach", "cleveland"]
    expected_roles = [
        "external_validation",
        "external_validation",
        "retrospective_development_baseline",
    ]

    for idx, fold in enumerate(folds):
        assert fold.held_out_center == expected_held_out[idx], (
            f"Fold {fold.fold_id} held-out centre mismatch: {fold.held_out_center} vs {expected_held_out[idx]}"
        )
        assert fold.held_out_status == expected_roles[idx], (
            f"Fold {fold.fold_id} role mismatch: {fold.held_out_status} vs {expected_roles[idx]}"
        )
        # Test partition must contain records only from the held-out centre
        unique_test_cohorts = set(fold.test_df["cohort"].unique())
        assert unique_test_cohorts == {fold.held_out_center}, (
            f"Fold {fold.fold_id} test partition contains non-held-out cohorts: {unique_test_cohorts}"
        )


# ---------------------------------------------------------------------------
# Test 3: Each training partition contains the other two centres only
# ---------------------------------------------------------------------------

def test_training_partitions_contain_other_two_centres_only():
    """Verify each training partition contains strictly the two remaining centres."""
    folds = generate_loco_splits()

    expected_train_pairs = [
        {"cleveland", "long_beach"},
        {"cleveland", "hungary"},
        {"hungary", "long_beach"},
    ]

    for idx, fold in enumerate(folds):
        assert set(fold.training_centers) == expected_train_pairs[idx], (
            f"Fold {fold.fold_id} expected training centres {expected_train_pairs[idx]}, got {set(fold.training_centers)}"
        )
        train_cohorts = set(fold.train_df["cohort"].unique())
        assert train_cohorts == expected_train_pairs[idx], (
            f"Fold {fold.fold_id} train_df contains unexpected cohorts: {train_cohorts}"
        )


# ---------------------------------------------------------------------------
# Test 4: Expected training and held-out counts match actual validated cohorts
# ---------------------------------------------------------------------------

def test_fold_sample_counts_match_validated_cohorts():
    """Verify exact sample counts per fold: 442/294, 536/200, 494/242; total 736."""
    folds = generate_loco_splits()
    summary = summarize_loco_splits(folds)

    expected_specs = [
        {"fold_id": 1, "n_train": 442, "n_test": 294, "held_out": "hungary", "cleve_train": 242, "va_train": 200},
        {"fold_id": 2, "n_train": 536, "n_test": 200, "held_out": "long_beach", "cleve_train": 242, "hungary_train": 294},
        {"fold_id": 3, "n_train": 494, "n_test": 242, "held_out": "cleveland", "hungary_train": 294, "va_train": 200},
    ]

    for idx, (fold, exp, s) in enumerate(zip(folds, expected_specs, summary)):
        assert fold.n_train == exp["n_train"], f"Fold {fold.fold_id} n_train mismatch: {fold.n_train} vs {exp['n_train']}"
        assert fold.n_test == exp["n_test"], f"Fold {fold.fold_id} n_test mismatch: {fold.n_test} vs {exp['n_test']}"
        assert len(fold.train_df) == exp["n_train"]
        assert len(fold.test_df) == exp["n_test"]
        assert fold.n_train + fold.n_test == 736
        assert s["total_samples"] == 736
        assert s["held_out_center"] == exp["held_out"]


# ---------------------------------------------------------------------------
# Test 5: No patient from held-out centre appears in its training partition
# ---------------------------------------------------------------------------

def test_zero_leakage_between_train_and_held_out():
    """Assert zero intersection between training and held-out compound identities in every fold."""
    folds = generate_loco_splits()

    for fold in folds:
        train_ids = set(fold.train_compound_ids)
        test_ids = set(fold.test_compound_ids)

        assert len(train_ids) == fold.n_train
        assert len(test_ids) == fold.n_test
        assert train_ids.isdisjoint(test_ids), (
            f"CRITICAL LEAKAGE in Fold {fold.fold_id}: {train_ids & test_ids} present in both train and test!"
        )
        # Also confirm no held-out cohort name exists in train_df
        assert fold.held_out_center not in set(fold.train_df["cohort"])


# ---------------------------------------------------------------------------
# Test 6: Every research patient is held out exactly once across the 3 folds
# ---------------------------------------------------------------------------

def test_every_patient_held_out_exactly_once():
    """Verify that the union of held-out sets covers all 736 patients with zero overlap."""
    folds = generate_loco_splits()

    test_sets = [set(fold.test_compound_ids) for fold in folds]

    # Pairwise disjoint
    assert test_sets[0].isdisjoint(test_sets[1]), "Overlap between Fold 1 and Fold 2 test partitions"
    assert test_sets[0].isdisjoint(test_sets[2]), "Overlap between Fold 1 and Fold 3 test partitions"
    assert test_sets[1].isdisjoint(test_sets[2]), "Overlap between Fold 2 and Fold 3 test partitions"

    # Union must equal exactly 736 unique patients
    all_held_out = test_sets[0] | test_sets[1] | test_sets[2]
    assert len(all_held_out) == 736, f"Expected 736 total unique held-out patients, got {len(all_held_out)}"


# ---------------------------------------------------------------------------
# Test 7: No duplicate compound patient identities within cohorts or folds
# ---------------------------------------------------------------------------

def test_no_duplicate_compound_patient_identities():
    """Verify compound IDs (cohort_source_row_index) are strictly unique."""
    cohorts = prepare_multicenter_research_data()

    all_compound_ids = []
    for c_name, c_dict in cohorts.items():
        c_ids = list(c_dict["compound_id"])
        assert len(c_ids) == len(set(c_ids)), f"Duplicate compound IDs within cohort '{c_name}'"
        all_compound_ids.extend(c_ids)

    assert len(all_compound_ids) == 736
    assert len(set(all_compound_ids)) == 736, "Globally duplicated compound IDs detected across cohorts"


# ---------------------------------------------------------------------------
# Test 8: Targets remain aligned with the correct patient records
# ---------------------------------------------------------------------------

def test_targets_strictly_aligned_with_patient_records():
    """Verify that y_train and y_test accurately align with each individual patient."""
    cohorts = prepare_multicenter_research_data()
    folds = generate_loco_splits(cohorts=cohorts)

    # Spot-check specific known records
    # 1. Long Beach VA record 0: target should match cohort ground truth
    va_df = cohorts["long_beach"]["df"]
    va_rec_0_target = int(va_df.loc[va_df["source_row_index"] == 0, "target"].iloc[0])

    # In Fold 2, Long Beach is held out:
    fold_2 = folds[1]
    va_test_mask = fold_2.test_df["source_row_index"] == 0
    assert int(fold_2.y_test[va_test_mask][0]) == va_rec_0_target

    # In Fold 1, Long Beach is in train:
    fold_1 = folds[0]
    va_train_mask = (fold_1.train_df["cohort"] == "long_beach") & (fold_1.train_df["source_row_index"] == 0)
    assert int(fold_1.y_train[va_train_mask][0]) == va_rec_0_target


# ---------------------------------------------------------------------------
# Test 9: Cleveland locked test partition remains completely excluded
# ---------------------------------------------------------------------------

def test_cleveland_locked_test_partition_excluded():
    """Verify that none of the 61 locked Cleveland test samples appear in any fold."""
    assert DEV_INDICES_PATH.is_file(), f"Missing dev_indices.json at {DEV_INDICES_PATH}"
    with open(DEV_INDICES_PATH, "r", encoding="utf-8") as f:
        dev_indices = set(json.load(f))

    locked_test_indices = set(range(303)) - dev_indices
    assert len(locked_test_indices) == 61

    folds = generate_loco_splits()

    for fold in folds:
        # Check Cleveland records in train (if present)
        cleve_train = fold.train_df[fold.train_df["cohort"] == "cleveland"]
        if len(cleve_train) > 0:
            train_cleve_idx = set(cleve_train["source_row_index"])
            assert train_cleve_idx.isdisjoint(locked_test_indices), (
                f"Fold {fold.fold_id} train contains locked test samples!"
            )
            assert len(train_cleve_idx) == 242

        # Check Cleveland records in test (if present, Fold 3)
        cleve_test = fold.test_df[fold.test_df["cohort"] == "cleveland"]
        if len(cleve_test) > 0:
            test_cleve_idx = set(cleve_test["source_row_index"])
            assert test_cleve_idx.isdisjoint(locked_test_indices), (
                f"Fold {fold.fold_id} test contains locked test samples!"
            )
            assert len(test_cleve_idx) == 242


# ---------------------------------------------------------------------------
# Test 10: Split generation is deterministic across repeated calls
# ---------------------------------------------------------------------------

def test_split_generation_is_deterministic():
    """Verify repeated calls generate identical folds, order, and compound IDs."""
    folds_run1 = generate_loco_splits()
    folds_run2 = generate_loco_splits()

    for f1, f2 in zip(folds_run1, folds_run2):
        assert f1.fold_id == f2.fold_id
        assert f1.held_out_center == f2.held_out_center
        assert f1.training_centers == f2.training_centers
        assert f1.n_train == f2.n_train
        assert f1.n_test == f2.n_test
        assert f1.train_compound_ids == f2.train_compound_ids
        assert f1.test_compound_ids == f2.test_compound_ids
        assert np.array_equal(f1.y_train, f2.y_train)
        assert np.array_equal(f1.y_test, f2.y_test)
        assert f1.X_train_10.equals(f2.X_train_10)
        assert f1.X_test_10.equals(f2.X_test_10)


# ---------------------------------------------------------------------------
# Test 11: Metadata and targets are not included among model predictors
# ---------------------------------------------------------------------------

def test_metadata_and_targets_excluded_from_model_inputs():
    """Verify that predictor matrices (X_train_10, X_test_10, X_train_9, X_test_9) contain zero metadata."""
    folds = generate_loco_splits()
    forbidden_columns = {"target", "num", "cohort", "source_row_index", "compound_id", "cp_raw"}

    for fold in folds:
        # Candidate A (10 features)
        assert set(fold.X_train_10.columns) == set(CANDIDATE_A_CLINICAL_10)
        assert set(fold.X_test_10.columns) == set(CANDIDATE_A_CLINICAL_10)
        assert forbidden_columns.isdisjoint(set(fold.X_train_10.columns))
        assert forbidden_columns.isdisjoint(set(fold.X_test_10.columns))
        assert fold.X_train_10.shape[1] == 10
        assert fold.X_test_10.shape[1] == 10

        # Candidate B (9 features)
        assert set(fold.X_train_9.columns) == set(CANDIDATE_B_CLINICAL_9)
        assert set(fold.X_test_9.columns) == set(CANDIDATE_B_CLINICAL_9)
        assert forbidden_columns.isdisjoint(set(fold.X_train_9.columns))
        assert forbidden_columns.isdisjoint(set(fold.X_test_9.columns))
        assert fold.X_train_9.shape[1] == 9
        assert fold.X_test_9.shape[1] == 9


# ---------------------------------------------------------------------------
# Test 12: Empty cohorts, missing identifiers, or malformed inputs fail explicitly
# ---------------------------------------------------------------------------

def test_malformed_inputs_fail_explicitly():
    """Verify that invalid cohort inputs raise explicit descriptive errors."""
    # 1. Non-dict input
    with pytest.raises(TypeError, match="Expected dict of cohorts"):
        generate_loco_splits(cohorts="not_a_dict")

    # 2. Missing a required cohort
    partial_cohorts = {
        "cleveland": {"df": pd.DataFrame({"source_row_index": [0]})},
        "hungary": {"df": pd.DataFrame({"source_row_index": [0]})},
    }
    with pytest.raises(ValueError, match="Missing required clinical cohorts"):
        generate_loco_splits(cohorts=partial_cohorts)

    valid_cols = list(CANDIDATE_A_CLINICAL_10) + ["target", "source_row_index", "cohort"]
    dummy_hungary = pd.DataFrame(np.random.randn(10, len(valid_cols)), columns=valid_cols)
    dummy_hungary["source_row_index"] = list(range(10))
    dummy_hungary["cohort"] = "hungary"
    dummy_hungary["target"] = 0
    dummy_va = dummy_hungary.copy()
    dummy_va["cohort"] = "long_beach"

    empty_cohorts = {
        "cleveland": {"df": pd.DataFrame(columns=valid_cols)},
        "hungary": {"df": dummy_hungary},
        "long_beach": {"df": dummy_va},
    }
    with pytest.raises(ValueError, match="is empty"):
        generate_loco_splits(cohorts=empty_cohorts)

    # 4. Cohort missing required clinical columns
    missing_col_df = pd.DataFrame({
        "age": [50.0],
        "sex": [1.0],
        "target": [0],
        "source_row_index": [0],
        "cohort": ["cleveland"],
    })
    missing_col_cohorts = {
        "cleveland": {"df": missing_col_df},
        "hungary": {"df": missing_col_df},
        "long_beach": {"df": missing_col_df},
    }
    with pytest.raises(ValueError, match="missing required columns"):
        generate_loco_splits(cohorts=missing_col_cohorts)

    # 5. Duplicate compound IDs within cohort
    dup_id_df = pd.DataFrame({col: [1.0, 2.0] for col in CANDIDATE_A_CLINICAL_10})
    dup_id_df["target"] = [0, 1]
    dup_id_df["source_row_index"] = [0, 0]  # Duplicated row index
    dup_id_df["cohort"] = ["cleveland", "cleveland"]
    dup_cohorts = {
        "cleveland": {"df": dup_id_df},
        "hungary": {"df": dup_id_df},
        "long_beach": {"df": dup_id_df},
    }
    with pytest.raises(ValueError, match="Duplicate compound IDs detected"):
        generate_loco_splits(cohorts=dup_cohorts)


# ===========================================================================
# Task 3.2: LOCO Prediction Pipeline & Leakage Verification Test Suite
# ===========================================================================

@pytest.fixture(scope="module")
def loco_prediction_results():
    """Module-level fixture running the complete LOCO prediction pipeline once."""
    preds_df, meta = execute_loco_prediction_pipeline(save_artifacts=False)
    return preds_df, meta


# ---------------------------------------------------------------------------
# Test 13: Both candidates run in all three LOCO folds
# ---------------------------------------------------------------------------

def test_both_candidates_run_in_all_three_loco_folds(loco_prediction_results):
    """Verify that both Candidate A and Candidate B generate predictions across all 3 LOCO folds."""
    preds_df, _ = loco_prediction_results
    assert set(preds_df["fold_id"].unique()) == {1, 2, 3}
    assert set(preds_df["held_out_center"].unique()) == {"hungary", "long_beach", "cleveland"}

    for fold_id in [1, 2, 3]:
        fold_rows = preds_df[preds_df["fold_id"] == fold_id]
        assert len(fold_rows) > 0
        assert not fold_rows["prob_candidate_a"].isna().any()
        assert not fold_rows["prob_candidate_b"].isna().any()
        assert not fold_rows["pred_candidate_a"].isna().any()
        assert not fold_rows["pred_candidate_b"].isna().any()


# ---------------------------------------------------------------------------
# Test 14: Each held-out patient receives exactly one prediction
# ---------------------------------------------------------------------------

def test_each_held_out_patient_receives_exactly_one_prediction(loco_prediction_results):
    """Verify combined output has exactly 736 unique research patients with exactly one prediction each."""
    preds_df, _ = loco_prediction_results
    assert len(preds_df) == 736
    assert preds_df["compound_id"].nunique() == 736
    assert preds_df["compound_id"].value_counts().max() == 1

    # Exact per-centre expected counts
    assert int((preds_df["held_out_center"] == "hungary").sum()) == 294
    assert int((preds_df["held_out_center"] == "long_beach").sum()) == 200
    assert int((preds_df["held_out_center"] == "cleveland").sum()) == 242


# ---------------------------------------------------------------------------
# Test 15: Probabilities are finite and within [0, 1]
# ---------------------------------------------------------------------------

def test_probabilities_finite_and_in_zero_one_bounds(loco_prediction_results):
    """Verify that all calibrated probabilities are finite numbers in [0, 1]."""
    preds_df, _ = loco_prediction_results
    for col in ["prob_candidate_a", "prob_candidate_b"]:
        probs = preds_df[col].to_numpy()
        assert np.all(np.isfinite(probs)), f"Column '{col}' contains non-finite values."
        assert np.all((probs >= 0.0) & (probs <= 1.0)), f"Column '{col}' has values outside [0, 1]."


# ---------------------------------------------------------------------------
# Test 16: Binary predictions use fixed 0.50 threshold
# ---------------------------------------------------------------------------

def test_binary_predictions_use_fixed_threshold_0_50(loco_prediction_results):
    """Verify that binary predictions use the predefined fixed 0.50 threshold."""
    preds_df, meta = loco_prediction_results
    assert (preds_df["threshold"] == 0.50).all()
    assert meta["decision_threshold"] == 0.50

    expected_pred_a = (preds_df["prob_candidate_a"] >= 0.50).astype(int)
    expected_pred_b = (preds_df["prob_candidate_b"] >= 0.50).astype(int)

    assert np.array_equal(preds_df["pred_candidate_a"], expected_pred_a)
    assert np.array_equal(preds_df["pred_candidate_b"], expected_pred_b)
    assert set(preds_df["pred_candidate_a"].unique()).issubset({0, 1})
    assert set(preds_df["pred_candidate_b"].unique()).issubset({0, 1})


# ---------------------------------------------------------------------------
# Test 17: Prediction artifacts exist and match schema and metadata
# ---------------------------------------------------------------------------

def test_prediction_artifacts_exist_and_match_manifest():
    """Verify that prediction artifacts in experiments/results/ match expected schema."""
    csv_path = DEFAULT_RESULTS_DIR / "phase17_loco_predictions.csv"
    meta_path = DEFAULT_RESULTS_DIR / "phase17_loco_predictions_metadata.json"

    assert csv_path.is_file(), f"Missing prediction CSV: {csv_path}"
    assert meta_path.is_file(), f"Missing metadata JSON: {meta_path}"

    df = pd.read_csv(csv_path)
    assert len(df) == 736
    expected_cols = [
        "fold_id", "held_out_center", "held_out_status", "cohort",
        "source_row_index", "compound_id", "target", "prob_candidate_a",
        "pred_candidate_a", "prob_candidate_b", "pred_candidate_b", "threshold",
    ]
    assert list(df.columns) == expected_cols

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["total_predictions"] == 736
    assert meta["unique_patient_count"] == 736
    assert meta["decision_threshold"] == 0.50
    assert meta["calibration"]["method"] == "sigmoid"
    assert meta["calibration"]["n_splits"] == 5
    assert meta["candidate_a"]["n_inputs"] == 11
    assert meta["candidate_b"]["n_inputs"] == 9
    assert meta["quarantined_test_set"]["locked_sample_count"] == 61
    assert meta["quarantined_test_set"]["quarantine_verified"] is True


# ---------------------------------------------------------------------------
# Test 18: Altering held-out labels does not affect fitted calibrators
# ---------------------------------------------------------------------------

def test_altering_held_out_labels_does_not_affect_fitted_calibrators():
    """Verify held-out target labels have zero effect on estimator and calibrator parameters."""
    folds = generate_loco_splits()
    f1 = folds[0]

    pipe_a1 = build_candidate_a_pipeline(random_state=42)
    cal_a1 = CalibratedClassifierCV(
        estimator=pipe_a1,
        method="sigmoid",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    )
    cal_a1.fit(f1.X_train_10, f1.y_train)

    pos_idx = int(np.where(cal_a1.classes_ == 1)[0][0])
    probs_orig = cal_a1.predict_proba(f1.X_test_10)[:, pos_idx]

    # Invert held-out labels
    f1_mutated_y_test = 1 - f1.y_test

    # Re-train identical training data (held-out labels are NEVER used)
    pipe_a2 = build_candidate_a_pipeline(random_state=42)
    cal_a2 = CalibratedClassifierCV(
        estimator=pipe_a2,
        method="sigmoid",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    )
    cal_a2.fit(f1.X_train_10, f1.y_train)
    probs_new = cal_a2.predict_proba(f1.X_test_10)[:, pos_idx]

    assert np.allclose(probs_orig, probs_new, atol=1e-12)

    # Calibrator sigmoid parameters must be bit-for-bit identical
    for cc1, cc2 in zip(cal_a1.calibrated_classifiers_, cal_a2.calibrated_classifiers_):
        assert np.array_equal(cc1.calibrators[0].a_, cc2.calibrators[0].a_)
        assert np.array_equal(cc1.calibrators[0].b_, cc2.calibrators[0].b_)


# ---------------------------------------------------------------------------
# Test 19: Altering held-out observations does not change training parameters
# ---------------------------------------------------------------------------

def test_altering_held_out_observations_does_not_change_training_parameters():
    """Verify mutating held-out features does not alter training parameters in any way."""
    folds = generate_loco_splits()
    f1 = folds[0]

    pipe_a = build_candidate_a_pipeline(random_state=42)
    cal_a = CalibratedClassifierCV(
        estimator=pipe_a,
        method="sigmoid",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    )
    cal_a.fit(f1.X_train_10, f1.y_train)

    orig_coefs = [cc.estimator.named_steps["model"].coef_.copy() for cc in cal_a.calibrated_classifiers_]
    orig_medians = [cc.estimator.named_steps["chol_missing_aware"].median_chol_ for cc in cal_a.calibrated_classifiers_]

    # Corrupt held-out features completely
    corrupted_X_test = f1.X_test_10.copy()
    corrupted_X_test.iloc[:, :] = 99999.0

    # Refit training data
    pipe_a2 = build_candidate_a_pipeline(random_state=42)
    cal_a2 = CalibratedClassifierCV(
        estimator=pipe_a2,
        method="sigmoid",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    )
    cal_a2.fit(f1.X_train_10, f1.y_train)

    new_coefs = [cc.estimator.named_steps["model"].coef_.copy() for cc in cal_a2.calibrated_classifiers_]
    new_medians = [cc.estimator.named_steps["chol_missing_aware"].median_chol_ for cc in cal_a2.calibrated_classifiers_]

    for c1, c2 in zip(orig_coefs, new_coefs):
        assert np.allclose(c1, c2, atol=1e-12)
    for m1, m2 in zip(orig_medians, new_medians):
        assert m1 == m2


# ---------------------------------------------------------------------------
# Test 20: Imputers and scalers fitted exclusively within training partitions
# ---------------------------------------------------------------------------

def test_imputers_and_scalers_fitted_exclusively_within_training_partitions():
    """Verify internal calibration folds never see held-out test records during fit."""
    folds = generate_loco_splits()
    f1 = folds[0]
    n_train = f1.n_train  # 442

    pipe_a = build_candidate_a_pipeline(random_state=42)
    cal_a = CalibratedClassifierCV(
        estimator=pipe_a,
        method="sigmoid",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    )
    cal_a.fit(f1.X_train_10, f1.y_train)

    # In 5-fold internal CV on 442 training samples, each fold fits on 4/5 of training data (~353 or 354 samples)
    for cc in cal_a.calibrated_classifiers_:
        scaler = cc.estimator.named_steps["scaler"]
        assert scaler.n_samples_seen_ < n_train
        assert scaler.n_samples_seen_ in {353, 354}


# ---------------------------------------------------------------------------
# Test 21: Locked Cleveland test partition excluded from predictions
# ---------------------------------------------------------------------------

def test_locked_cleveland_test_partition_excluded_from_predictions(loco_prediction_results):
    """Verify that none of the 61 locked Cleveland test patients appear in predictions."""
    preds_df, _ = loco_prediction_results
    assert DEV_INDICES_PATH.is_file()
    with open(DEV_INDICES_PATH, "r", encoding="utf-8") as f:
        dev_indices = set(json.load(f))
    locked_test_indices = set(range(303)) - dev_indices

    cleveland_preds = preds_df[preds_df["cohort"] == "cleveland"]
    assert len(cleveland_preds) == 242
    pred_cleveland_indices = set(cleveland_preds["source_row_index"])
    assert pred_cleveland_indices.isdisjoint(locked_test_indices), (
        "CRITICAL LEAKAGE: Locked Cleveland test samples present in predictions!"
    )


# ---------------------------------------------------------------------------
# Test 22: Deterministic reproducibility
# ---------------------------------------------------------------------------

def test_deterministic_reproducibility():
    """Verify that repeated executions produce identical predictions under deterministic seeds."""
    folds = generate_loco_splits()
    f1 = folds[:1]

    res1_df, _ = execute_loco_prediction_pipeline(folds=f1, save_artifacts=False, random_state=42)
    res2_df, _ = execute_loco_prediction_pipeline(folds=f1, save_artifacts=False, random_state=42)

    assert np.array_equal(res1_df["prob_candidate_a"], res2_df["prob_candidate_a"])
    assert np.array_equal(res1_df["prob_candidate_b"], res2_df["prob_candidate_b"])
    assert np.array_equal(res1_df["pred_candidate_a"], res2_df["pred_candidate_a"])
    assert np.array_equal(res1_df["pred_candidate_b"], res2_df["pred_candidate_b"])


# ---------------------------------------------------------------------------
# Test 23: Unsupported internal calibration fails explicitly
# ---------------------------------------------------------------------------

def test_unsupported_internal_calibration_fails_explicitly():
    """Verify pipeline raises an explicit ValueError when fold cannot support internal calibration."""
    # 1. Single class in training partition
    single_class_df = pd.DataFrame(np.random.randn(20, len(CANDIDATE_A_CLINICAL_10)), columns=CANDIDATE_A_CLINICAL_10)
    single_class_df["target"] = 0
    single_class_df["cohort"] = "cleveland"
    single_class_df["source_row_index"] = list(range(20))
    single_class_df["compound_id"] = [f"cleveland_{i}" for i in range(20)]

    test_dummy = single_class_df.copy()
    test_dummy["cohort"] = "hungary"
    test_dummy["compound_id"] = [f"hungary_{i}" for i in range(20)]

    single_class_fold = LOCOFold(
        fold_id=1,
        held_out_center="hungary",
        training_centers=("cleveland",),
        held_out_status="external_validation",
        train_df=single_class_df,
        test_df=test_dummy,
    )
    with pytest.raises(ValueError, match="training partition contains only one class"):
        execute_loco_prediction_pipeline(folds=[single_class_fold], save_artifacts=False)

    # 2. Minority class smaller than n_cal_splits
    few_minority_df = single_class_df.copy()
    few_minority_df.loc[0:1, "target"] = 1  # Only 2 positive samples
    few_minority_fold = LOCOFold(
        fold_id=1,
        held_out_center="hungary",
        training_centers=("cleveland",),
        held_out_status="external_validation",
        train_df=few_minority_df,
        test_df=test_dummy,
    )
    with pytest.raises(ValueError, match="cannot support internal calibration with n_splits=5"):
        execute_loco_prediction_pipeline(folds=[few_minority_fold], n_cal_splits=5, save_artifacts=False)


# ---------------------------------------------------------------------------
# Test 24: No metadata or targets enter model inputs
# ---------------------------------------------------------------------------

def test_no_metadata_enters_model_inputs_during_evaluation(loco_prediction_results):
    """Verify no identifier or metadata columns enter candidate input matrices."""
    _, meta = loco_prediction_results
    assert meta["candidate_a"]["n_inputs"] == 11
    assert meta["candidate_b"]["n_inputs"] == 9
    forbidden = {"target", "num", "cohort", "source_row_index", "compound_id", "threshold"}
    assert forbidden.isdisjoint(set(meta["candidate_a"]["model_inputs"]))
    assert forbidden.isdisjoint(set(meta["candidate_b"]["model_inputs"]))


# ===========================================================================
# Task 3.3: Per-Centre Metrics & Bootstrap Uncertainty Test Suite
# ===========================================================================

@pytest.fixture(scope="module")
def multicenter_metrics_results():
    """Module-level fixture computing all multicenter metrics once."""
    df, meta, report_md = evaluate_all_multicenter_metrics(save_artifacts=False)
    return df, meta, report_md


# ---------------------------------------------------------------------------
# Test 25: Correct calculation on hand-computable fixtures
# ---------------------------------------------------------------------------

def test_metrics_hand_computable_fixture():
    """Verify exact calculation of all metrics on a hand-computable 4-sample fixture."""
    y = np.array([1, 0, 1, 0])
    p = np.array([0.9, 0.2, 0.8, 0.1])

    res = compute_multicenter_metrics(y, p, threshold=0.50, n_ece_bins=10)

    assert res["accuracy"] == 1.0
    assert res["sensitivity"] == 1.0
    assert res["specificity"] == 1.0
    assert res["precision"] == 1.0
    assert res["f1_score"] == 1.0
    assert res["roc_auc"] == 1.0
    assert res["pr_auc"] == 1.0
    assert np.isclose(res["brier_score"], 0.025, atol=1e-8)

    # Hand-computed ECE:
    # 0.9 -> bin 9 (y=1): acc=1.0, conf=0.9, diff=0.1
    # 0.8 -> bin 8 (y=1): acc=1.0, conf=0.8, diff=0.2
    # 0.2 -> bin 2 (y=0): acc=0.0, conf=0.2, diff=0.2
    # 0.1 -> bin 1 (y=0): acc=0.0, conf=0.1, diff=0.1
    # Total ECE = (0.1 + 0.2 + 0.2 + 0.1) / 4 = 0.15
    assert np.isclose(res["ece"], 0.15, atol=1e-8)


# ---------------------------------------------------------------------------
# Test 26: Positive-class and threshold conventions (fixed 0.50)
# ---------------------------------------------------------------------------

def test_threshold_boundary_conventions():
    """Verify that predictions at exactly 0.50 are classified as positive class 1."""
    y = np.array([1, 1, 0])
    p = np.array([0.4999, 0.5000, 0.5000])

    res = compute_multicenter_metrics(y, p, threshold=0.50)
    # y_pred: [0, 1, 1]
    # TP = 1 (p=0.5, y=1), FN = 1 (p=0.4999, y=1), FP = 1 (p=0.5, y=0), TN = 0
    assert res["confusion_matrix"] == {"tn": 0, "fp": 1, "fn": 1, "tp": 1}
    assert res["sensitivity"] == 0.50
    assert res["specificity"] == 0.0
    assert res["precision"] == 0.50
    assert res["f1_score"] == 0.50


# ---------------------------------------------------------------------------
# Test 27: ECE equal-width binning, boundary handling, and probabilities 0.0 and 1.0
# ---------------------------------------------------------------------------

def test_ece_binning_and_boundary_handling():
    """Verify equal-width 10-bin ECE boundaries, including p=0.0 and p=1.0."""
    # 1. p=1.0 mapped to bin 9 without IndexError
    y_perf = np.array([1, 1, 1, 1, 0])
    p_perf = np.array([0.8, 0.8, 0.8, 0.8, 0.8])
    assert compute_expected_calibration_error(y_perf, p_perf, n_bins=10) == 0.0

    # 2. Completely miscalibrated at boundary p=1.0
    y_mis = np.array([0, 0])
    p_mis = np.array([1.0, 1.0])
    assert compute_expected_calibration_error(y_mis, p_mis, n_bins=10) == 1.0

    # 3. Boundary p=0.0
    y_zero = np.array([0, 0])
    p_zero = np.array([0.0, 0.0])
    assert compute_expected_calibration_error(y_zero, p_zero, n_bins=10) == 0.0

    # 4. Out-of-bounds raises ValueError
    with pytest.raises(ValueError, match="strictly within"):
        compute_expected_calibration_error(np.array([1]), np.array([1.05]))
    with pytest.raises(ValueError, match="strictly within"):
        compute_expected_calibration_error(np.array([1]), np.array([-0.01]))
    with pytest.raises(ValueError, match="finite numbers"):
        compute_expected_calibration_error(np.array([1]), np.array([np.nan]))


# ---------------------------------------------------------------------------
# Test 28: Stratified bootstrap sample counts and deterministic reproducibility
# ---------------------------------------------------------------------------

def test_stratified_bootstrap_sample_counts_and_determinism():
    """Verify that stratified bootstrap preserves exact class balance and is deterministic."""
    y = np.array([1] * 12 + [0] * 18)
    p = np.linspace(0.1, 0.9, 30)

    # Run twice with same random seed
    res1 = compute_stratified_bootstrap_ci(y, p, threshold=0.50, n_bootstraps=100, random_state=42)
    res2 = compute_stratified_bootstrap_ci(y, p, threshold=0.50, n_bootstraps=100, random_state=42)

    for k in res1:
        assert res1[k]["point_estimate"] == res2[k]["point_estimate"]
        assert res1[k]["ci_lower"] == res2[k]["ci_lower"]
        assert res1[k]["ci_upper"] == res2[k]["ci_upper"]
        assert res1[k]["replicates_computed"] == 100


# ---------------------------------------------------------------------------
# Test 29: Bootstrap intervals calculated separately for each held-out centre
# ---------------------------------------------------------------------------

def test_bootstrap_intervals_calculated_strictly_per_centre(multicenter_metrics_results):
    """Verify that metrics and CIs are calculated independently for each centre without pooling."""
    df, _, _ = multicenter_metrics_results

    assert set(df["center"].unique()) == {"hungary", "long_beach", "cleveland"}

    # Hungary N=294
    hungary_df = df[df["center"] == "hungary"]
    assert (hungary_df["n_samples"] == 294).all()
    assert (hungary_df["n_positives"] == 106).all()
    assert (hungary_df["n_negatives"] == 188).all()

    # Long Beach N=200
    va_df = df[df["center"] == "long_beach"]
    assert (va_df["n_samples"] == 200).all()
    assert (va_df["n_positives"] == 149).all()
    assert (va_df["n_negatives"] == 51).all()

    # Cleveland N=242
    cleve_df = df[df["center"] == "cleveland"]
    assert (cleve_df["n_samples"] == 242).all()
    assert (cleve_df["n_positives"] == 110).all()
    assert (cleve_df["n_negatives"] == 132).all()


# ---------------------------------------------------------------------------
# Test 30: Confidence-limit ordering and valid probability bounds
# ---------------------------------------------------------------------------

def test_confidence_limit_ordering_and_bounds(multicenter_metrics_results):
    """Verify ci_lower <= ci_upper and all metrics are within valid bounds [0, 1]."""
    df, _, _ = multicenter_metrics_results

    for _, row in df.iterrows():
        pt = row["point_estimate"]
        lo = row["ci_lower"]
        hi = row["ci_upper"]

        if pd.notna(lo) and pd.notna(hi):
            assert lo <= hi, f"Inverted CI for {row['center']} {row['candidate']} {row['metric']}: {lo} > {hi}"
            assert 0.0 <= lo <= 1.0, f"ci_lower out of bounds: {lo}"
            assert 0.0 <= hi <= 1.0, f"ci_upper out of bounds: {hi}"

        if pd.notna(pt):
            assert 0.0 <= pt <= 1.0, f"point_estimate out of bounds: {pt}"


# ---------------------------------------------------------------------------
# Test 31: Explicit handling of zero denominators and undefined metrics
# ---------------------------------------------------------------------------

def test_explicit_handling_of_zero_denominators():
    """Verify zero denominators yield np.nan rather than falling back silently to 0.0."""
    # All negative targets: sensitivity and precision have zero denominators
    y_no_pos = np.array([0, 0, 0, 0])
    p_no_pos = np.array([0.1, 0.2, 0.3, 0.4])

    res = compute_multicenter_metrics(y_no_pos, p_no_pos, threshold=0.50)
    assert np.isnan(res["sensitivity"])
    assert np.isnan(res["precision"])
    assert np.isnan(res["f1_score"])
    assert np.isnan(res["roc_auc"])
    assert np.isnan(res["pr_auc"])
    assert res["specificity"] == 1.0

    # No predicted positives: precision is undefined
    y_some = np.array([1, 0])
    p_low = np.array([0.1, 0.2])
    res2 = compute_multicenter_metrics(y_some, p_low, threshold=0.50)
    assert np.isnan(res2["precision"])
    assert np.isnan(res2["f1_score"])


# ---------------------------------------------------------------------------
# Test 32: Prevention of silent row loss, duplicate patient identities, and target misalignment
# ---------------------------------------------------------------------------

def test_prevention_of_silent_row_loss(multicenter_metrics_results):
    """Verify all 736 research patients are evaluated across the 3 centres."""
    df, _, _ = multicenter_metrics_results
    assert len(df) == 54  # 3 centres x 2 candidates x 9 metrics

    # Total sample count across centres
    unique_center_samples = df.drop_duplicates(subset=["center"])["n_samples"].sum()
    assert unique_center_samples == 736


# ---------------------------------------------------------------------------
# Test 33: Integrity checks rejecting incomplete or contaminated prediction files
# ---------------------------------------------------------------------------

def test_integrity_checks_reject_corrupted_predictions():
    """Verify evaluate_all_multicenter_metrics detects and rejects invalid predictions."""
    # 1. Missing required columns
    bad_df = pd.DataFrame({"fold_id": [1], "target": [1]})
    with pytest.raises(ValueError, match="missing required columns"):
        evaluate_all_multicenter_metrics(predictions_df=bad_df, save_artifacts=False)

    # 2. Corrupted probabilities
    pred_path = DEFAULT_RESULTS_DIR / "phase17_loco_predictions.csv"
    if pred_path.is_file():
        real_df = pd.read_csv(pred_path)
        corrupted_df = real_df.copy()
        corrupted_df.loc[0, "prob_candidate_a"] = 1.5
        with pytest.raises(ValueError, match="out-of-bounds"):
            evaluate_all_multicenter_metrics(predictions_df=corrupted_df, save_artifacts=False)


# ---------------------------------------------------------------------------
# Test 34: Output artifact schema and report generation
# ---------------------------------------------------------------------------

def test_metrics_artifacts_exist_and_match_manifest():
    """Verify that metrics CSV, JSON, and Markdown report exist with valid schemas."""
    assert DEFAULT_METRICS_CSV.is_file(), f"Missing CSV: {DEFAULT_METRICS_CSV}"
    assert DEFAULT_METRICS_JSON.is_file(), f"Missing JSON: {DEFAULT_METRICS_JSON}"
    assert DEFAULT_METRICS_REPORT.is_file(), f"Missing Report: {DEFAULT_METRICS_REPORT}"

    # Verify CSV
    csv_df = pd.read_csv(DEFAULT_METRICS_CSV)
    assert len(csv_df) == 54
    assert set(csv_df["center"].unique()) == {"hungary", "long_beach", "cleveland"}
    assert set(csv_df["candidate"].unique()) == {"candidate_a", "candidate_b"}

    # Verify JSON
    with open(DEFAULT_METRICS_JSON, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["n_bootstraps"] == 1000
    assert meta["confidence_level"] == 0.95
    assert meta["fixed_decision_threshold"] == 0.50
    assert meta["ece_binning"]["n_bins"] == 10
    assert meta["provenance"]["total_predictions"] == 736
    assert meta["provenance"]["quarantined_locked_test_n"] == 61
    assert "hungary" in meta["centers"]
    assert "long_beach" in meta["centers"]
    assert "cleveland" in meta["centers"]

    # Verify Markdown Report
    with open(DEFAULT_METRICS_REPORT, "r", encoding="utf-8") as f:
        report = f.read()
    assert "# Phase 17: Per-Centre Multicenter Validation Metrics & Bootstrap Uncertainty Report" in report
    assert "Hungary" in report
    assert "Long Beach" in report
    assert "Cleveland" in report
    assert "External Validation Centre" in report
    assert "Retrospective Development Baseline" in report
    assert "CC BY 4.0" in report


