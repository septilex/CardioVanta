/** Access tokens live only in memory. Refresh credentials stay in an HttpOnly cookie. */
export type Account = { id: string; email: string; roles: string[] };
export type ImportState = { id: string; status: "ready" | "validating" | "importing" | "completed" | "failed"; row_count: number; notice?: string };
export const workspaceBase = process.env.NEXT_PUBLIC_API_BASE_URL || "";
let access = "";
let refreshing: Promise<Account | null> | null = null;

export function setAccess(value: string) { access = value; }
export function getAccess() { return access; }

export async function workspaceRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (access) headers.set("Authorization", `Bearer ${access}`);
  if (typeof options.body === "string") headers.set("Content-Type", "application/json");
  const response = await fetch(`${workspaceBase}/api/v1${path}`, { ...options, headers, credentials: "include", cache: "no-store" });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : "The request could not be completed. Please try again.";
    throw new Error(detail + (response.status === 429 ? ` Retry in ${response.headers.get("Retry-After") || "60"} seconds.` : ""));
  }
  return data as T;
}

export function refreshAccount(): Promise<Account | null> {
  if (!refreshing) {
    refreshing = workspaceRequest<{ access_token: string; user: Account }>("/auth/refresh", { method: "POST" })
      .then(result => { setAccess(result.access_token); return result.user; })
      .catch(() => { setAccess(""); return null; })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

/** Browser scheduling: synchronous state work precedes Promise microtasks, then timer tasks.
 * Used to let React flush the import-start status before beginning the file transfer. */
export function afterStatusUpdate(onPhase: (phase: "sync" | "microtask" | "timer") => void = () => {}): Promise<void> {
  onPhase("sync");
  return new Promise(resolve => {
    Promise.resolve().then(() => onPhase("microtask"));
    setTimeout(() => { onPhase("timer"); resolve(); }, 0);
  });
}
