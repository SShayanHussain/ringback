import { ORCHESTRATOR_URL } from "./env";
import { getAccessToken } from "./session";

// Defensive fetch (PLAYBOOK §12.4): read text first, then guarded JSON.parse so a non-JSON error
// body surfaces AS the message instead of crashing res.json().
async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const access = token ?? getAccessToken();
  const res = await fetch(`${ORCHESTRATOR_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
      ...(init.headers || {}),
    },
    cache: "no-store",
  });
  const raw = await res.text();
  let body: any;
  try {
    body = JSON.parse(raw);
  } catch {
    body = { error: { message: raw || `HTTP ${res.status}` } };
  }
  if (!res.ok) {
    throw new Error(body?.error?.message || `HTTP ${res.status}`);
  }
  return body.data as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, data: unknown, token?: string): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(data) }, token);
}

export function apiPut<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, { method: "PUT", body: JSON.stringify(data) });
}
