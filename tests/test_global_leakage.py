import sys
from pathlib import Path
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.advanced_model_search import load_dev_data

def test_global_stratified_group_kfold_no_overlap():
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, file_hash = load_dev_data()
    
    outer_cv = StratifiedGroupKFold(n_splits=5)
    
    for fold_i, (train_idx, val_idx) in enumerate(outer_cv.split(X_dev, y_dev, groups=dev_groups)):
        train_groups = set(dev_groups[train_idx])
        val_groups = set(dev_groups[val_idx])
        
        overlap = train_groups.intersection(val_groups)
        assert len(overlap) == 0, f"Outer group leakage in fold {fold_i}! Overlap: {overlap}"
        
        inner_cv = StratifiedGroupKFold(n_splits=5)
        X_tr, y_tr, g_tr = X_dev.iloc[train_idx], y_dev[train_idx], dev_groups[train_idx]
        
        for inner_fold_i, (i_tr_idx, i_val_idx) in enumerate(inner_cv.split(X_tr, y_tr, groups=g_tr)):
            inner_train_groups = set(g_tr[i_tr_idx])
            inner_val_groups = set(g_tr[i_val_idx])
            
            inner_overlap = inner_train_groups.intersection(inner_val_groups)
            assert len(inner_overlap) == 0, f"Inner group leakage! Overlap: {inner_overlap}"
            
            outer_val_indices = set(val_idx)
            mapped_i_tr_idx = set(train_idx[i_tr_idx])
            mapped_i_val_idx = set(train_idx[i_val_idx])
            
            assert len(mapped_i_tr_idx.intersection(outer_val_indices)) == 0, "Inner train uses outer val data!"
            assert len(mapped_i_val_idx.intersection(outer_val_indices)) == 0, "Inner val uses outer val data!"

if __name__ == "__main__":
    test_global_stratified_group_kfold_no_overlap()
    print("All global leakage tests passed successfully!")
