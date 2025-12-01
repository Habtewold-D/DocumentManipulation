"use client";

import { useEffect, useState } from "react";

import { listToolLogs } from "@/lib/api/logs";
import type { ToolLogItem } from "@/lib/types/domain";

export function useToolLogs(documentId: string) {
  const [logs, setLogs] = useState<ToolLogItem[]>([]);

  useEffect(() => {
    listToolLogs(documentId).then(setLogs);
  }, [documentId]);

  return { logs, refresh: () => listToolLogs(documentId).then(setLogs) };
}
