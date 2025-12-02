import { apiRequest } from "@/lib/api/client";
import type { CommandRunResponse } from "@/lib/types/api";

export async function runCommand(documentId: string, command: string) {
  return apiRequest<CommandRunResponse>(`/documents/${documentId}/commands`, {
    method: "POST",
    body: JSON.stringify({ command }),
  });
}
