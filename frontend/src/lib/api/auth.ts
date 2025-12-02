import { apiRequest } from "@/lib/api/client";

export type LoginPayload = { email: string; password: string };
export type RegisterPayload = { email: string; password: string; full_name?: string };

export async function login(payload: LoginPayload) {
  return apiRequest<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function register(payload: RegisterPayload) {
  return apiRequest<{ user_id: string; email: string; full_name?: string; created_at: string }>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
