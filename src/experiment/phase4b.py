import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score, average_precision_score, brier_score_loss, log_loss
from sklearn.calibration import CalibratedClassifierCV, CalibrationDisplay
from sklearn.linear_model import LogisticRegression
from sklearn.utils import resample
from sklearn.model_selection import StratifiedGroupKFold

from src.config.config import RAW_DATA_PATH, load_schema, RANDOM_SEED, BASE_DIR
from src.preprocessing.preprocessor import PreprocessingFactory

# Parameters
BOOTSTRAP_REPETITIONS = 300
MIN_SUBGROUP_SIZE = 20
MIN_CLASS_SIZE = 5
TEST_SET_DISCLAIMER = "The locked 20% test observations were not used for training, calibration, threshold selection, robustness analysis, subgroup analysis, or evaluation."

def get_authoritative_config():
    p3_file = BASE_DIR / "reports" / "phase3_calibration_results.json"
    p4a_file = BASE_DIR / "reports" / "phase4a_threshold_analysis.json"
    
    with open(p3_file, "r") as f:
        p3_data = json.load(f)
        
    with open(p4a_file, "r") as f:
        p4a_data = json.load(f)
        
    cal_method = p3_data["selected_method"]
    cal_cv = p3_data["calibration_cv"]
    candidates = p4a_data["candidates"]
    
    return cal_method, cal_cv, candidates

def get_base_pipeline():
    factory = PreprocessingFactory()
    base_params = {'C': 0.1, 'class_weight': 'balanced', 'solver': 'lbfgs', 'random_state': RANDOM_SEED}
    return Pipeline([
        ('preprocessor', factory.get_preprocessing_pipeline('linear')),
        ('model', LogisticRegression(**base_params))
    ])

def _build_calibration_splits(X, y, groups, cal_cv):
    sgkf = StratifiedGroupKFold(n_splits=cal_cv)
    return list(sgkf.split(X, y, groups=groups))

def fit_calibrated_model(X_train, y_train, cal_method, cal_cv, groups=None):
    base_pipe = get_base_pipeline()
    if cal_method == 'uncalibrated':
        base_pipe.fit(X_train, y_train)
        return base_pipe
    else:
        if groups is not None:
            # Duplicate-aware explicit calibration splits
            splits = _build_calibration_splits(X_train, y_train, groups, cal_cv)
            cal_clf = CalibratedClassifierCV(estimator=base_pipe, method=cal_method, cv=splits)
        else:
            cal_clf = CalibratedClassifierCV(estimator=base_pipe, method=cal_method, cv=cal_cv)
            
        cal_clf.fit(X_train, y_train)
        return cal_clf

def calculate_all_metrics(y_true, y_prob, thresholds_dict):
    metrics = {}
    unique_classes = np.unique(y_true)
    
    if len(unique_classes) == 2:
        metrics['roc_auc'] = float(roc_auc_score(y_true, y_prob))
        metrics['avg_precision'] = float(average_precision_score(y_true, y_prob))
        metrics['brier_score'] = float(brier_score_loss(y_true, y_prob))
        metrics['log_loss'] = float(log_loss(y_true, y_prob))
        metrics['estimable'] = True
    else:
        metrics['estimable'] = False
        metrics['reason'] = "Not estimable: Requires both target classes in sample."
        return metrics

    metrics['thresholds'] = {}
    for cand_name, cand_data in thresholds_dict.items():
        t = cand_data['threshold']
        y_pred = (y_prob >= t).astype(int)
        
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        
        accuracy = (tp + tn) / len(y_true)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        balanced_accuracy = (recall + specificity) / 2
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        metrics['thresholds'][cand_name] = {
            "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "specificity": float(specificity),
            "f1": float(f1),
            "balanced_accuracy": float(balanced_accuracy),
            "fpr": float(fpr),
            "fnr": float(fnr)
        }
    return metrics

