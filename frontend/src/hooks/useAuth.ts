"use client";

import { useMemo } from "react";

import { getAccessToken } from "@/lib/auth/token-storage";

export function useAuth() {
  const token = getAccessToken();

  return useMemo(
    () => ({
      isAuthenticated: Boolean(token),
      token,
    }),
    [token],
  );
}
