import { apiRequest } from "@/lib/api/client";
import type { ToolLogItem } from "@/lib/types/domain";

export async function listToolLogs(documentId: string) {
  return apiRequest<ToolLogItem[]>(`/documents/${documentId}/tool-logs`);
}
