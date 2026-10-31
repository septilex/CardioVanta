"""
Inference on a registry-loaded model.

``InferenceEngine`` wraps a ``LoadedModel`` (already integrity-verified and
validated by ``cardiovanta_ml.registry``). It performs no I/O and never loads
artifacts itself. The method API (``predict``, ``explain``,
``explain_shap_equivalent`` and the ``schema`` / ``metadata`` attributes) is the
one the FastAPI layer has used since R0.3, ported unchanged.

``probability`` is always the calibrated P(significant obstructive CAD present).
The column is selected from the model's ``classes_`` and the disease label
declared in the registry metadata, never hard-coded.
"""
from typing import Any, Dict, Mapping, Optional

import pandas as pd

from cardiovanta_ml.inference.explain import linear_contributions, shap_equivalent_contributions
from cardiovanta_ml.inference.outcome import OUTCOME_ID, PROBABILITY_DEFINITION, disease_label_index
from cardiovanta_ml.registry.loader import LoadedModel

# Value exposed as metadata.outcome_mapping in the API, by registry mapping_status (R0.3-compatible strings).
OUTCOME_MAPPING_SOURCES = {
    "explicit": "explicit_package_metadata",
    "interim_legacy": "interim_legacy_inverted_target_mapping",
}


class InferenceEngine:
    def __init__(self, loaded: LoadedModel):
        if not isinstance(loaded, LoadedModel):
            raise TypeError("InferenceEngine requires a LoadedModel from cardiovanta_ml.load_model()")
        self.loaded = loaded
        self.model = loaded.model
        self.explanation_model = loaded.explanation_model
        self.schema = loaded.input_schema
        self.metadata = loaded.package_metadata
        self.shap_background = loaded.shap_background
        self.model_dir = loaded.artifact_dir

    @property
    def disease_label(self) -> int:
        """Model label meaning disease present, as declared in the registry metadata."""
        return self.loaded.disease_label

    @property
    def outcome_mapping_source(self) -> str:
        return OUTCOME_MAPPING_SOURCES[self.loaded.metadata.outcome.mapping_status]

    def _validate_input(self, raw_input: Mapping[str, Any]):
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

    def _frame(self, raw_input: Mapping[str, Any]):
        validated_input, outside_range = self._validate_input(raw_input)
        ordered_input = {k: [validated_input[k]] for k in self.schema["feature_order"]}
        return pd.DataFrame(ordered_input), outside_range

    def predict(self, raw_input: Mapping[str, Any], apply_threshold: Optional[float] = None) -> Dict[str, Any]:
        """Deterministic prediction. Returns a structured dictionary."""
        df_input, outside_range = self._frame(raw_input)

        disease_idx = disease_label_index(self.model.classes_, self.disease_label)
        prob = float(self.model.predict_proba(df_input)[0, disease_idx])

        result: Dict[str, Any] = {
            "probability": prob,
            "outcome": OUTCOME_ID,
            "probability_definition": PROBABILITY_DEFINITION,
            "outside_development_range": outside_range,
            "development_range_note": "Development-data ranges are dataset guardrails, not clinical validity limits." if outside_range else None,
        }

        if apply_threshold is not None:
            result["threshold_applied"] = apply_threshold
            # class 1 = disease present (P(disease) >= threshold); class 0 = not.
            result["class"] = 1 if prob >= apply_threshold else 0
        else:
            result["threshold_applied"] = None
            result["class"] = None
            result["threshold_note"] = "No validated production decision threshold is configured. Returning probability only."

        return result

    def explain(self, raw_input: Mapping[str, Any]) -> Dict[str, Any]:
        """Linear contributions of the uncalibrated explanation model (disease-present log-odds)."""
        if self.explanation_model is None:
            raise ValueError("explanation_model.joblib not found. Explanations unavailable.")
        df_input, _ = self._frame(raw_input)
        return linear_contributions(self.explanation_model, df_input, self.schema["feature_order"], self.disease_label)

    def explain_shap_equivalent(self, raw_input: Mapping[str, Any]) -> Dict[str, Any]:
        """SHAP-equivalent attribution of the explanation model against the frozen background."""
        if self.explanation_model is None or self.shap_background is None:
            raise ValueError("explanation_model.joblib or shap_background.json not found. SHAP explanations unavailable.")
        df_input, _ = self._frame(raw_input)
        return shap_equivalent_contributions(self.explanation_model, self.shap_background, df_input,
                                             self.schema["feature_order"], self.disease_label)


def predict(features: Mapping[str, Any], model: LoadedModel, threshold: Optional[float] = None) -> Dict[str, Any]:
    """Convenience: P(disease present) for one patient with a registry-loaded model."""
    return InferenceEngine(model).predict(features, apply_threshold=threshold)


def explain(features: Mapping[str, Any], model: LoadedModel) -> Dict[str, Any]:
    """Convenience: both explanation methods for one patient."""
    engine = InferenceEngine(model)
    return {"linear": engine.explain(features), "shap_equivalent": engine.explain_shap_equivalent(features)}
