"use client";

import { useCallback, useState } from "react";

import { listToolLogs } from "@/lib/api/logs";
import type { ToolLogItem } from "@/lib/types/domain";

export function useToolLogs(documentId: string) {
  const [logs, setLogs] = useState<ToolLogItem[]>([]);

  const fetchLogs = useCallback(async () => {
    if (!documentId) return [];
    const items = await listToolLogs(documentId);
    setLogs(items);
    return items;
  }, [documentId]);

  return { logs, fetchLogs };
}
