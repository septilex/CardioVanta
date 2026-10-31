// Clinical feature and outcome definitions are generated from
// contracts/feature_schema.v2.json. Do not redeclare them here.
import type { ClinicalFeatures, FeatureId, OutcomeId } from "./generated-features";

export * from "./generated-features";

/** Request body of POST /api/v1/predict: the 13 production clinical inputs. */
export type PredictRequest = ClinicalFeatures;

export interface PredictionResult {
  /** Calibrated model-estimated probability that significant obstructive CAD is present. */
  probability: number;
  /** Always the contract outcome id (disease-positive orientation). */
  outcome?: OutcomeId;
  probability_definition?: string;
  /** Only when a threshold is supplied: 1 = disease present, 0 = not. */
  threshold_applied: number | null;
  class: number | null;
  threshold_status: string;
}

export interface DevelopmentRangeWarning {
  outside_development_range: boolean;
  features: string[];
  note: string | null;
}

/** One additive contribution per production feature. */
export type FeatureContributions = { [K in FeatureId]: number };

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
  /** "explicit_package_metadata" | "interim_legacy_inverted_target_mapping" */
  outcome_mapping?: string;
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
