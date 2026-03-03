"use client";

import { useState } from "react";

import { getCommandRun, runCommand } from "@/lib/api/commands";
import type { CommandRunResponse } from "@/lib/types/api";
import { toErrorMessage } from "@/lib/utils/errors";

const TERMINAL_STATUSES = new Set(["completed", "failed", "canceled"]);

async function pollUntilDone(runId: string, onUpdate: (result: CommandRunResponse) => void): Promise<CommandRunResponse> {
  let latest = await getCommandRun(runId);
  onUpdate(latest);

  let attempts = 0;
  while (!TERMINAL_STATUSES.has(latest.status) && attempts < 90) {
    await new Promise((resolve) => setTimeout(resolve, 1200));
    latest = await getCommandRun(runId);
    onUpdate(latest);
    attempts += 1;
  }

  return latest;
}

export function useCommandRun(documentId: string) {
  const [result, setResult] = useState<CommandRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (command: string, imageUrl?: string | null) => {
    setLoading(true);
    setError(null);
    try {
      const queued = await runCommand(documentId, command, imageUrl);
      setResult(queued);
      const final = await pollUntilDone(queued.run_id, setResult);
      return final;
    } catch (unknownError) {
      setError(toErrorMessage(unknownError));
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { result, loading, error, run };
}
