import { getAccessToken } from "@/lib/auth/token-storage";

export function isAuthenticated() {
  return Boolean(getAccessToken());
}
