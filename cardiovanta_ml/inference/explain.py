"""
Explanations of the uncalibrated explanation model, in disease-present orientation.

Both methods explain the EXPLANATION model: an uncalibrated LogisticRegression
fitted on the same development data. That is a different model from the
calibrated ensemble that produces the reported probability. Contributions are
therefore directional signals. They decompose the explanation model's log-odds
exactly, and do NOT decompose the calibrated probability.

Orientation: ``decision_function`` is the log-odds of ``classes_[1]``. Multiplying
by ``disease_log_odds_sign`` (exactly +1 or -1) re-expresses every term as log-odds
of disease presence, without changing additivity.

Ported unchanged from the pre-R2 ``src/inference/predict.py`` (R0.3 semantics).
"""
from typing import Any, Dict, Mapping, Sequence

import numpy as np
import pandas as pd

from cardiovanta_ml.inference.outcome import disease_log_odds_sign

LINEAR_NOTE = (
    "These feature contributions explain the underlying uncalibrated Logistic Regression explanation model's "
    "log-odds of significant obstructive CAD being present (positive = toward disease presence). That model is "
    "related to, but not identical to, the calibrated ensemble that produces the displayed probability; the "
    "contributions do not decompose that calibrated ensemble probability and do not imply clinical causality."
)
SHAP_NOTE = (
    "SHAP-equivalent linear attribution of the uncalibrated explanation model's log-odds of significant "
    "obstructive CAD being present, relative to the frozen development background (positive = toward disease "
    "presence). These contributions do not decompose the calibrated probability and do not imply clinical causality."
)


def _aggregate(feature_names: Sequence[str], contributions: np.ndarray, feature_order: Sequence[str]) -> Dict[str, float]:
    """Sum transformed-column contributions back onto the raw clinical features."""
    raw: Dict[str, float] = {f: 0.0 for f in feature_order}
    for name, contrib in zip(feature_names, contributions):
        for f in feature_order:
            if name.startswith(f"num__{f}") or name.startswith(f"bin__{f}") or name.startswith(f"cat__{f}_"):
                raw[f] += float(contrib)
                break
        else:
            raise ValueError(f"Could not map transformed feature {name} back to raw feature.")
    return raw


def linear_contributions(explanation_model: Any, df_input: pd.DataFrame, feature_order: Sequence[str],
                         disease_label: int) -> Dict[str, Any]:
    """Exact additive decomposition of the explanation model's disease log-odds: intercept + sum(coef * x)."""
    preprocessor = explanation_model.named_steps["preprocessor"]
    x_transformed = preprocessor.transform(df_input)[0]
    feature_names = preprocessor.get_feature_names_out()
    lr = explanation_model.named_steps["model"]
    coef = lr.coef_[0]
    intercept = float(lr.intercept_[0])

    raw = _aggregate(feature_names, x_transformed * coef, feature_order)
    sum_of_contributions = float(sum(raw.values()))
    actual_decision_function = float(explanation_model.decision_function(df_input)[0])
    np.testing.assert_almost_equal(intercept + sum_of_contributions, actual_decision_function, decimal=5)

    sign = disease_log_odds_sign(explanation_model.classes_, disease_label)
    return {
        "note": LINEAR_NOTE,
        "intercept": sign * intercept,
        "contributions": {f: sign * v for f, v in raw.items()},
        "decision_function_log_odds": sign * actual_decision_function,
    }


def shap_equivalent_contributions(explanation_model: Any, shap_background: Mapping[str, Any], df_input: pd.DataFrame,
                                  feature_order: Sequence[str], disease_label: int) -> Dict[str, Any]:
    """Closed-form linear SHAP of the explanation model, coef * (x - E[x]), against the frozen background means."""
    preprocessor = explanation_model.named_steps["preprocessor"]
    x_transformed = preprocessor.transform(df_input)[0]
    feature_names = preprocessor.get_feature_names_out()
    coef = explanation_model.named_steps["model"].coef_[0]

    bg_means = shap_background["background_means"]
    expected_value = shap_background["expected_value"]
    bg_means_array = np.array([bg_means[fn] for fn in feature_names])

    raw = _aggregate(feature_names, coef * (x_transformed - bg_means_array), feature_order)
    actual_decision_function = float(explanation_model.decision_function(df_input)[0])
    sum_of_contributions = float(sum(raw.values()))
    np.testing.assert_almost_equal(expected_value + sum_of_contributions, actual_decision_function, decimal=5)

    sign = disease_log_odds_sign(explanation_model.classes_, disease_label)
    return {
        "note": SHAP_NOTE,
        "expected_value": sign * expected_value,
        "contributions": {f: sign * v for f, v in raw.items()},
        "decision_function_log_odds": sign * actual_decision_function,
    }
