import { getAccessToken } from "@/lib/auth/token-storage";

function getDefaultApiBaseUrl() {
  if (typeof window !== "undefined") {
    const host = window.location.hostname || "localhost";
    return `http://${host}:8000/api/v1`;
  }
  return "http://localhost:8000/api/v1";
}

export function getApiBaseUrl() {
  const raw = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim();

  if (!raw || raw === "/") {
    return getDefaultApiBaseUrl();
  }

  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw.replace(/\/+$/, "");
  }

  if (raw.startsWith("/api/")) {
    if (typeof window !== "undefined") {
      return `${window.location.origin}${raw}`.replace(/\/+$/, "");
    }
    return raw.replace(/\/+$/, "");
  }

  return getDefaultApiBaseUrl();
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

  let response: Response;
  try {
    response = await fetch(buildUrl(API_BASE_URL, path), requestInit);
  } catch (error) {
    if (typeof window !== "undefined") {
      const retryBase = `http://${window.location.hostname}:8000/api/v1`;
      response = await fetch(buildUrl(retryBase, path), requestInit);
    } else {
      throw error;
    }
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}
