export interface PredictRequest {
  age: number;
  sex: 0 | 1;
  cp: 0 | 1 | 2 | 3;
  trestbps: number;
  chol: number;
  fbs: 0 | 1;
  restecg: 0 | 1 | 2;
  thalach: number;
  exang: 0 | 1;
  oldpeak: number;
  slope: 0 | 1 | 2;
  ca: 0 | 1 | 2 | 3 | 4;
  thal: 0 | 1 | 2 | 3;
}

export interface PredictionResult {
  probability: number;
  threshold_applied: number | null;
  class: number | null;
  threshold_status: string;
}

export interface DevelopmentRangeWarning {
  outside_development_range: boolean;
  features: string[];
  note: string | null;
}

export interface FeatureContributions {
  age: number;
  sex: number;
  cp: number;
  trestbps: number;
  chol: number;
  fbs: number;
  restecg: number;
  thalach: number;
  exang: number;
  oldpeak: number;
  slope: number;
  ca: number;
  thal: number;
}

export interface ExplanationResult {
  intercept: number;
  contributions: FeatureContributions;
  decision_function_log_odds: number;
  note: string;
}

export interface MetadataResult {
  package_version: string;
  model_type: string;
  calibration_method: string;
}

export interface ShapEquivalentExplanationResult {
  expected_value: number;
  contributions: FeatureContributions;
  decision_function_log_odds: number;
  note: string;
}

export interface PredictResponse {
  prediction: PredictionResult;
  development_range_warning: DevelopmentRangeWarning;
  explanation: ExplanationResult;
  shap_equivalent_explanation?: ShapEquivalentExplanationResult;
  metadata: MetadataResult;
}