def run_resampling_robustness(X_train, y_train, cal_method, cal_cv, candidates, dev_groups):
    np.random.seed(RANDOM_SEED)
    results = []
    
    n_samples = len(X_train)
    indices = np.arange(n_samples)
    
    estimable_counts = {'overall': 0, 'non_estimable': 0}
    
    for i in range(BOOTSTRAP_REPETITIONS):
        boot_idx = resample(indices, replace=True, n_samples=n_samples, random_state=RANDOM_SEED+i)
        boot_groups = dev_groups[boot_idx]
        oob_idx = np.array(list(set(indices) - set(boot_idx)))
        
        base_res = {
            "repetition": i+1,
            "unique_bootstrap_ids": [int(x) for x in set(boot_idx)],
            "oob_ids": [int(x) for x in oob_idx]
        }
        
        if len(oob_idx) == 0:
            base_res["estimable"] = False
            base_res["reason"] = "No OOB samples"
            results.append(base_res)
            estimable_counts['non_estimable'] += 1
            continue
            
        y_oob = y_train[oob_idx]
        if len(np.unique(y_oob)) < 2:
            base_res["estimable"] = False
            base_res["reason"] = "OOB sample missing target class"
            results.append(base_res)
            estimable_counts['non_estimable'] += 1
            continue
            
        X_boot = X_train.iloc[boot_idx]
        y_boot = y_train[boot_idx]
        
        if len(np.unique(y_boot)) < 2:
            base_res["estimable"] = False
            base_res["reason"] = "Bootstrap sample missing target class"
            results.append(base_res)
            estimable_counts['non_estimable'] += 1
            continue
            
        # Duplicate-aware explicit calibration splits
        model = fit_calibrated_model(X_boot, y_boot, cal_method, cal_cv, groups=boot_groups)
        y_prob = model.predict_proba(X_train.iloc[oob_idx])[:, 1]
        
        m = calculate_all_metrics(y_oob, y_prob, candidates)
        m.update(base_res)
        results.append(m)
        if m['estimable']:
            estimable_counts['overall'] += 1
        else:
            estimable_counts['non_estimable'] += 1
        
    agg = {}
    valid_results = [r for r in results if r.get('estimable', False)]
    
    metric_keys = ['roc_auc', 'avg_precision', 'brier_score', 'log_loss']
    for k in metric_keys:
        vals = [r[k] for r in valid_results]
        agg[k] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "median": float(np.median(vals)),
            "p025": float(np.percentile(vals, 2.5)),
            "p975": float(np.percentile(vals, 97.5)),
            "min": float(np.min(vals)),
            "max": float(np.max(vals))
        }
        
    for cand_name in candidates.keys():
        agg[cand_name] = {}
        t_keys = ['accuracy', 'precision', 'recall', 'specificity', 'f1', 'balanced_accuracy']
        for tk in t_keys:
            vals = [r['thresholds'][cand_name][tk] for r in valid_results]
            agg[cand_name][tk] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "median": float(np.median(vals)),
                "p025": float(np.percentile(vals, 2.5)),
                "p975": float(np.percentile(vals, 97.5)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals))
            }
            
    return results, agg, estimable_counts

def run_subgroup_analysis(X_train, y_train, oof_probs, candidates, figures_dir):
    subgroups = []
    
    axes = ['sex', 'cp', 'fbs', 'restecg', 'exang', 'slope', 'ca', 'thal']
    X_ext = X_train.copy()
    X_ext['age_band'] = pd.cut(X_ext['age'], bins=[0, 45, 60, 150], labels=['<=45', '46-60', '>60'], right=True)
    axes.append('age_band')
    
    for axis in axes:
        unique_vals = X_ext[axis].dropna().unique()
        for val in unique_vals:
            mask = (X_ext[axis] == val)
            sg_X = X_ext[mask]
            sg_y = y_train[mask]
            sg_probs = oof_probs[mask]
            
            n_total = len(sg_y)
            n_pos = int(np.sum(sg_y == 1))
            n_neg = int(np.sum(sg_y == 0))
            
            sg_res = {
                "axis": axis,
                "value": str(val),
                "sample_count": n_total,
                "positive_count": n_pos,
                "negative_count": n_neg,
                "analysis_status": "Estimable",
                "reason": ""
            }
            
            if axis == 'age_band':
                sg_res["note"] = "These are exploratory dataset-analysis bins and are not clinical age thresholds."
            
            if n_total < MIN_SUBGROUP_SIZE:
                sg_res["analysis_status"] = "Not estimable"
                sg_res["reason"] = f"Total size ({n_total}) < {MIN_SUBGROUP_SIZE}"
            elif n_pos < MIN_CLASS_SIZE or n_neg < MIN_CLASS_SIZE:
                sg_res["analysis_status"] = "Not estimable"
                sg_res["reason"] = f"Class size (pos={n_pos}, neg={n_neg}) < {MIN_CLASS_SIZE}"
            else:
                m = calculate_all_metrics(sg_y, sg_probs, candidates)
                if not m["estimable"]:
                    sg_res["analysis_status"] = "Not estimable"
                    sg_res["reason"] = m["reason"]
                else:
                    sg_res.update(m)
                    
                    fig, ax = plt.subplots(figsize=(6, 4))
                    CalibrationDisplay.from_predictions(sg_y, sg_probs, n_bins=5, ax=ax, name=f"Subgroup {axis}={val}")
                    plt.title(f"Calibration Curve: {axis}={val} (Dev OOF)")
                    plt.tight_layout()
                    safe_val = str(val).replace('>', 'gt_').replace('<', 'lt_').replace('=', 'eq_')
                    plt.savefig(figures_dir / f"phase4b_subgroup_calib_{axis}_{safe_val}.png")
                    plt.close()
                
            subgroups.append(sg_res)
            
    return subgroups

