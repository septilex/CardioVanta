import json
import pandas as pd
import numpy as np
import ast
import os
from pathlib import Path
from sklearn.model_selection import StratifiedGroupKFold
from src.config.config import BASE_DIR, RAW_DATA_PATH, load_schema

def test_phase4b_no_test_set_construction():
    phase4b_path = BASE_DIR / "src" / "experiment" / "phase4b.py"
    with open(phase4b_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    tree = ast.parse(content)
    called_get_train_test_split = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "get_train_test_split":
                called_get_train_test_split = True
    
    assert not called_get_train_test_split, "Test set was constructed!"
    assert "dev_indices.json" in content, "Must use frozen dev split"

def test_no_production_artifacts():
    import glob
    def get_artifacts():
        files = set()
        for ext in ["*.pkl", "*.joblib"]:
            files.update(glob.glob(str(BASE_DIR / "**" / ext), recursive=True))
        return {f for f in files if "venv" not in f}
        
    before_artifacts = get_artifacts()
    from src.experiment.phase4b import run_phase4b
    run_phase4b()
    after_artifacts = get_artifacts()
    new_artifacts = after_artifacts - before_artifacts
    assert len(new_artifacts) == 0, f"Created production artifacts: {new_artifacts}"

def test_subgroup_counts_reconcile():
    sg_file = BASE_DIR / "reports" / "phase4b_subgroup_summary.json"
    with open(sg_file, "r") as f:
        data = json.load(f)
        
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        expected_total = len(json.load(f))
        
    axis_totals = {}
    for sg in data["subgroups"]:
        axis = sg["axis"]
        if axis not in axis_totals:
            axis_totals[axis] = 0
        axis_totals[axis] += sg["sample_count"]
        
        if sg["analysis_status"] == "Estimable":
            assert sg["positive_count"] >= data["minimum_class_size"]
            assert sg["negative_count"] >= data["minimum_class_size"]
            assert sg["sample_count"] >= data["minimum_subgroup_size"]
            assert np.isfinite(sg["roc_auc"])
            assert 0 <= sg["thresholds"]["youden_j"]["precision"] <= 1
            assert 0 <= sg["thresholds"]["youden_j"]["recall"] <= 1
            assert 0 <= sg["thresholds"]["youden_j"]["specificity"] <= 1
            assert 0 <= sg["thresholds"]["youden_j"]["f1"] <= 1
            assert sg["positive_count"] + sg["negative_count"] == sg["sample_count"]
        else:
            assert sg["reason"] != ""
            assert "roc_auc" not in sg
            
    for axis, total in axis_totals.items():
        assert total == expected_total, f"Axis {axis} sums to {total} instead of {expected_total}"

def test_resampling_validity_and_disjointness():
    res_file = BASE_DIR / "reports" / "phase4b_resampling_summary.json"
    with open(res_file, "r") as f:
        data = json.load(f)
        
    assert "bootstrap" in data["method"].lower()
    assert "n=300" in data["method"]
    
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
    n_dev = len(dev_idx)
    all_dev_ids_range = set(range(n_dev))
    
    raw_records = data["raw"]
    assert len(raw_records) == 300
    assert [r["repetition"] for r in raw_records] == list(range(1, 301))
    
    estimable_count = 0
    non_estimable_count = 0
    
    for r in raw_records:
        unique_boot = set(r["unique_bootstrap_ids"])
        oob = set(r["oob_ids"])
        
        # Core OOB Disjointness Validations
        assert len(unique_boot.intersection(oob)) == 0, "Leakage: Overlap between unique boot and OOB"
        assert unique_boot.union(oob) == all_dev_ids_range, "Union of boot and OOB does not cover all dev IDs"
        
        if r["estimable"]:
            estimable_count += 1
            assert np.isfinite(r["roc_auc"])
            assert 0.0 <= r["roc_auc"] <= 1.0
            assert len(oob) > 0
        else:
            non_estimable_count += 1
            assert "reason" in r
            
    assert estimable_count + non_estimable_count == 300
    assert estimable_count == data["estimable_repetitions"]
    assert non_estimable_count == data["non_estimable_repetitions"]
    
    agg = data["aggregation"]
    for m in ["roc_auc", "brier_score", "log_loss"]:
        if m in agg:
            assert agg[m]["p025"] <= agg[m]["median"] <= agg[m]["p975"]
            assert agg[m]["min"] <= agg[m]["mean"] <= agg[m]["max"]


def test_duplicate_aware_calibration():
    # DIRECTLY TEST THE REAL DUPLICATE-AWARE CALIBRATION PATH
    import pandas as pd
    import numpy as np
    from src.experiment.phase4b import fit_calibrated_model, _build_calibration_splits
    from src.config.config import RAW_DATA_PATH, load_schema
    import json
    from pathlib import Path
    
    dev_idx_path = Path("data/processed/dev_indices.json")
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    X_full = df.drop(columns=[schema["target_column"]])
    y_full = df[schema["target_column"]].to_numpy()
    
    X_dev = X_full.loc[dev_idx].reset_index(drop=True)
    y_dev = y_full[dev_idx]
    
    pos_idx = np.where(y_dev == 1)[0][:5]
    neg_idx = np.where(y_dev == 0)[0][:5]
    base_idx = np.concatenate([pos_idx, neg_idx])
    
    X_base = X_dev.iloc[base_idx].reset_index(drop=True)
    y_base = y_dev[base_idx]
    original_ids = np.arange(10)
    
    boot_indices = [0, 1, 2, 2, 3, 4, 5, 5, 5, 6, 7, 8, 9]
    X_boot = X_base.iloc[boot_indices].reset_index(drop=True)
    y_boot = y_base[boot_indices]
    boot_groups = original_ids[boot_indices]
    
    cal_cv = 3
    cal_method = 'sigmoid'
    
    # Verify exact calibration split construction using internal helper
    splits = _build_calibration_splits(X_boot, y_boot, boot_groups, cal_cv)
    val_folds = {gid: [] for gid in np.unique(boot_groups)}
    
    fold_idx = 0
    for train_idx, val_idx in splits:
        train_groups = set(boot_groups[train_idx])
        val_groups = set(boot_groups[val_idx])
        assert len(train_groups.intersection(val_groups)) == 0, "Leakage detected: train and val groups overlap!"
        for gid in val_groups:
            val_folds[gid].append(fold_idx)
        fold_idx += 1
        
    # Verify every original ID appears in exactly one validation fold
    for gid, folds in val_folds.items():
        assert len(folds) == 1, f"Group {gid} appears in {len(folds)} validation folds!"
        
    # Call the real production path
    model = fit_calibrated_model(X_boot, y_boot, cal_method, cal_cv, groups=boot_groups)
    
    # Verify the returned model fits and predicts proba
    probs = model.predict_proba(X_boot)
    assert probs.shape == (len(X_boot), 2)
    assert np.all((probs >= 0) & (probs <= 1))

def test_bootstrap_oob_integrity():
    # Verify bootstrap OOB Integrity
    # It must be that unique_bootstrap_ids & oob_ids == empty
    # And unique_bootstrap_ids | oob_ids == all development IDs
    import json
    from pathlib import Path
    reports_dir = Path("reports")
    summary_path = reports_dir / "phase4b_resampling_summary.json"
    
    if summary_path.exists():
        with open(summary_path, "r") as f:
            data = json.load(f)
            
        raw_list = data.get("raw", data) if isinstance(data, dict) else data
        if not raw_list:
            return
            
        dev_idx_path = Path("data/processed/dev_indices.json")
        with open(dev_idx_path, "r") as f:
            dev_idx = json.load(f)
        expected_dev_ids = set(range(len(dev_idx)))
        
        for res in raw_list:
            if not res.get("estimable", False):
                continue
                
            boot_ids = set(res["unique_bootstrap_ids"])
            oob_ids = set(res["oob_ids"])
            
            # Intersection is empty
            assert len(boot_ids.intersection(oob_ids)) == 0
            
            # Union is all development IDs
            assert boot_ids.union(oob_ids) == expected_dev_ids

def test_duplicate_audit():
    import pandas as pd
    import json
    from pathlib import Path
    from src.config.config import RAW_DATA_PATH
    
    df = pd.read_csv(RAW_DATA_PATH)
    dupes = df[df.duplicated(keep=False)]
    assert len(dupes) == 2
    assert 163 in dupes.index
    assert 164 in dupes.index
    
    dev_idx_path = Path("data/processed/dev_indices.json")
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    assert 163 in dev_idx
    assert 164 in dev_idx
def test_perturbation_validity():
    pert_file = BASE_DIR / "reports" / "phase4b_perturbation_summary.json"
    with open(pert_file, "r") as f:
        data = json.load(f)
        
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
    dev_total = len(dev_idx)
        
    for res in data["results"]:
        assert res["mean_abs_prob_change"] >= 0
        assert "direction" in res
        
        flip_rate = res.get("youden_j_flip_rate", 0)
        assert 0.0 <= flip_rate <= 1.0
        
        flips = res.get("youden_j_flips", 0)
        assert isinstance(flips, int)
        assert flips >= 0
        
        assert 0 <= res["baseline_mean_prob"] <= 1
        assert 0 <= res["perturbed_mean_prob"] <= 1
        
        if "range" in res["direction"]:
            assert "derived_dev_min" in res
            assert "derived_dev_max" in res
            assert res["derived_dev_min"] <= res["derived_dev_max"]
            assert "magnitude_before_clip" in res
            assert flips <= dev_total
        elif "shift" in res["direction"]:
            assert "affected_count" in res
            assert res["affected_count"] <= dev_total
            assert flips <= res["affected_count"]

def test_ai_dependency_isolation():
    phase4b_path = BASE_DIR / "src" / "experiment" / "phase4b.py"
    with open(phase4b_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    tree = ast.parse(content)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
            
    for imp in imports:
        if imp:
            assert "openai" not in imp.lower()
            assert "anthropic" not in imp.lower()
            assert "gemini" not in imp.lower()
            assert "google.generativeai" not in imp.lower()
            
    req_path = BASE_DIR / "requirements.txt"
    if req_path.exists():
        with open(req_path, "r") as f:
            reqs = f.read().lower()
        assert "openai" not in reqs
        assert "anthropic" not in reqs
        assert "gemini" not in reqs

def test_oof_alignment():
    oof_file = BASE_DIR / "reports" / "phase4a_oof_predictions.csv"
    oof_df = pd.read_csv(oof_file)
    
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    y_full = df[schema["target_column"]].to_numpy()
    y_train = y_full[dev_idx]
    
    assert len(oof_df) == len(dev_idx)
    assert np.all(oof_df["original_sample_index"].values == np.array(dev_idx))
    assert np.all(oof_df["true_label"].values == y_train)
    assert len(oof_df["original_sample_index"].unique()) == len(dev_idx)

def test_missing_subgroup_figure():
    fig_path = BASE_DIR / "reports" / "figures" / "phase4b_subgroup_sensitivity.png"
    assert fig_path.exists(), "Subgroup sensitivity figure missing"
