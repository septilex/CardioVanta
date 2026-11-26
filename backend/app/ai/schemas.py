from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from cardiovanta_ml.contracts.generated_features import OutcomeId

Feature = Literal["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"]
Direction = Literal["increases", "decreases", "neutral"]
Text = Annotated[str, Field(min_length=1, max_length=800)]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Factor(StrictModel):
    feature_name: Feature
    contribution_direction: Direction

class ExplanationRequest(StrictModel):
    probability: float = Field(ge=0, le=1)
    outcome: OutcomeId
    contributing_factors: list[Factor] = Field(min_length=1, max_length=13)

    @model_validator(mode="after")
    def unique_features(self):
        names = [f.feature_name for f in self.contributing_factors]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate features")
        return self

class ExplainedFactor(Factor):
    plain_language_explanation: Text

class ExplanationContent(StrictModel):
    summary: Text
    prediction_interpretation: Text
    contributing_factors: list[ExplainedFactor] = Field(min_length=1, max_length=13)
    limitations: list[Text] = Field(min_length=1, max_length=5)

class ExplanationResponse(ExplanationContent):
    recommended_next_step: str
    disclaimer: str
    prompt_version: Literal["explanation-v1"]
