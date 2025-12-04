"use client";

import { useState } from "react";

import { runCommand } from "@/lib/api/commands";
import type { CommandRunResponse } from "@/lib/types/api";

export function useCommandRun(documentId: string) {
  const [result, setResult] = useState<CommandRunResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async (command: string) => {
    setLoading(true);
    try {
      const response = await runCommand(documentId, command);
      setResult(response);
      return response;
    } finally {
      setLoading(false);
    }
  };

  return { result, loading, run };
}
