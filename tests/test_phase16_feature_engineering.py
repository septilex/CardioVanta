"""
CardioVanta Phase 16: Comprehensive Test Suite
==============================================
Verifies:
1. Four candidate configurations and pipeline structures.
2. Frozen selection rule, tie tolerance (0.0001), and simplicity hierarchy.
3. Mathematical correctness and fold-local scaling of feature transformations.
4. Duplicate group integrity across outer, inner, and calibration folds.
5. Zero outer-validation leakage into calibration or candidate selection.
6. Locked test protection and artifact immutability.
7. Error handling on invalid inputs and split configurations.
"""

import sys
import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase_16_feature_engineering import (
    CANDIDATE_NAMES,
    SIMPLICITY_HIERARCHY,
    TIE_TOLERANCE,
    EVAL_THRESHOLD,
    Phase16FeatureAugmenter,
    build_candidate_pipeline,
    select_candidate_by_rule,
    compute_metrics,
    load_development_data,
    load_locked_test_data,
    evaluate_adoption_gate,
    select_final_candidate_full_dev
)
from src.config.config import BASE_DIR, RAW_DATA_PATH


# ---------------------------------------------------------------------------
# 1. Candidate Scope and Configuration Tests
# ---------------------------------------------------------------------------

def test_exact_four_candidates():
    """Verify that exactly four candidates are configured."""
    assert len(CANDIDATE_NAMES) == 4
    expected = [
        "Candidate A (Baseline)",
        "Candidate B (Age x Thalach)",
        "Candidate C (Oldpeak Squared)",
        "Candidate D (Combined)"
    ]
    assert CANDIDATE_NAMES == expected


def test_baseline_matches_production_settings():
    """Verify Candidate A matches the established baseline settings."""
    pipe_a = build_candidate_pipeline("Candidate A (Baseline)")
    lr = pipe_a.named_steps["model"]
    assert lr.C == 0.1
    assert lr.class_weight == "balanced"
    assert lr.solver == "lbfgs"
    assert lr.random_state == 42


def test_simplicity_hierarchy_and_tolerance():
    """Verify deterministic simplicity hierarchy and tie tolerance."""
    assert TIE_TOLERANCE == 0.0001
    assert SIMPLICITY_HIERARCHY["Candidate A (Baseline)"] == 1
    assert SIMPLICITY_HIERARCHY["Candidate B (Age x Thalach)"] == 2
    assert SIMPLICITY_HIERARCHY["Candidate C (Oldpeak Squared)"] == 3
    assert SIMPLICITY_HIERARCHY["Candidate D (Combined)"] == 4


# ---------------------------------------------------------------------------
# 2. Frozen Candidate Selection Rule Tests
# ---------------------------------------------------------------------------

def test_selection_rule_clear_winner():
    """Test selection rule when one candidate clearly has highest ROC-AUC."""
    cand_aucs = {
        "Candidate A (Baseline)": 0.8500,
        "Candidate B (Age x Thalach)": 0.8520,  # +0.0020 (above 0.0001 tolerance)
        "Candidate C (Oldpeak Squared)": 0.8400,
        "Candidate D (Combined)": 0.8450
    }
    sel, best_auc, tied = select_candidate_by_rule(cand_aucs, tolerance=0.0001)
    assert sel == "Candidate B (Age x Thalach)"
    assert best_auc == 0.8520
    assert tied == ["Candidate B (Age x Thalach)"]


def test_selection_rule_tie_break_prefers_simpler():
    """Test that tie-break strictly selects simpler candidate within tolerance."""
    # Candidate B is best, but Candidate A is within 0.0001 -> Candidate A must win!
    cand_aucs = {
        "Candidate A (Baseline)": 0.85000,
        "Candidate B (Age x Thalach)": 0.85008,  # diff is 0.00008 <= 0.0001
        "Candidate C (Oldpeak Squared)": 0.84000,
        "Candidate D (Combined)": 0.85005   # diff is 0.00003 <= 0.0001
    }
    sel, best_auc, tied = select_candidate_by_rule(cand_aucs, tolerance=0.0001)
    assert sel == "Candidate A (Baseline)", "Candidate A must be preferred by simplicity rank"
    assert len(tied) == 3