def run_perturbation_analysis(X_train, y_train, model, schema, candidates):
    base_probs = model.predict_proba(X_train)[:, 1]
    results = []
    
    features = schema['features']
    
    for feat in features:
        col = feat['name']
        if col not in X_train.columns:
            continue
            
        f_type = feat.get('type')
        if f_type == 'continuous':
            dev_min = X_train[col].min()
            dev_max = X_train[col].max()
            dev_range = dev_max - dev_min
            
            shift_pos = dev_range * 0.05
            X_pert_pos = X_train.copy()
            X_pert_pos[col] = np.clip(X_pert_pos[col] + shift_pos, dev_min, dev_max)
            pert_probs_pos = model.predict_proba(X_pert_pos)[:, 1]
            diff_pos = pert_probs_pos - base_probs
            
            res_pos = {
                "feature": col,
                "direction": "+5% dev range",
                "magnitude_before_clip": float(shift_pos),
                "derived_dev_min": float(dev_min),
                "derived_dev_max": float(dev_max),
                "mean_abs_prob_change": float(np.mean(np.abs(diff_pos))),
                "mean_prob_change": float(np.mean(diff_pos)),
                "baseline_mean_prob": float(np.mean(base_probs)),
                "perturbed_mean_prob": float(np.mean(pert_probs_pos)),
            }
            for cand_name, cand_data in candidates.items():
                t = cand_data['threshold']
                base_pred = (base_probs >= t).astype(int)
                pert_pred = (pert_probs_pos >= t).astype(int)
                flips = np.sum(base_pred != pert_pred)
                res_pos[f"{cand_name}_flips"] = int(flips)
                res_pos[f"{cand_name}_flip_rate"] = float(flips / len(X_train)) # Full dev count
            results.append(res_pos)
            
            shift_neg = dev_range * 0.05
            X_pert_neg = X_train.copy()
            X_pert_neg[col] = np.clip(X_pert_neg[col] - shift_neg, dev_min, dev_max)
            pert_probs_neg = model.predict_proba(X_pert_neg)[:, 1]
            diff_neg = pert_probs_neg - base_probs
            
            res_neg = {
                "feature": col,
                "direction": "-5% dev range",
                "magnitude_before_clip": float(shift_neg),
                "derived_dev_min": float(dev_min),
                "derived_dev_max": float(dev_max),
                "mean_abs_prob_change": float(np.mean(np.abs(diff_neg))),
                "mean_prob_change": float(np.mean(diff_neg)),
                "baseline_mean_prob": float(np.mean(base_probs)),
                "perturbed_mean_prob": float(np.mean(pert_probs_neg)),
            }
            for cand_name, cand_data in candidates.items():
                t = cand_data['threshold']
                base_pred = (base_probs >= t).astype(int)
                pert_pred = (pert_probs_neg >= t).astype(int)
                flips = np.sum(base_pred != pert_pred)
                res_neg[f"{cand_name}_flips"] = int(flips)
                res_neg[f"{cand_name}_flip_rate"] = float(flips / len(X_train)) # Full dev count
            results.append(res_neg)
            
        elif f_type in ['categorical', 'binary']:
            allowed = X_train[col].dropna().unique().tolist()
            if len(allowed) > 1:
                for orig_cat in allowed:
                    for target_cat in allowed:
                        if orig_cat == target_cat: continue
                        
                        mask = (X_train[col] == orig_cat)
                        affected_count = mask.sum()
                        if affected_count == 0: continue
                        
                        X_pert = X_train.copy()
                        X_pert.loc[mask, col] = target_cat
                        
                        base_probs_mask = base_probs[mask]
                        pert_probs_mask = model.predict_proba(X_pert[mask])[:, 1]
                        diff = pert_probs_mask - base_probs_mask
                        
                        res = {
                            "feature": col,
                            "direction": f"shift {orig_cat} -> {target_cat}",
                            "source_category": str(orig_cat),
                            "target_category": str(target_cat),
                            "affected_count": int(affected_count),
                            "mean_abs_prob_change": float(np.mean(np.abs(diff))),
                            "mean_prob_change": float(np.mean(diff)),
                            "baseline_mean_prob": float(np.mean(base_probs_mask)),
                            "perturbed_mean_prob": float(np.mean(pert_probs_mask)),
                        }
                        
                        for cand_name, cand_data in candidates.items():
                            t = cand_data['threshold']
                            base_pred = (base_probs_mask >= t).astype(int)
                            pert_pred = (pert_probs_mask >= t).astype(int)
                            flips = np.sum(base_pred != pert_pred)
                            res[f"{cand_name}_flips"] = int(flips)
                            res[f"{cand_name}_flip_rate"] = float(flips / affected_count)
                            
                        results.append(res)
                
    return results

