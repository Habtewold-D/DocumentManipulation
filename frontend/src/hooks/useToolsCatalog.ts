"use client";

import { useCallback, useState } from "react";

import { listTools } from "@/lib/api/tools";
import { toErrorMessage } from "@/lib/utils/errors";

export function useToolsCatalog() {
  const [tools, setTools] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTools = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listTools();
      setTools(items);
      return items;
    } catch (unknownError) {
      setError(toErrorMessage(unknownError));
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  return { tools, loading, error, fetchTools };
}
