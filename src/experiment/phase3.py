import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sklearn
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score, average_precision_score
from sklearn.calibration import CalibratedClassifierCV, CalibrationDisplay
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression

from src.config.config import RAW_DATA_PATH, load_schema, RANDOM_SEED, BASE_DIR
from src.preprocessing.preprocessor import PreprocessingFactory

def check_temperature_scaling():
    from sklearn.dummy import DummyClassifier
    
    # 1. Check initialization
    try:
        clf = CalibratedClassifierCV(estimator=DummyClassifier(strategy="prior"), method='temperature', cv=2)
        init_success = True
    except Exception as e:
        init_success = False
        return False, init_success, False, f"{type(e).__name__}: {str(e)}"
        
    # 2. Check fitting
    try:
        X_dummy = [[0], [1], [0], [1]]
        y_dummy = np.array([0, 1, 0, 1])
        clf.fit(X_dummy, y_dummy)
        fit_success = True
        return True, init_success, fit_success, None
    except Exception as e:
        fit_success = False
        return False, init_success, fit_success, f"{type(e).__name__}: {str(e)}"

def map_transformed_features(transformed_features, orig_features):
    mapping = {}
    for tf in transformed_features:
        parts = tf.split("__", 1)
        if len(parts) == 2:
            raw_name = parts[1]
            matched = False
            # Sort original features by length descending to match exactly (e.g. 'thalach' vs 'thal')
            for of in sorted(orig_features, key=len, reverse=True):
                if raw_name == of or raw_name.startswith(of + "_"):
                    mapping[tf] = of
                    matched = True
                    break
            if not matched:
                raise ValueError(f"Could not map transformed feature {tf}")
        else:
            raise ValueError(f"Unexpected transformed feature format: {tf}")
            
    if len(mapping) != len(transformed_features):
        raise ValueError("Not all transformed features mapped")
    if len(set(mapping.values())) != len(orig_features):
        raise ValueError("Not all raw features are represented in the mapping")
        
    return mapping

