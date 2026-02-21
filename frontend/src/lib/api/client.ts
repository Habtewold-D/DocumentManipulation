import { getAccessToken } from "@/lib/auth/token-storage";

const API_VERSION_SEGMENT = "/v1";

export function getApiBaseUrl() {
  const raw = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim();

  if (!raw || raw === "/") {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is required (expected format: <backend-origin>/api)");
  }

  const normalized = raw.replace(/\/+$/, "");
  const withoutVersion = normalized.replace(/\/v1$/i, "");
  return `${withoutVersion}${API_VERSION_SEGMENT}`;
}

const API_BASE_URL = getApiBaseUrl();

function buildUrl(baseUrl: string, path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && !(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const requestInit: RequestInit = {
    ...init,
    headers,
  };

  const response = await fetch(buildUrl(API_BASE_URL, path), requestInit);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}
