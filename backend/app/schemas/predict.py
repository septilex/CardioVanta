from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional, Dict, Any, List

class PredictRequest(BaseModel):
    # Enforce exact fields in order and forbid extra fields
    model_config = ConfigDict(
        extra='forbid',
        json_schema_serialization_defaults_required=True
    )
    
    age: float
    sex: Literal[0, 1]
    cp: Literal[0, 1, 2, 3]
    trestbps: float
    chol: float
    fbs: Literal[0, 1]
    restecg: Literal[0, 1, 2]
    thalach: float
    exang: Literal[0, 1]
    oldpeak: float
    slope: Literal[0, 1, 2]
    ca: Literal[0, 1, 2, 3, 4]
    thal: Literal[0, 1, 2, 3]

class PredictionResult(BaseModel):
    probability: float
    threshold_applied: Optional[float]
    class_: Optional[int] = Field(default=None, alias='class')
    threshold_status: str

    model_config = ConfigDict(populate_by_name=True)

class DevelopmentRangeWarning(BaseModel):
    outside_development_range: bool
    features: List[str]
    note: Optional[str]

class FeatureContributions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    age: float
    sex: float
    cp: float
    trestbps: float
    chol: float
    fbs: float
    restecg: float
    thalach: float
    exang: float
    oldpeak: float
    slope: float
    ca: float
    thal: float

class ExplanationResult(BaseModel):
    intercept: float
    contributions: FeatureContributions = Field(
        description="Positive contribution: moves the Logistic Regression decision function toward the positive class / higher model score. Negative contribution: moves it toward the negative class / lower model score."
    )
    decision_function_log_odds: float
    note: str

class ShapEquivalentExplanationResult(BaseModel):
    expected_value: float
    contributions: FeatureContributions = Field(
        description="SHAP-equivalent contributions relative to the average patient (frozen development background). Positive contribution increases log-odds; negative decreases log-odds."
    )
    decision_function_log_odds: float
    note: str

class MetadataResult(BaseModel):
    package_version: str
    model_type: str
    calibration_method: str

class PredictResponse(BaseModel):
    prediction: PredictionResult
    development_range_warning: DevelopmentRangeWarning
    explanation: ExplanationResult
    shap_equivalent_explanation: ShapEquivalentExplanationResult
    metadata: MetadataResult