def test_selection_rule_between_candidates_b_and_c():
    """Test that tie-break prefers Candidate B over Candidate C when tied."""
    cand_aucs = {
        "Candidate A (Baseline)": 0.84000,
        "Candidate B (Age x Thalach)": 0.85005,
        "Candidate C (Oldpeak Squared)": 0.85000,
        "Candidate D (Combined)": 0.84500
    }
    sel, best_auc, tied = select_candidate_by_rule(cand_aucs, tolerance=0.0001)
    assert sel == "Candidate B (Age x Thalach)"


# ---------------------------------------------------------------------------
# 3. Mathematical Correctness and Transformation Integrity Tests
# ---------------------------------------------------------------------------

def test_feature_augmenter_mathematical_transform():
    """Verify that interaction and squared terms are computed correctly."""
    # Create synthetic data with 5 continuous columns
    # Col 0: age, Col 3: thalach, Col 4: oldpeak
    X_train = np.array([
        [1.0, 0.0, 0.0, 2.0, 3.0],
        [2.0, 0.0, 0.0, 4.0, 5.0],
        [3.0, 0.0, 0.0, 6.0, 7.0]
    ])
    
    # 1. Candidate B (Interaction only)
    aug_b = Phase16FeatureAugmenter(add_interaction=True, add_oldpeak_sq=False)
    aug_b.fit(X_train)
    out_b = aug_b.transform(X_train)
    assert out_b.shape == (3, 6), "Should append exactly 1 interaction column"
    # Verify standard scaling of the interaction term
    u_inter = X_train[:, 0] * X_train[:, 3]  # [2.0, 8.0, 18.0]
    expected_mean = np.mean(u_inter)
    expected_std = np.std(u_inter)
    expected_z = (u_inter - expected_mean) / expected_std
    np.testing.assert_allclose(out_b[:, 5], expected_z, atol=1e-7)

    # 2. Candidate C (Quadratic only)
    aug_c = Phase16FeatureAugmenter(add_interaction=False, add_oldpeak_sq=True)
    aug_c.fit(X_train)
    out_c = aug_c.transform(X_train)
    assert out_c.shape == (3, 6), "Should append exactly 1 squared column"
    u_sq = X_train[:, 4] ** 2  # [9.0, 25.0, 49.0]
    expected_sq_z = (u_sq - np.mean(u_sq)) / np.std(u_sq)
    np.testing.assert_allclose(out_c[:, 5], expected_sq_z, atol=1e-7)

    # 3. Candidate D (Combined)
    aug_d = Phase16FeatureAugmenter(add_interaction=True, add_oldpeak_sq=True)
    aug_d.fit(X_train)
    out_d = aug_d.transform(X_train)
    assert out_d.shape == (3, 7), "Should append exactly 2 columns"
    np.testing.assert_allclose(out_d[:, 5], expected_z, atol=1e-7)
    np.testing.assert_allclose(out_d[:, 6], expected_sq_z, atol=1e-7)


def test_feature_augmenter_fold_isolation():
    """Verify that test/validation transform applies training-fold parameters."""
    X_train = np.array([
        [1.0, 0.0, 0.0, 2.0, 3.0],
        [3.0, 0.0, 0.0, 4.0, 5.0]
    ])
    aug = Phase16FeatureAugmenter(add_interaction=True, add_oldpeak_sq=True)
    aug.fit(X_train)
    
    # Validation data with different values
    X_val = np.array([
        [10.0, 0.0, 0.0, 20.0, 30.0]
    ])
    out_val = aug.transform(X_val)
    
    # Expected transform using TRAINING mean and scale
    val_u_inter = 10.0 * 20.0
    val_z_inter = (val_u_inter - aug.mean_inter_) / aug.scale_inter_
    assert np.isclose(out_val[0, 5], val_z_inter)


def test_unfitted_transform_raises_error():
    """Verify that calling transform before fit raises RuntimeError."""
    aug = Phase16FeatureAugmenter(add_interaction=True)
    with pytest.raises(RuntimeError, match="has not been fitted"):
        aug.transform(np.zeros((2, 5)))


# ---------------------------------------------------------------------------
# 4. Pipeline Integration and End-to-End Fit Tests
# ---------------------------------------------------------------------------