def run_phase3_final():
    print("Starting Phase 3 FINAL QA: Calibration and Explainability Correction...")
    reports_dir = BASE_DIR / "reports"
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"exact sklearn.__version__: {sklearn.__version__}")
    is_temp_supported, init_ok, fit_ok, err_msg = check_temperature_scaling()
    print(f"whether method='temperature' successfully initializes: {init_ok}")
    print(f"whether method='temperature' successfully fits: {fit_ok}")
    if not is_temp_supported:
        print(f"exact exception: {err_msg}")
    
    # 1. Load Data (Development Only - STRICT NO X_test)
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    
    # Read the frozen development indices created previously
    dev_idx_path = BASE_DIR / "data" / "processed" / "dev_indices.json"
    if not dev_idx_path.exists():
        raise FileNotFoundError(f"Missing frozen split artifact: {dev_idx_path}")
        
    with open(dev_idx_path, "r") as f:
        dev_idx = json.load(f)
    
    X_full = df.drop(columns=[schema["target_column"]])
    # MUST convert y to numpy to avoid pandas KeyError in sklearn 1.9.0 temperature scaling
    y_full = df[schema["target_column"]].to_numpy()
    
    X_train = X_full.loc[dev_idx].reset_index(drop=True)
    y_train = y_full[dev_idx]
    
    # Base Estimator Configuration
    base_params = {'C': 0.1, 'class_weight': 'balanced', 'solver': 'lbfgs', 'random_state': RANDOM_SEED}
    
    supported_methods = ['sigmoid', 'isotonic']
    if is_temp_supported:
        supported_methods.append('temperature')
        
    kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    
    metrics = {
        'uncalibrated': {'brier': [], 'log_loss': [], 'roc_auc': [], 'avg_precision': [], 'probs': [], 'y_true': []}
    }
    for m in supported_methods:
        metrics[m] = {'brier': [], 'log_loss': [], 'roc_auc': [], 'avg_precision': [], 'probs': [], 'y_true': []}
        
    global_importances_oof = []

    # 3. Leakage-safe Calibration Loop
    for train_idx, val_idx in kf.split(X_train, y_train):
        X_tr, y_tr = X_train.iloc[train_idx], y_train[train_idx]
        X_val, y_val = X_train.iloc[val_idx], y_train[val_idx]
        
        # Uncalibrated Base Model
        factory = PreprocessingFactory()
        pipe_uncal = Pipeline([
            ('preprocessor', factory.get_preprocessing_pipeline('linear')),
            ('model', LogisticRegression(**base_params))
        ])
        pipe_uncal.fit(X_tr, y_tr)
        prob_uncal = pipe_uncal.predict_proba(X_val)[:, 1]
        
        # Measure out-of-fold feature importance using the base uncalibrated model
        perm_res = permutation_importance(pipe_uncal, X_val, y_val, scoring='roc_auc', n_repeats=5, random_state=RANDOM_SEED)
        global_importances_oof.append(perm_res.importances_mean)
        
        metrics['uncalibrated']['brier'].append(brier_score_loss(y_val, prob_uncal))
        metrics['uncalibrated']['log_loss'].append(log_loss(y_val, prob_uncal))
        metrics['uncalibrated']['roc_auc'].append(roc_auc_score(y_val, prob_uncal))
        metrics['uncalibrated']['avg_precision'].append(average_precision_score(y_val, prob_uncal))
        metrics['uncalibrated']['probs'].extend(prob_uncal)
        metrics['uncalibrated']['y_true'].extend(y_val)
        
        for m in supported_methods:
            factory_cal = PreprocessingFactory()
            pipe_base = Pipeline([
                ('preprocessor', factory_cal.get_preprocessing_pipeline('linear')),
                ('model', LogisticRegression(**base_params))
            ])
            cal = CalibratedClassifierCV(estimator=pipe_base, method=m, cv=3)
            cal.fit(X_tr, y_tr)
            prob_cal = cal.predict_proba(X_val)[:, 1]
            
            metrics[m]['brier'].append(brier_score_loss(y_val, prob_cal))
            metrics[m]['log_loss'].append(log_loss(y_val, prob_cal))
            metrics[m]['roc_auc'].append(roc_auc_score(y_val, prob_cal))
            metrics[m]['avg_precision'].append(average_precision_score(y_val, prob_cal))
            metrics[m]['probs'].extend(prob_cal)
            metrics[m]['y_true'].extend(y_val)
            
    summary = {}
    for name in metrics:
        summary[name] = {
            'brier_mean': float(np.mean(metrics[name]['brier'])), 'brier_std': float(np.std(metrics[name]['brier'])),
            'log_loss_mean': float(np.mean(metrics[name]['log_loss'])), 'log_loss_std': float(np.std(metrics[name]['log_loss'])),
            'roc_auc_mean': float(np.mean(metrics[name]['roc_auc'])), 'roc_auc_std': float(np.std(metrics[name]['roc_auc'])),
            'avg_precision_mean': float(np.mean(metrics[name]['avg_precision'])), 'avg_precision_std': float(np.std(metrics[name]['avg_precision'])),
            'brier_min': float(np.min(metrics[name]['brier'])), 'brier_max': float(np.max(metrics[name]['brier']))
        }
        
    # 5. Safe Selection Rule
    uncal_brier = summary['uncalibrated']['brier_mean']
    uncal_logloss = summary['uncalibrated']['log_loss_mean']
    
    best_brier = uncal_brier
    selected_method = 'uncalibrated'
    selection_reason = "Uncalibrated baseline performed better on the observed development CV metrics or was more stable."
    
    for m in supported_methods:
        brier = summary[m]['brier_mean']
        logloss = summary[m]['log_loss_mean']
        
        if brier < best_brier:
            # Stability check: log loss must not blow up massively
            if logloss > uncal_logloss * 1.2:
                print(f"Rejecting {m} despite lower Brier score due to unstable log loss ({logloss:.4f} vs {uncal_logloss:.4f})")
                if m == 'isotonic':
                    selection_reason = f"Isotonic rejected. While it had a lower Brier score, its high Log Loss ({logloss:.2f}) is consistent with overfitting risk on this small calibration dataset."
                else:
                    selection_reason = f"{m} rejected due to unstable Log Loss ({logloss:.2f}), consistent with overfitting risk."
            else:
                best_brier = brier
                selected_method = m
                selection_reason = f"Selected {m} because it performed better on the observed development CV metrics (lowest stable Brier score)."
                
    # 3. Calibration Curves
    fig, ax = plt.subplots(figsize=(8, 6))
    for name in ['uncalibrated'] + supported_methods:
        CalibrationDisplay.from_predictions(metrics[name]['y_true'], metrics[name]['probs'], n_bins=5, ax=ax, name=name.capitalize())
    plt.title('Calibration Curves on Development Data')
    plt.tight_layout()
    plt.savefig(figures_dir / "calibration_curves.png")
    plt.close()
    
    cal_results = []
    for name, res in summary.items():
        res['method'] = name
        cal_results.append(res)
    pd.DataFrame(cal_results).to_csv(reports_dir / "phase3_calibration_results.csv", index=False)
    
    with open(reports_dir / "phase3_calibration_results.json", "w") as f:
        json.dump({
            "base_model": "Logistic Regression",
            "cv_configuration": "StratifiedKFold(n_splits=5)",
            "selection_rule": "Lowest mean Brier score with Log Loss stability check",
            "temperature_scaling_evaluated": is_temp_supported,
            "selected_method": selected_method,
            "calibration_cv": 5,
            "selection_reason": selection_reason,
            "results": cal_results
        }, f, indent=4)
        
    print(f"Selected Calibration: {selected_method}. Reason: {selection_reason}")
    
    # 9. Global Explainability (Out-of-Fold)
    mean_oof_importances = np.mean(global_importances_oof, axis=0)
    std_oof_importances = np.std(global_importances_oof, axis=0)
    
    global_imp = pd.DataFrame({
        'feature': X_train.columns,
        'importance_mean': mean_oof_importances,
        'importance_std': std_oof_importances
    }).sort_values('importance_mean', ascending=False)
    
    global_imp.to_csv(reports_dir / "phase3_global_importance.csv", index=False)
    with open(reports_dir / "phase3_global_importance.json", "w") as f:
        json.dump({
            "method": "Out-of-Fold Permutation Importance (ROC-AUC)",
            "features": global_imp.to_dict(orient='records')
        }, f, indent=4)
        
    plt.figure(figsize=(10, 6))
    plt.barh(global_imp['feature'][::-1], global_imp['importance_mean'][::-1], xerr=global_imp['importance_std'][::-1])
    plt.xlabel("Permutation Importance (Mean Decrease in ROC-AUC)")
    plt.title("Global Feature Importance (Out-of-Fold Dev Data)")
    plt.tight_layout()
    plt.savefig(figures_dir / "global_feature_importance.png")
    plt.close()

    # 8. Fix Local Explainability (Option A)
    # Fit ONE standalone base pipeline to get uncalibrated coefficients and logit
    factory_base = PreprocessingFactory()
    single_base_pipe = Pipeline([
        ('preprocessor', factory_base.get_preprocessing_pipeline('linear')),
        ('model', LogisticRegression(**base_params))
    ])
    single_base_pipe.fit(X_train, y_train)
    
    # Fit the final calibrated model
    if selected_method == 'uncalibrated':
        final_model = single_base_pipe
    else:
        factory_cal = PreprocessingFactory()
        pipe_for_cal = Pipeline([
            ('preprocessor', factory_cal.get_preprocessing_pipeline('linear')),
            ('model', LogisticRegression(**base_params))
        ])
        final_model = CalibratedClassifierCV(estimator=pipe_for_cal, method=selected_method, cv=5)
        final_model.fit(X_train, y_train)
        
    preprocessor = single_base_pipe.named_steps['preprocessor']
    classifier = single_base_pipe.named_steps['model']
    
    try:
        transformed_features = preprocessor.get_feature_names_out()
    except AttributeError:
        transformed_features = [f"f{i}" for i in range(classifier.coef_.shape[1])]
    
    coefs = classifier.coef_[0]
    intercept = classifier.intercept_[0]
    
    # Precise deterministic mapping
    orig_features = list(X_train.columns)
    mapping = map_transformed_features(transformed_features, orig_features)
    
    local_examples = []
    sample_indices = [0, 50, 100]
    
    for idx in sample_indices:
        x_sample = X_train.iloc[[idx]]
        y_true = int(y_train[idx])
        
        base_prob = single_base_pipe.predict_proba(x_sample)[0, 1]
        cal_prob = final_model.predict_proba(x_sample)[0, 1]
        pred_class = int(final_model.predict(x_sample)[0])
        
        # Calculate raw logit manually to verify
        logit = single_base_pipe.decision_function(x_sample)[0]
        
        x_trans = preprocessor.transform(x_sample)
        if hasattr(x_trans, 'toarray'):
            x_trans = x_trans.toarray()
        x_trans = x_trans[0]
        
        raw_contributions = x_trans * coefs
        
        original_contributions = {col: 0.0 for col in orig_features}
        
        for tf, contrib in zip(transformed_features, raw_contributions):
            original_contributions[mapping[tf]] += contrib
                    
        # Verification Math
        sum_contribs = sum(original_contributions.values())
        reconstructed_logit = sum_contribs + intercept
        
        # Verify mathematically that sum of contributions + intercept == logit
        assert np.isclose(reconstructed_logit, logit), f"Logit mismatch: {reconstructed_logit} != {logit}"
        
        sorted_contribs = sorted(original_contributions.items(), key=lambda item: item[1], reverse=True)
        pos_contributors = [{"feature": k, "contribution": float(v), "direction": "positive"} for k, v in sorted_contribs if v > 0]
        neg_contributors = [{"feature": k, "contribution": float(v), "direction": "negative"} for k, v in sorted_contribs if v < 0][::-1]
        
        local_examples.append({
            "sample_index_in_dev": int(idx),
            "true_label": int(y_true),
            "predicted_class": pred_class,
            "base_logistic_regression_probability": float(base_prob),
            "calibrated_final_probability": float(cal_prob),
            "explanation_target": "Base Logistic Regression logit contribution",
            "base_intercept": float(intercept),
            "reconstructed_logit": float(reconstructed_logit),
            "actual_logit": float(logit),
            "top_positive_contributors": pos_contributors[:3],
            "top_negative_contributors": neg_contributors[:3],
            "all_features_represented": True
        })
        
    with open(reports_dir / "phase3_local_examples.json", "w") as f:
        json.dump({
            "method": "Base Logistic Regression Contribution (Option A)",
            "note": "The contribution values explain the base uncalibrated Logistic Regression logit. They do not decompose the calibrated ensemble probability.",
            "examples": local_examples
        }, f, indent=4)
        
    # Plot Local Example
    plt.figure(figsize=(8, 5))
    example_data = local_examples[0]
    feats = [item['feature'] for item in example_data['top_positive_contributors']] + [item['feature'] for item in example_data['top_negative_contributors']]
    vals = [item['contribution'] for item in example_data['top_positive_contributors']] + [item['contribution'] for item in example_data['top_negative_contributors']]
    colors = ['green' if v > 0 else 'red' for v in vals]
    
    plt.barh(feats[::-1], vals[::-1], color=colors[::-1])
    plt.xlabel("Base Logit Contribution Magnitude")
    plt.title(f"Base Feature Contributions (Dev Sample {example_data['sample_index_in_dev']})\nCalibrated Prob: {example_data['calibrated_final_probability']:.2f} | Base Prob: {example_data['base_logistic_regression_probability']:.2f}")
    plt.tight_layout()
    plt.savefig(figures_dir / "local_explanation_example.png")
    plt.close()

    print("Phase 3 FINAL QA Complete.")

if __name__ == "__main__":
    run_phase3_final()
