const TOKEN_KEY = "pdf_agent_token";
const AUTH_EVENT = "auth-token-changed";
const TOKEN_COOKIE_KEY = "pdf_agent_token";

function setTokenCookie(token: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_COOKIE_KEY}=${encodeURIComponent(token)}; path=/; SameSite=Lax`;
}

function clearTokenCookie() {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_COOKIE_KEY}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax`;
}

export function setAccessToken(token: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(TOKEN_KEY, token);
    setTokenCookie(token);
    window.dispatchEvent(new Event(AUTH_EVENT));
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function clearAccessToken() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
    clearTokenCookie();
    window.dispatchEvent(new Event(AUTH_EVENT));
  }
}

export function subscribeAuthToken(callback: () => void) {
  if (typeof window === "undefined") return () => {};

  const listener = () => callback();
  window.addEventListener("storage", listener);
  window.addEventListener(AUTH_EVENT, listener);

  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener(AUTH_EVENT, listener);
  };
}