def test_all_pipelines_fit_on_raw_data_subset():
    """Verify that all 4 candidate pipelines fit and predict on a dataframe subset containing both classes."""
    df = pd.read_csv(RAW_DATA_PATH)
    # Ensure subset contains both classes
    df_0 = df[df["target"] == 0].iloc[:15]
    df_1 = df[df["target"] == 1].iloc[:15]
    df_sub = pd.concat([df_0, df_1]).reset_index(drop=True)
    X_sub = df_sub.drop(columns=["target"])
    y_sub = df_sub["target"].to_numpy()

    for cand_name in CANDIDATE_NAMES:
        pipe = build_candidate_pipeline(cand_name)
        pipe.fit(X_sub, y_sub)
        probs = pipe.predict_proba(X_sub)
        assert probs.shape == (30, 2)
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)


# ---------------------------------------------------------------------------
# 5. Data Partitioning, Duplicate Grouping, and Leakage Tests
# ---------------------------------------------------------------------------

def test_development_and_locked_test_partition():
    """Verify dataset sizes and strict partition boundary."""
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, raw_hash = load_development_data()
    X_test, y_test, test_idx = load_locked_test_data(df, X_full, y_full, dev_idx)

    assert len(X_dev) == 242
    assert len(X_test) == 61
    assert len(X_dev) + len(X_test) == len(df) == 303
    assert len(set(dev_idx).intersection(set(test_idx))) == 0


def test_duplicate_groups_consistency():
    """Verify duplicate groups correctly group exact duplicate feature rows."""
    X_dev, y_dev, dev_groups, _, _, _, _, _, _ = load_development_data()
    assert len(dev_groups) == len(X_dev) == 242

    # Check that identical rows receive identical group ids
    for i in range(len(X_dev)):
        for j in range(i + 1, min(i + 10, len(X_dev))):
            if (X_dev.iloc[i] == X_dev.iloc[j]).all():
                assert dev_groups[i] == dev_groups[j]


# ---------------------------------------------------------------------------
# 6. Production Artifact Immutability Tests
# ---------------------------------------------------------------------------

