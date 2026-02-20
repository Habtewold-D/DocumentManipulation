import { apiRequest } from "@/lib/api/client";

type ToolsResponse = {
  tools: string[];
};

export async function listTools() {
  const response = await apiRequest<ToolsResponse>("/tools");
  return response.tools;
}
