import { API_BASE_URL, ApiError } from './api';
import type { PredictResponse } from '../types';
export interface AIResponse {
  summary: string;
  prediction_interpretation: string;
  contributing_factors: { feature_name: string; contribution_direction: string; plain_language_explanation: string }[];
  limitations: string[];
  recommended_next_step: string;
  disclaimer: string;
  prompt_version: string;
}
export function minimizeResult(result: PredictResponse) {
  return { token: result.explanation_token };
}
export async function aiEnabled(signal: AbortSignal): Promise<boolean> {
  const r = await fetch(`${API_BASE_URL}/api/v1/ai/status`, { signal, cache: 'no-store' });
  return r.ok && (await r.json()).enabled === true;
}
export async function explainResult(result: PredictResponse, signal: AbortSignal): Promise<AIResponse> {
  const r = await fetch(`${API_BASE_URL}/api/v1/ai/explanation`, { method: 'POST', signal,
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(minimizeResult(result)), cache: 'no-store' });
  if (!r.ok) throw new ApiError('AI explanation unavailable', r.status);
  return r.json();
}
