import { PredictRequest, PredictResponse } from "../types";
import { PREDICTION_AVAILABILITY, UNAVAILABLE_CODE } from "./predictionAvailability";

const getApiBaseUrl = () => {
  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envUrl && envUrl.trim() !== "") {
    return envUrl.trim();
  }
  if (process.env.NODE_ENV === "development") {
    return "http://127.0.0.1:8000";
  }
  return "";
};

export const API_BASE_URL = getApiBaseUrl();

export class ApiError extends Error {
  constructor(public message: string, public status?: number, public code?: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Wakes the serverless prediction function without sending any clinical data.
 * The Python function can take tens of seconds to start after a quiet period (cold start);
 * calling the health endpoint as soon as the assessment page opens means the model is usually
 * loaded by the time the person submits. Failures are ignored: this is only an optimisation.
 */
let warmUpStarted = false;
export function warmUpPredictionService(): void {
  if (warmUpStarted || !PREDICTION_AVAILABILITY.enabled || typeof fetch !== "function") return;
  warmUpStarted = true;
  fetch(`${API_BASE_URL}/api/v1/health`, { method: "GET", cache: "no-store", keepalive: true }).catch(() => {
    warmUpStarted = false;
  });
}

export async function predict(data: PredictRequest, signal?: AbortSignal): Promise<PredictResponse> {
  // Containment (Phase 10): never send a prediction request while predictions are unavailable.
  if (!PREDICTION_AVAILABILITY.enabled) {
    throw new ApiError(PREDICTION_AVAILABILITY.notice, 503, UNAVAILABLE_CODE);
  }

  const url = `${API_BASE_URL}/api/v1/predict`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
    signal,
  });

  if (!response.ok) {
    let errorMessage = "An unknown error occurred while predicting.";
    let errorCode: string | undefined;
    try {
      const errData = await response.json();
      errorMessage = errData.detail || errorMessage;
      errorCode = typeof errData.code === "string" ? errData.code : undefined;
    } catch {
      // Ignored
    }
    throw new ApiError(errorMessage, response.status, errorCode);
  }

  return response.json();
}
