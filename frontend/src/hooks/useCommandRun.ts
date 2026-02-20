"use client";

import { useState } from "react";

import { runCommand } from "@/lib/api/commands";
import type { CommandRunResponse } from "@/lib/types/api";
import { toErrorMessage } from "@/lib/utils/errors";

export function useCommandRun(documentId: string) {
  const [result, setResult] = useState<CommandRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (command: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await runCommand(documentId, command);
      setResult(response);
      return response;
    } catch (unknownError) {
      setError(toErrorMessage(unknownError));
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { result, loading, error, run };
}
