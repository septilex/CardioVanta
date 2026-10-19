"""
Tests for Next Research Phase (High-Accuracy Investigation)
===========================================================
Validates:
1. Complete isolation of the 61-sample locked test partition.
2. Group-level cross-validation isolation (zero duplicate group leakage).
3. Candidate 4 (Oldpeak Quadratic + Tuned Regularization) deterministic reproducibility.
4. Exact preservation of production artifacts.
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
from experiments.next_research_phase_90pct import build_candidates, evaluate_all
from scripts.verify_artifact_integrity import verify_artifacts


def test_locked_test_isolation_in_results():
    """Verify that the research experiment evaluated zero locked-test samples."""
    results_path = PROJECT_ROOT / "experiments" / "results" / "next_research_phase_90pct.json"
    assert results_path.exists(), "Results JSON was not generated"

    with open(results_path, "r") as f:
        data = json.load(f)

    assert data["dev_samples"] == 242
    assert data["locked_test_samples_used"] == 0
    assert "target_reached" in data


def test_duplicate_group_kfold_no_overlap():
    """Verify that StratifiedGroupKFold prevents identical duplicate patients from bridging folds."""
    X_dev, y_dev, dev_groups, _, _, _, _, _, _ = load_dev_data()
    assert len(X_dev) == 242
    assert len(np.unique(dev_groups)) == 241

    cv = StratifiedGroupKFold(n_splits=5)
    for fold_i, (tr_idx, val_idx) in enumerate(cv.split(X_dev, y_dev, groups=dev_groups)):
        tr_g = set(dev_groups[tr_idx])
        val_g = set(dev_groups[val_idx])
        overlap = tr_g.intersection(val_g)
        assert len(overlap) == 0, f"Fold {fold_i} has group leakage: {overlap}"


def test_best_candidate_metrics_reproducibility():
    """Verify that Candidate 4 reproduces exact accuracy (86.36%) and recall (90.15%)."""
    results_path = PROJECT_ROOT / "experiments" / "results" / "next_research_phase_90pct.json"
    with open(results_path, "r") as f:
        data = json.load(f)

    best_name = data["best_candidate"]
    best_cand = data["candidates"][best_name]

    assert best_cand["accuracy"] == pytest.approx(0.863636, abs=1e-3)
    assert best_cand["recall"] == pytest.approx(0.901515, abs=1e-3)
    assert best_cand["correct_samples"] == 209
    assert best_cand["total_samples"] == 242


def test_production_artifacts_untouched():
    """Verify that the production manifest and model files remain 100% authentic."""
    manifest_file = PROJECT_ROOT / "configs" / "artifact_hashes.json"
    assert verify_artifacts(str(manifest_file), PROJECT_ROOT) is True


def test_nested_cv_results_isolation_and_structure():
    """Verify that the nested CV evaluation strictly evaluated 242 dev samples with 0 locked test samples."""
    nested_path = PROJECT_ROOT / "experiments" / "results" / "nested_cv_90pct_results.json"
    assert nested_path.exists(), "Nested CV results JSON does not exist"

    with open(nested_path, "r") as f:
        data = json.load(f)

    assert data["dev_samples"] == 242
    assert data["locked_test_samples_used"] == 0
    assert data["target_reached"] is False
    assert "research_history_limitation" in data
    assert len(data["research_history_limitation"]) > 20


def test_nested_cv_inner_outer_group_isolation():
    """Verify that both outer and inner CV loops enforce strict duplicate patient group isolation."""
    X_dev, y_dev, dev_groups, _, _, _, _, _, _ = load_dev_data()
    outer_cv = StratifiedGroupKFold(n_splits=5)

    for o_fold, (tr_idx, val_idx) in enumerate(outer_cv.split(X_dev, y_dev, groups=dev_groups)):
        # Outer group isolation
        o_tr_groups = set(dev_groups[tr_idx])
        o_val_groups = set(dev_groups[val_idx])
        assert len(o_tr_groups.intersection(o_val_groups)) == 0, f"Outer fold {o_fold} leaked groups"

        # Inner group isolation
        g_tr = dev_groups[tr_idx]
        X_tr = X_dev.iloc[tr_idx].reset_index(drop=True)
        y_tr = y_dev[tr_idx]
        inner_cv = StratifiedGroupKFold(n_splits=5)

        for i_fold, (in_tr_idx, in_val_idx) in enumerate(inner_cv.split(X_tr, y_tr, groups=g_tr)):
            in_tr_groups = set(g_tr[in_tr_idx])
            in_val_groups = set(g_tr[in_val_idx])
            assert len(in_tr_groups.intersection(in_val_groups)) == 0, (
                f"Outer fold {o_fold}, inner fold {i_fold} leaked groups"
            )


def test_nested_cv_pooled_metrics_integrity():
    """Verify honest nested CV pooled out-of-fold metrics and comparison with baseline."""
    nested_path = PROJECT_ROOT / "experiments" / "results" / "nested_cv_90pct_results.json"
    with open(nested_path, "r") as f:
        data = json.load(f)

    nested = data["nested_evaluation"]["nested_selection_procedure"]["pooled_outer_metrics"]
    base = data["nested_evaluation"]["authoritative_baseline"]["pooled_outer_metrics"]
    comp = data["nested_evaluation"]["comparison_vs_baseline"]

    assert nested["total_samples"] == 242
    assert nested["correct_samples"] == 203
    assert nested["accuracy"] == pytest.approx(203 / 242, abs=1e-5)
    assert nested["recall"] == pytest.approx(114 / 132, abs=1e-5)
    assert nested["confusion_matrix"]["tp"] == 114
    assert nested["confusion_matrix"]["fn"] == 18

    assert base["total_samples"] == 242
    assert base["correct_samples"] == 207
    assert base["accuracy"] == pytest.approx(207 / 242, abs=1e-5)
    assert base["recall"] == pytest.approx(117 / 132, abs=1e-5)

    assert comp["correct_samples_diff"] == -4
    assert comp["accuracy_diff"] < 0  # Proves nested selection procedure does not beat baseline


def test_candidate_selection_strictly_inner():
    """Verify that candidate selection in each fold was strictly driven by inner folds without outer leakage."""
    nested_path = PROJECT_ROOT / "experiments" / "results" / "nested_cv_90pct_results.json"
    with open(nested_path, "r") as f:
        data = json.load(f)

    outer_folds = data["nested_evaluation"]["nested_selection_procedure"]["outer_folds"]
    assert len(outer_folds) == 5

    for fold in outer_folds:
        selected = fold["selected_candidate"]
        inner_winner = fold["inner_selection_metrics"]["name"]
        # The selected candidate must be identical to the top inner candidate
        assert selected == inner_winner
        # Verify inner ranking order
        top_cand = fold["all_inner_candidates"][0]
        assert top_cand["name"] == selected

