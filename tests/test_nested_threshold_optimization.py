"""
Tests for Nested Threshold Optimisation Investigation
======================================================
Validates:
1. Complete isolation of the 61-sample locked test partition.
2. Group-level cross-validation isolation (zero duplicate group leakage in outer and inner folds).
3. Threshold selection provenance (thresholds selected strictly on inner folds).
4. Reproducibility of nested threshold evaluation results.
5. Exact preservation of production artifacts.
"""

import sys
import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.model_selection import StratifiedGroupKFold

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.advanced_model_search import load_dev_data
from scripts.verify_artifact_integrity import verify_artifacts


def test_locked_test_isolation_in_threshold_results():
    """Verify that the threshold experiment evaluated zero locked-test samples."""
    results_path = PROJECT_ROOT / "experiments" / "results" / "nested_threshold_optimization.json"
    assert results_path.exists(), "Results JSON was not generated"

    with open(results_path, "r") as f:
        data = json.load(f)

    assert data["dev_samples"] == 242
    assert data["locked_test_samples_used"] == 0
    assert data["target_reached"] is False
    assert "research_history_limitation" in data
    assert len(data["selected_thresholds"]) == 5


def test_threshold_splits_group_isolation():
    """Verify that StratifiedGroupKFold prevents identical duplicate patients from bridging folds."""
    X_dev, y_dev, dev_groups, _, _, _, _, _, _ = load_dev_data()
    assert len(X_dev) == 242
    assert len(np.unique(dev_groups)) == 241

    outer_cv = StratifiedGroupKFold(n_splits=5)
    for fold_i, (tr_idx, val_idx) in enumerate(outer_cv.split(X_dev, y_dev, groups=dev_groups)):
        tr_g = set(dev_groups[tr_idx])
        val_g = set(dev_groups[val_idx])
        overlap = tr_g.intersection(val_g)
        assert len(overlap) == 0, f"Outer fold {fold_i} has group leakage: {overlap}"

        # Inner fold group isolation
        g_tr = dev_groups[tr_idx]
        X_tr = X_dev.iloc[tr_idx].reset_index(drop=True)
        y_tr = y_dev[tr_idx]
        inner_cv = StratifiedGroupKFold(n_splits=5)

        for in_fold_i, (in_tr_idx, in_val_idx) in enumerate(inner_cv.split(X_tr, y_tr, groups=g_tr)):
            in_tr_g = set(g_tr[in_tr_idx])
            in_val_g = set(g_tr[in_val_idx])
            in_overlap = in_tr_g.intersection(in_val_g)
            assert len(in_overlap) == 0, f"Inner fold {in_fold_i} has group leakage: {in_overlap}"


def test_threshold_selection_strictly_inner():
    """Verify that every threshold was selected strictly from inner folds meeting recall >= 0.85."""
    results_path = PROJECT_ROOT / "experiments" / "results" / "nested_threshold_optimization.json"
    with open(results_path, "r") as f:
        data = json.load(f)

    outer_folds = data["evaluation_results"]["threshold_tuned_procedure"]["outer_folds"]
    assert len(outer_folds) == 5

    for fold in outer_folds:
        selected_t = fold["selected_threshold"]
        inner_metrics = fold["inner_selection_metrics"]
        assert selected_t == inner_metrics["threshold"]
        assert inner_metrics["recall"] >= 0.85
        assert inner_metrics["meets_recall_constraint"] is True


def test_threshold_metrics_reproducibility():
    """Verify exact out-of-fold accuracy, recall, and baseline comparison."""
    results_path = PROJECT_ROOT / "experiments" / "results" / "nested_threshold_optimization.json"
    with open(results_path, "r") as f:
        data = json.load(f)

    tuned = data["evaluation_results"]["threshold_tuned_procedure"]["pooled_outer_metrics"]
    base = data["evaluation_results"]["authoritative_baseline_fixed_0_50"]["pooled_outer_metrics"]
    comp = data["evaluation_results"]["comparison_vs_baseline"]

    assert tuned["total_samples"] == 242
    assert tuned["correct_samples"] == 206
    assert tuned["accuracy"] == pytest.approx(206 / 242, abs=1e-5)
    assert tuned["recall"] == pytest.approx(117 / 132, abs=1e-5)

    assert base["total_samples"] == 242
    assert base["correct_samples"] == 207
    assert base["accuracy"] == pytest.approx(207 / 242, abs=1e-5)
    assert base["recall"] == pytest.approx(117 / 132, abs=1e-5)

    assert comp["correct_samples_diff"] == -1
    assert comp["accuracy_diff"] < 0  # Threshold tuning did not beat baseline


def test_production_artifacts_untouched():
    """Verify that the production manifest and model files remain 100% authentic."""
    manifest_file = PROJECT_ROOT / "configs" / "artifact_hashes.json"
    assert verify_artifacts(str(manifest_file), PROJECT_ROOT) is True
