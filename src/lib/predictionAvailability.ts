/**
 * Prediction availability (Phase 10 production-incident containment).
 *
 * The web app reads the same committed switch as the API, `configs/prediction_service.json`, so the
 * two halves of one deployment always agree. It is imported at build time and is deliberately not an
 * environment variable: production settings cannot re-enable predictions. Re-enabling is a reviewed
 * change of `predictions_enabled` to `true`, followed by a verified deployment.
 *
 * Fail-safe: predictions are enabled only when `predictions_enabled` is exactly `true`.
 */
import serviceConfig from "../../configs/prediction_service.json";

export const UNAVAILABLE_CODE = "predictions_temporarily_unavailable";
export const DEFAULT_UNAVAILABLE_NOTICE =
  "CardioVanta predictions are temporarily unavailable while we verify the prediction service. No risk estimate can currently be generated.";

export interface PredictionAvailability {
  enabled: boolean;
  notice: string;
}

export function resolvePredictionAvailability(raw: unknown): PredictionAvailability {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) {
    return { enabled: false, notice: DEFAULT_UNAVAILABLE_NOTICE };
  }
  const record = raw as Record<string, unknown>;
  const notice =
    typeof record.notice === "string" && record.notice.trim() !== ""
      ? record.notice.trim()
      : DEFAULT_UNAVAILABLE_NOTICE;
  return { enabled: record.predictions_enabled === true, notice };
}

export const PREDICTION_AVAILABILITY: PredictionAvailability = resolvePredictionAvailability(serviceConfig);
