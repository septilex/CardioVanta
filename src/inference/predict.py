import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from src.config.config import BASE_DIR

class InferenceEngine:
    def __init__(self, model_dir=None):
        if model_dir is None:
            self.model_dir = BASE_DIR / "artifacts" / "model"
        else:
            self.model_dir = Path(model_dir)
            
        # Load schema
        with open(self.model_dir / "feature_schema.json", "r") as f:
            self.schema = json.load(f)
            
        # Load metadata
        with open(self.model_dir / "metadata.json", "r") as f:
            self.metadata = json.load(f)
            
        # Verify sklearn version
        import sklearn
        req_version = self.metadata["environment"]["sklearn_version"]
        if sklearn.__version__ != req_version:
            raise ValueError(f"Runtime sklearn version {sklearn.__version__} is incompatible with package metadata {req_version}")
            
        # Load models
        self.model = joblib.load(self.model_dir / "model.joblib")
        
        # Load explanation model (uncalibrated Logistic Regression on full dev set)
        exp_path = self.model_dir / "explanation_model.joblib"
        if exp_path.exists():
            self.explanation_model = joblib.load(exp_path)
        else:
            self.explanation_model = None
            
        # Load SHAP background artifact if available
        shap_bg_path = self.model_dir / "shap_background.json"
        if shap_bg_path.exists():
            with open(shap_bg_path, "r") as f:
                self.shap_background = json.load(f)
        else:
            self.shap_background = None
        
    def _validate_input(self, raw_input: dict):
        # 1. Missing or Extra features
        expected_features = set(self.schema["feature_order"])
        input_features = set(raw_input.keys())
        
        missing = expected_features - input_features
        extra = input_features - expected_features
        
        if missing:
            raise ValueError(f"Missing required features: {missing}")
        if extra:
            raise ValueError(f"Unexpected extra features: {extra}")
            
        validated = {}
        outside_range = False
        
        # 2. Validate types and bounds
        for feature in self.schema["features"]:
            name = feature["name"]
            val = raw_input[name]
            
            # Must be numeric
            try:
                val = float(val)
            except (ValueError, TypeError):
                raise ValueError(f"Feature '{name}' must be numeric. Received: {val}")
                
            ftype = feature["type"]
            
            if ftype in ["binary", "categorical"]:
                if val not in feature["allowed_values"]:
                    raise ValueError(f"Feature '{name}' value {val} not in allowed categorical/binary values {feature['allowed_values']}.")
            elif ftype == "continuous":
                if val < feature["min"] or val > feature["max"]:
                    outside_range = True
                    
            validated[name] = val
            
        return validated, outside_range

    def predict(self, raw_input: dict, apply_threshold: float = None):
        """
        Deterministic prediction. Returns a structured dictionary.
        """
        validated_input, outside_range = self._validate_input(raw_input)
        
        # Ensure correct order
        ordered_input = {k: [validated_input[k]] for k in self.schema["feature_order"]}
        df_input = pd.DataFrame(ordered_input)
        
        # Predict calibrated probability
        prob = self.model.predict_proba(df_input)[0, 1]
        
        result = {
            "probability": prob,
            "outside_development_range": outside_range,
            "development_range_note": "Development-data ranges are dataset guardrails, not clinical validity limits." if outside_range else None
        }
        
        if apply_threshold is not None:
            result["threshold_applied"] = apply_threshold
            result["class"] = 1 if prob >= apply_threshold else 0
        else:
            result["threshold_applied"] = None
            result["class"] = None
            result["threshold_note"] = "No validated production decision threshold is configured. Returning probability only."
            
        return result
        
    def explain(self, raw_input: dict):
        """
        Deterministic offline local explanation support for the underlying Logistic Regression model.
        Uses the standalone explanation model (uncalibrated Logistic Regression on full dev data)
        for exact consistency with Phase 3 methodology.
        """
        if self.explanation_model is None:
            raise ValueError("explanation_model.joblib not found. Explanations unavailable.")
            
        validated_input, _ = self._validate_input(raw_input)
        ordered_input = {k: [validated_input[k]] for k in self.schema["feature_order"]}
        df_input = pd.DataFrame(ordered_input)
        
        preprocessor = self.explanation_model.named_steps['preprocessor']
        X_transformed = preprocessor.transform(df_input)[0]
        feature_names = preprocessor.get_feature_names_out()
        
        lr = self.explanation_model.named_steps['model']
        coef = lr.coef_[0]
        intercept = float(lr.intercept_[0])
        
        contributions = X_transformed * coef
        
        raw_feature_contributions = {f: 0.0 for f in self.schema["feature_order"]}
        for name, contrib in zip(feature_names, contributions):
            found = False
            for f in self.schema["feature_order"]:
                if name.startswith(f"num__{f}") or name.startswith(f"bin__{f}") or name.startswith(f"cat__{f}_"):
                    raw_feature_contributions[f] += float(contrib)
                    found = True
                    break
            if not found:
                raise ValueError(f"Could not map transformed feature {name} back to raw feature.")
                
        decision_function_value = float(intercept + sum(raw_feature_contributions.values()))
        sum_of_contributions = float(sum(raw_feature_contributions.values()))
        
        # Verify intercept + sum(feature contributions) == decision_function()
        actual_decision_function = float(self.explanation_model.decision_function(df_input)[0])
        np.testing.assert_almost_equal(
            intercept + sum_of_contributions,
            actual_decision_function,
            decimal=5
        )
        
        return {
            "note": "These feature contributions explain the underlying uncalibrated Logistic Regression decision function (log-odds). They do not decompose the final calibrated ensemble probability and do not imply clinical causality.",
            "intercept": intercept,
            "contributions": raw_feature_contributions,
            "decision_function_log_odds": actual_decision_function
        }
        
    def explain_shap_equivalent(self, raw_input: dict):
        """
        Deterministic, zero-overhead SHAP-equivalent explanation (LinearExplainer with independent feature perturbation
        and implicit kmeans-100 background representation).
        """
        if self.explanation_model is None or self.shap_background is None:
            raise ValueError("explanation_model.joblib or shap_background.json not found. SHAP explanations unavailable.")
            
        validated_input, _ = self._validate_input(raw_input)
        ordered_input = {k: [validated_input[k]] for k in self.schema["feature_order"]}
        df_input = pd.DataFrame(ordered_input)
        
        preprocessor = self.explanation_model.named_steps['preprocessor']
        X_transformed = preprocessor.transform(df_input)[0]
        feature_names = preprocessor.get_feature_names_out()
        
        lr = self.explanation_model.named_steps['model']
        coef = lr.coef_[0]
        
        bg_means = self.shap_background["background_means"]
        expected_value = self.shap_background["expected_value"]
        
        # Convert bg_means to an array matching feature_names
        bg_means_array = np.array([bg_means[fn] for fn in feature_names])
        
        # Calculate manual SHAP contributions: coef * (X_transformed - E[X])
        contributions = coef * (X_transformed - bg_means_array)
        
        raw_feature_contributions = {f: 0.0 for f in self.schema["feature_order"]}
        for name, contrib in zip(feature_names, contributions):
            found = False
            for f in self.schema["feature_order"]:
                if name.startswith(f"num__{f}") or name.startswith(f"bin__{f}") or name.startswith(f"cat__{f}_"):
                    raw_feature_contributions[f] += float(contrib)
                    found = True
                    break
            if not found:
                raise ValueError(f"Could not map transformed feature {name} back to raw feature.")
                
        actual_decision_function = float(self.explanation_model.decision_function(df_input)[0])
        sum_of_contributions = float(sum(raw_feature_contributions.values()))
        
        # SHAP additivity check
        np.testing.assert_almost_equal(
            expected_value + sum_of_contributions,
            actual_decision_function,
            decimal=5
        )
        
        return {
            "note": "SHAP-equivalent linear attribution relative to the frozen development background. These log-odds contributions do not imply clinical causality.",
            "expected_value": expected_value,
            "contributions": raw_feature_contributions,
            "decision_function_log_odds": actual_decision_function
        }
