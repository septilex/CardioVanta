/**
 * Server-only loading of research evaluations for request-time rendering (/research/evaluations).
 *
 * RESEARCH_API_ORIGIN is a SERVER environment variable (never NEXT_PUBLIC_, never in the browser bundle) naming the
 * FastAPI origin reachable from the Next.js server: http://backend:8000 in Docker Compose, the deployment's own
 * https origin on Vercel. Unset means "not configured": the page says so instead of rendering stale or invented
 * numbers. The path is fixed, so the variable cannot be used to reach arbitrary URLs.
 */
import type { ResearchEvaluations } from "./api";

export type ServerEvaluations =
  | { kind: "ready"; data: ResearchEvaluations }
  | { kind: "unavailable"; message: string };

const TIMEOUT_MS = 5000;

function isEvaluations(value: unknown): value is ResearchEvaluations {
  const v = value as ResearchEvaluations;
  return !!v && Array.isArray(v.evaluations) && Array.isArray(v.version_coverage) && Array.isArray(v.unevaluated_cohorts);
}

export async function loadEvaluationsOnServer(): Promise<ServerEvaluations> {
  const origin = process.env.RESEARCH_API_ORIGIN?.trim();
  if (!origin || !/^https?:\/\/[^\s/]+$/.test(origin)) {
    return { kind: "unavailable", message: "Server rendering of research data is not configured in this environment." };
  }
  try {
    // no-store: read PostgreSQL (through the API and its Redis cache) on every request, never at build time.
    const response = await fetch(`${origin}/api/v1/research/evaluations`, {
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const body: unknown = await response.json().catch(() => null);
    if (response.ok && isEvaluations(body)) return { kind: "ready", data: body };
    if (response.status === 503) {
      return { kind: "unavailable", message: "The research database is temporarily unavailable." };
    }
  } catch {
    // network error or timeout: fall through to the generic message (details are not shown to readers)
  }
  return { kind: "unavailable", message: "Research data could not be loaded right now." };
}