def run_phase4b():
    print("Starting Phase 4B: Robustness and Subgroup Analysis...")
    reports_dir = BASE_DIR / "reports"
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
        
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    
    X_full = df.drop(columns=[schema["target_column"]])
    y_full = df[schema["target_column"]].to_numpy()
    
    X_train = X_full.loc[dev_idx].reset_index(drop=True)
    dev_groups = X_train.groupby(list(X_train.columns)).ngroup().values

    y_train = y_full[dev_idx]
    
    cal_method, cal_cv, candidates = get_authoritative_config()
    print(f"Loaded Phase 3 config: {cal_method} (cv={cal_cv})")
    
    print("Running bootstrap resampling...")
    resamp_raw, resamp_agg, counts = run_resampling_robustness(X_train, y_train, cal_method, cal_cv, candidates, dev_groups)
    
    with open(reports_dir / "phase4b_resampling_summary.json", "w") as f:
        json.dump({
            "note": f"Empirical resampling variability observed in the development data. These are resampling percentile ranges, not clinical confidence intervals. {TEST_SET_DISCLAIMER}",
            "method": f"Bootstrap resampling (n={BOOTSTRAP_REPETITIONS}) with duplicate-aware calibration.",
            "estimable_repetitions": counts['overall'],
            "non_estimable_repetitions": counts['non_estimable'],
            "aggregation": resamp_agg,
            "raw": resamp_raw
        }, f, indent=4)
        
    flat_resamp = []
    for r in resamp_raw:
        flat = {k: v for k, v in r.items() if not isinstance(v, dict) and k not in ['unique_bootstrap_ids', 'oob_ids']}
        if r.get('estimable', False):
            for c, cdata in r.get('thresholds', {}).items():
                for tk, tv in cdata.items():
                    flat[f"{c}_{tk}"] = tv
        flat_resamp.append(flat)
    pd.DataFrame(flat_resamp).to_csv(reports_dir / "phase4b_resampling_results.csv", index=False)
    
    print("Running subgroup analysis...")
    oof_df = pd.read_csv(reports_dir / "phase4a_oof_predictions.csv")
    oof_probs = oof_df['predicted_probability'].values
    assert np.all(oof_df['original_sample_index'].values == np.array(dev_idx))
    assert np.all(oof_df['true_label'].values == y_train)
    
    subgroups = run_subgroup_analysis(X_train, y_train, oof_probs, candidates, figures_dir)
    with open(reports_dir / "phase4b_subgroup_summary.json", "w") as f:
        json.dump({
            "note": f"Development OOF subgroup-specific estimates. Only reports observed descriptive difference. Not for ranking clinical subsets. {TEST_SET_DISCLAIMER}",
            "minimum_subgroup_size": MIN_SUBGROUP_SIZE,
            "minimum_class_size": MIN_CLASS_SIZE,
            "subgroups": subgroups
        }, f, indent=4)
        
    flat_sg = []
    for s in subgroups:
        flat = {k: v for k, v in s.items() if not isinstance(v, dict)}
        if s["analysis_status"] == "Estimable":
            for c, cdata in s.get('thresholds', {}).items():
                for tk, tv in cdata.items():
                    flat[f"{c}_{tk}"] = tv
        flat_sg.append(flat)
    pd.DataFrame(flat_sg).to_csv(reports_dir / "phase4b_subgroup_results.csv", index=False)
    
    print("Running perturbation analysis...")
    # NOTE: fit_calibrated_model uses base 5-fold CV without group awareness for the overall perturbation baseline,
    # because the development dataset itself does not contain deliberate identical duplicates like the bootstrap set.
    full_model = fit_calibrated_model(X_train, y_train, cal_method, cal_cv, groups=dev_groups)
    pert_results = run_perturbation_analysis(X_train, y_train, full_model, schema, candidates)
    
    with open(reports_dir / "phase4b_perturbation_summary.json", "w") as f:
        json.dump({
            "note": f"Input sensitivity analysis via controlled feature perturbation. Does not imply causal evidence or generalization robustness. {TEST_SET_DISCLAIMER}",
            "results": pert_results
        }, f, indent=4)
    pd.DataFrame(pert_results).to_csv(reports_dir / "phase4b_perturbation_results.csv", index=False)
    
    # Visualizations
    df_resamp = pd.DataFrame([r for r in resamp_raw if r.get('estimable', False)])
    for m in ['roc_auc', 'brier_score', 'log_loss', 'avg_precision']:
        if m in df_resamp.columns:
            plt.figure(figsize=(6, 4))
            plt.hist(df_resamp[m], bins=20, edgecolor='black', alpha=0.7)
            plt.axvline(np.mean(df_resamp[m]), color='red', linestyle='dashed', linewidth=2, label='Mean')
            plt.title(f'Bootstrap {m.upper()} Distribution (Development Resampling)')
            plt.xlabel(m)
            plt.ylabel('Frequency')
            plt.legend()
            plt.tight_layout()
            plt.savefig(figures_dir / f"phase4b_robustness_{m}.png")
            plt.close()
    
    sg_estimable = [s for s in subgroups if s['analysis_status'] == 'Estimable']
    if sg_estimable:
        labels = [f"{s['axis']}={s['value']}" for s in sg_estimable]
        f1s = [s['thresholds']['youden_j']['f1'] for s in sg_estimable]
        specs = [s['thresholds']['youden_j']['specificity'] for s in sg_estimable]
        sens = [s['thresholds']['youden_j']['recall'] for s in sg_estimable]
        
        plt.figure(figsize=(10, 6))
        plt.barh(labels, f1s, color='skyblue')
        plt.title('Subgroup Youden J F1 (Development Data)')
        plt.xlabel('F1 Score')
        plt.tight_layout()
        plt.savefig(figures_dir / "phase4b_subgroup_f1.png")
        plt.close()
        
        plt.figure(figsize=(10, 6))
        plt.barh(labels, specs, color='lightgreen')
        plt.title('Subgroup Specificity (Development Data)')
        plt.xlabel('Specificity')
        plt.tight_layout()
        plt.savefig(figures_dir / "phase4b_subgroup_specificity.png")
        plt.close()
        
        plt.figure(figsize=(10, 6))
        plt.barh(labels, sens, color='salmon')
        plt.title('Subgroup Sensitivity (Development Data)')
        plt.xlabel('Sensitivity (Recall)')
        plt.tight_layout()
        plt.savefig(figures_dir / "phase4b_subgroup_sensitivity.png")
        plt.close()
        
    df_pert = pd.DataFrame(pert_results)
    if not df_pert.empty:
        c_pert = df_pert[df_pert['direction'].str.contains('range', na=False)]
        if not c_pert.empty:
            # Probability response visualization
            features = c_pert['feature'].unique()
            x = np.arange(len(features))
            width = 0.25
            
            baseline = []
            pos_pert = []
            neg_pert = []
            
            for f in features:
                f_data = c_pert[c_pert['feature'] == f]
                b = f_data['baseline_mean_prob'].iloc[0]
                p_pos = f_data[f_data['direction'] == '+5% dev range']['perturbed_mean_prob'].iloc[0]
                p_neg = f_data[f_data['direction'] == '-5% dev range']['perturbed_mean_prob'].iloc[0]
                baseline.append(b)
                pos_pert.append(p_pos)
                neg_pert.append(p_neg)
                
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(x - width, neg_pert, width, label='-5% range', color='lightblue')
            ax.bar(x, baseline, width, label='Baseline', color='gray')
            ax.bar(x + width, pos_pert, width, label='+5% range', color='lightcoral')
            
            ax.set_ylabel('Mean Predicted Probability')
            ax.set_title('Continuous Feature Perturbation Response (Development Input Sensitivity Analysis)')
            ax.set_xticks(x)
            ax.set_xticklabels(features)
            ax.legend()
            plt.tight_layout()
            plt.savefig(figures_dir / "phase4b_continuous_prob_response.png")
            plt.close()

            # Flip rates
            plt.figure(figsize=(10, 6))
            plt.barh(c_pert['feature'] + " " + c_pert['direction'], c_pert['youden_j_flip_rate'], color='orange')
            plt.title('Continuous Perturbation Flip Rate (Youden J) (Development Analysis)')
            plt.xlabel('Flip Rate')
            plt.tight_layout()
            plt.savefig(figures_dir / "phase4b_continuous_flip_rate.png")
            plt.close()

        cat_pert = df_pert[df_pert['direction'].str.contains('shift', na=False)]
        if not cat_pert.empty:
            plt.figure(figsize=(12, 8))
            plt.barh(cat_pert['direction'], cat_pert['youden_j_flip_rate'], color='purple')
            plt.title('Categorical Perturbation Flip Rate (Youden J) (Development Analysis)')
            plt.xlabel('Flip Rate (of affected count)')
            plt.tight_layout()
            plt.savefig(figures_dir / "phase4b_categorical_flip_rate.png")
            plt.close()

    # Reporting
    print("\n--- PHASE 4B REQUIRED REPORTING NUMBERS ---\n")
    print("A. Bootstrap:")
    print(f"- 300 repetitions")
    print(f"- Estimable count: {counts['overall']}")
    print(f"- Non-estimable count: {counts['non_estimable']}")
    for k, v in resamp_agg.items():
        if isinstance(v, dict) and 'mean' in v:
            print(f"- {k}: mean={v['mean']:.3f}, std={v['std']:.3f}, median={v['median']:.3f}, p025={v['p025']:.3f}, p975={v['p975']:.3f}, min={v['min']:.3f}, max={v['max']:.3f}")

    print("\nB. Subgroups:")
    for s in subgroups:
        if s['analysis_status'] == 'Estimable':
            print(f"- Axis: {s['axis']}, Value: {s['value']}, Sample Count: {s['sample_count']}, Pos: {s['positive_count']}, Neg: {s['negative_count']}")
            print(f"  ROC-AUC: {s['roc_auc']:.3f}, Avg Precision: {s['avg_precision']:.3f}, Brier: {s['brier_score']:.3f}, Log Loss: {s['log_loss']:.3f}")
            c = s['thresholds'].get('youden_j', {})
            if c:
                print(f"  Accuracy: {c.get('accuracy',0):.3f}, Precision: {c.get('precision',0):.3f}, Recall: {c.get('recall',0):.3f}, Specificity: {c.get('specificity',0):.3f}, F1: {c.get('f1',0):.3f}, Balanced Accuracy: {c.get('balanced_accuracy',0):.3f}")
        else:
            print(f"- Axis: {s['axis']}, Value: {s['value']}, Reason: {s['reason']}")
            
    print("\nC. Perturbation:")
    for res in pert_results:
        print(f"- Feature: {res['feature']}, Direction: {res['direction']}")
        if "affected_count" in res:
            print(f"  Affected Count: {res['affected_count']}")
        print(f"  Mean Prob Change: {res['mean_prob_change']:.4f}, Mean Abs Prob Change: {res['mean_abs_prob_change']:.4f}, Flips: {res.get('youden_j_flips', 0)}, Flip Rate: {res.get('youden_j_flip_rate', 0):.4f}")

if __name__ == "__main__":
    run_phase4b()
