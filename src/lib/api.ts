import { PredictRequest, PredictResponse } from "../types";

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
  constructor(public message: string, public status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function predict(data: PredictRequest, signal?: AbortSignal): Promise<PredictResponse> {
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
    try {
      const errData = await response.json();
      errorMessage = errData.detail || errorMessage;
    } catch {
      // Ignored
    }
    throw new ApiError(errorMessage, response.status);
  }

  return response.json();
}
