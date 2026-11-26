const BASE = import.meta.env.VITE_API_URL ?? "";

let csrfToken: string | null = null;
export const setCsrfToken = (t: string | null) => { csrfToken = t; };

// Called when a request that needs a session comes back 401 (the session expired or was revoked),
// so the app can drop its signed-in state and send the user to the sign-in page.
let onUnauthorized: (() => void) | null = null;
export const setUnauthorizedHandler = (fn: (() => void) | null) => { onUnauthorized = fn; };
// 401 here means a wrong password or "no session yet", not an expired session.
const SESSION_PROBES = new Set(["/api/auth/login", "/api/auth/me"]);

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function describeError(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: unknown[]; msg?: string };
    const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : "input";
    return `${field}: ${first.msg ?? "is invalid"}`;
  }
  return fallback;
}

export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && csrfToken) headers["X-CSRF-Token"] = csrfToken;

  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      credentials: "include",
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }
  if (res.status === 401 && !SESSION_PROBES.has(path)) onUnauthorized?.();
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, describeError(body, `Request failed (${res.status}).`));
  return body as T;
}
