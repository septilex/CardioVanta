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

/* ─── Research evaluations (PostgreSQL, research metadata only) ─── */

export interface ResearchEvaluationRow {
  version: string;
  serialization: string;
  cohort: string;
  cohort_name: string;
  cohort_role: string;
  n_patients: number;
  method: string;
  evaluated_on: string;
  source: string;
  metric: string;
  value: number;
}

export interface ResearchEvaluations {
  evaluations: ResearchEvaluationRow[];
  version_coverage: { version: string; serialization: string; calibration: string; evaluation_count: number; cohorts: string[] }[];
  unevaluated_cohorts: { code: string; name: string; country: string; n_patients: number; role: string }[];
}

/** GET /api/v1/research/evaluations. Rejects with ApiError (status 503 + code) when the database is unavailable. */
export async function fetchResearchEvaluations(signal?: AbortSignal): Promise<ResearchEvaluations> {
  const response = await fetch(`${API_BASE_URL}/api/v1/research/evaluations`, { signal });
  if (!response.ok) {
    let message = "Research data could not be loaded.";
    let code: string | undefined;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
      code = typeof body.code === "string" ? body.code : undefined;
    } catch {
      // keep the generic message
    }
    throw new ApiError(message, response.status, code);
  }
  return response.json();
}
