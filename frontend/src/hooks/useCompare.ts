"use client";

import { useCallback, useState } from "react";

import { compareVersions } from "@/lib/api/compare";
import type { CompareResult } from "@/lib/types/domain";
import { toErrorMessage } from "@/lib/utils/errors";

export function useCompare(documentId: string) {
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runCompare = useCallback(
    async (fromVersion: string, toVersion: string) => {
      if (!documentId || !fromVersion || !toVersion) return null;
      setLoading(true);
      setError(null);
      try {
        const result = await compareVersions(documentId, fromVersion, toVersion);
        setCompareResult(result);
        return result;
      } catch (unknownError) {
        setError(toErrorMessage(unknownError));
        setCompareResult(null);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [documentId],
  );

  return {
    compareResult,
    loading,
    error,
    runCompare,
  };
}
