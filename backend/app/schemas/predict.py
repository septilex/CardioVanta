from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional, List

from backend.app.schemas.generated_features import (
    ClinicalFeaturesBase,
    FeatureContributionsBase,
    OutcomeId,
)

# Feature fields, types, accepted codes and descriptions come from the generated
# contract module (source: contracts/feature_schema.v2.json). Do not redeclare them here.


class PredictRequest(ClinicalFeaturesBase):
    # Enforce exact fields in order and forbid extra fields
    model_config = ConfigDict(
        extra='forbid',
        json_schema_serialization_defaults_required=True
    )

class PredictionResult(BaseModel):
    probability: float = Field(
        description="Calibrated model-estimated probability that significant obstructive CAD is present (disease-positive orientation)."
    )
    outcome: OutcomeId = Field(
        description="Event whose probability is reported. The positive outcome always means disease present."
    )
    probability_definition: str
    threshold_applied: Optional[float]
    class_: Optional[int] = Field(
        default=None,
        alias='class',
        description="Only when a threshold is supplied: 1 = disease present (probability >= threshold), 0 = not. A mathematical operating point, not a diagnosis."
    )
    threshold_status: str

    model_config = ConfigDict(populate_by_name=True)

class DevelopmentRangeWarning(BaseModel):
    outside_development_range: bool
    features: List[str]
    note: Optional[str]

class FeatureContributions(FeatureContributionsBase):
    model_config = ConfigDict(extra='forbid')

class ExplanationResult(BaseModel):
    intercept: float
    contributions: FeatureContributions = Field(
        description="Positive contribution: moves the Logistic Regression decision function toward the positive class (positive class = significant obstructive CAD present). Negative contribution: moves it toward disease absence. Contributions explain the uncalibrated explanation model's log-odds, not the calibrated probability."
    )
    decision_function_log_odds: float
    note: str

class ShapEquivalentExplanationResult(BaseModel):
    expected_value: float
    contributions: FeatureContributions = Field(
        description="SHAP-equivalent contributions relative to the frozen development background. Positive contribution increases the explanation model's log-odds of significant obstructive CAD being present; negative decreases them."
    )
    decision_function_log_odds: float
    note: str

class MetadataResult(BaseModel):
    package_version: str
    model_type: str
    calibration_method: str
    outcome_mapping: str = Field(
        description="How disease-positive orientation was established: 'explicit_package_metadata' or 'interim_legacy_inverted_target_mapping' (frozen package 1.0.0, trained on an inverted target; see src/inference/outcome.py)."
    )

class PredictResponse(BaseModel):
    prediction: PredictionResult
    development_range_warning: DevelopmentRangeWarning
    explanation: ExplanationResult
    shap_equivalent_explanation: ShapEquivalentExplanationResult
    metadata: MetadataResult