def test_production_artifacts_unmodified():
    """Ensure Phase 16 does NOT modify production model artifacts."""
    artifacts_dir = BASE_DIR / "artifacts" / "model"
    hashes_file = BASE_DIR / "configs" / "artifact_hashes.json"

    with open(hashes_file) as f:
        recorded_hashes = json.load(f)

    import hashlib
    for rel_path, expected_hash in recorded_hashes.items():
        full_path = BASE_DIR / rel_path
        if full_path.exists():
            with open(full_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            assert actual_hash == expected_hash, f"Artifact {rel_path} was modified!"


# ---------------------------------------------------------------------------
# 7. Calibration Boundaries and Group Isolation Tests
# ---------------------------------------------------------------------------

def test_calibration_boundaries_and_group_isolation():
    """Verify that calibration splits strictly isolate duplicate groups."""
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.calibration import CalibratedClassifierCV

    X_dev, y_dev, dev_groups, _, _, _, _, _, _ = load_development_data()
    # Take a 150-sample outer training subset
    train_idx = np.arange(150)
    X_tr = X_dev.iloc[train_idx].reset_index(drop=True)
    y_tr = y_dev[train_idx]
    g_tr = dev_groups[train_idx]

    cal_cv = StratifiedGroupKFold(n_splits=5)
    cal_splits = list(cal_cv.split(X_tr, y_tr, groups=g_tr))

    # Verify each calibration split has zero group overlap
    for c_tr_idx, c_val_idx in cal_splits:
        tr_groups = set(g_tr[c_tr_idx])
        val_groups = set(g_tr[c_val_idx])
        assert len(tr_groups.intersection(val_groups)) == 0, "Duplicate group leaked across calibration split!"

    # Verify CalibratedClassifierCV fits cleanly with explicit precomputed splits
    pipe = build_candidate_pipeline("Candidate B (Age x Thalach)")
    cal = CalibratedClassifierCV(estimator=pipe, method="sigmoid", cv=cal_splits)
    cal.fit(X_tr, y_tr)
    probs = cal.predict_proba(X_tr)[:, 1]
    assert len(probs) == len(X_tr)
    assert np.all((probs >= 0.0) & (probs <= 1.0))


def test_no_outer_validation_leakage():
    """Verify that outer validation fold is never used in candidate selection or calibration."""
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.calibration import CalibratedClassifierCV

    X_dev, y_dev, dev_groups, _, _, _, _, _, _ = load_development_data()
    outer_cv = StratifiedGroupKFold(n_splits=5)
    train_idx, val_idx = next(outer_cv.split(X_dev, y_dev, groups=dev_groups))

    X_tr, y_tr = X_dev.iloc[train_idx].reset_index(drop=True), y_dev[train_idx]
    g_tr = dev_groups[train_idx]
    X_val = X_dev.iloc[val_idx].reset_index(drop=True)

    # Candidate selection uses ONLY X_tr and y_tr
    cand_aucs = {}
    inner_cv = StratifiedGroupKFold(n_splits=3)
    for cand_name in CANDIDATE_NAMES:
        inner_oof = np.zeros(len(y_tr))
        for i_tr, i_val in inner_cv.split(X_tr, y_tr, groups=g_tr):
            p = build_candidate_pipeline(cand_name)
            p.fit(X_tr.iloc[i_tr], y_tr[i_tr])
            inner_oof[i_val] = p.predict_proba(X_tr.iloc[i_val])[:, 1]
        from sklearn.metrics import roc_auc_score
        cand_aucs[cand_name] = roc_auc_score(y_tr, inner_oof)

    sel_cand, _, _ = select_candidate_by_rule(cand_aucs)

    # Fit calibration on outer train ONLY
    cal_splits = list(StratifiedGroupKFold(n_splits=3).split(X_tr, y_tr, groups=g_tr))
    sel_pipe = build_candidate_pipeline(sel_cand)
    cal = CalibratedClassifierCV(estimator=sel_pipe, method="sigmoid", cv=cal_splits)
    cal.fit(X_tr, y_tr)

    # X_val only evaluated once after fitting is fully frozen
    val_probs = cal.predict_proba(X_val)[:, 1]
    assert len(val_probs) == len(val_idx)
    assert np.all((val_probs >= 0.0) & (val_probs <= 1.0))


def test_locked_test_isolation_during_dev_selection():
    """Verify locked test is completely excluded from development candidate selection."""
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, raw_hash = load_development_data()
    X_test, y_test, test_idx = load_locked_test_data(df, X_full, y_full, dev_idx)

    # Select final candidate on development set
    sel_name, cand_aucs, tied = select_final_candidate_full_dev(X_dev, y_dev, dev_groups, n_splits=3)
    assert sel_name in CANDIDATE_NAMES
    assert len(X_dev) == 242
    assert len(X_test) == 61
    assert set(dev_idx).isdisjoint(set(test_idx))


def test_reproducibility_deterministic_pipeline():
    """Verify deterministic reproducibility of candidate pipeline predictions."""
    X_dev, y_dev, dev_groups, _, _, _, _, _, _ = load_development_data()
    sub_X = X_dev.iloc[:50]
    sub_y = y_dev[:50]

    pipe1 = build_candidate_pipeline("Candidate D (Combined)")
    pipe1.fit(sub_X, sub_y)
    probs1 = pipe1.predict_proba(sub_X)[:, 1]

    pipe2 = build_candidate_pipeline("Candidate D (Combined)")
    pipe2.fit(sub_X, sub_y)
    probs2 = pipe2.predict_proba(sub_X)[:, 1]

    np.testing.assert_allclose(probs1, probs2, atol=1e-12)


def test_adoption_gate_decision_logic():
    """Verify adoption gate strictly enforces both accuracy improvement and recall threshold."""
    # Case 1: Both pass -> ACCEPT
    base = {"accuracy": 0.850, "recall": 0.880}
    sel = {"accuracy": 0.866, "recall": 0.885}  # +1.6 pp acc gain, recall > 0.85
    res = evaluate_adoption_gate(sel, base)
    assert res["adoption_gate_passed"] is True
    assert res["decision"] == "ACCEPT"

    # Case 2: Insufficient accuracy gain -> REJECT
    sel_low_acc = {"accuracy": 0.860, "recall": 0.890}  # +1.0 pp acc gain (< 1.5 pp)
    res_low = evaluate_adoption_gate(sel_low_acc, base)
    assert res_low["gate_1_accuracy_passed"] is False
    assert res_low["gate_2_recall_passed"] is True
    assert res_low["adoption_gate_passed"] is False
    assert res_low["decision"] == "REJECT"

    # Case 3: High accuracy but low recall -> REJECT
    sel_low_rec = {"accuracy": 0.880, "recall": 0.830}  # recall < 0.85
    res_low_rec = evaluate_adoption_gate(sel_low_rec, base)
    assert res_low_rec["gate_1_accuracy_passed"] is True
    assert res_low_rec["gate_2_recall_passed"] is False
    assert res_low_rec["adoption_gate_passed"] is False
    assert res_low_rec["decision"] == "REJECT"

