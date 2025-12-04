"use client";

import { useCallback, useMemo, useState } from "react";

import { login as loginRequest, register as registerRequest } from "@/lib/api/auth";
import { getAccessToken } from "@/lib/auth/token-storage";
import { setAccessToken } from "@/lib/auth/token-storage";
import { toErrorMessage } from "@/lib/utils/errors";

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = getAccessToken();

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await loginRequest({ email, password });
      setAccessToken(response.access_token);
      return true;
    } catch (unknownError) {
      setError(toErrorMessage(unknownError));
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    setLoading(true);
    setError(null);
    try {
      await registerRequest({ email, password, full_name: fullName || undefined });
      return true;
    } catch (unknownError) {
      setError(toErrorMessage(unknownError));
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return useMemo(
    () => ({
      isAuthenticated: Boolean(token),
      token,
      loading,
      error,
      login,
      register,
    }),
    [error, loading, login, register, token],
  );
}
