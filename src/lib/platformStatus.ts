export interface PlatformHealth {
  backendAvailable: boolean;
  modelServiceAvailable: boolean;
}

const REQUEST_TIMEOUT_MS = 2_500;

function healthUrl(): string | null {
  const configured = process.env.CARDIOVANTA_BACKEND_URL?.trim()
    || process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) {
    try {
      return new URL("/api/v1/health", configured).toString();
    } catch {
      return null;
    }
  }

  // Vercel provides the current deployment host at runtime. Calling its same-origin
  // rewrite keeps the Python function behind vercel.json and needs no public API host.
  const deploymentHost = process.env.VERCEL_URL?.trim();
  if (deploymentHost && /^[a-z0-9.-]+(?::\d+)?$/i.test(deploymentHost)) {
    return `https://${deploymentHost}/api/v1/health`;
  }
  if (process.env.NODE_ENV === "development") return "http://127.0.0.1:8000/api/v1/health";
  return null;
}

export async function getPlatformHealth(fetcher: typeof fetch = fetch): Promise<PlatformHealth> {
  const url = healthUrl();
  if (!url) return { backendAvailable: false, modelServiceAvailable: false };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetcher(url, { cache: "no-store", signal: controller.signal });
    if (!response.ok) return { backendAvailable: true, modelServiceAvailable: false };
    const body: unknown = await response.json();
    const modelServiceAvailable = Boolean(
      body && typeof body === "object"
      && "status" in body && body.status === "ok"
      && "service" in body && body.service === "CardioVanta",
    );
    return { backendAvailable: true, modelServiceAvailable };
  } catch {
    return { backendAvailable: false, modelServiceAvailable: false };
  } finally {
    clearTimeout(timeout);
  }
}
