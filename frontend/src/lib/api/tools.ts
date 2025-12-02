import { apiRequest } from "@/lib/api/client";

export type ToolCatalogItem = {
  name: string;
  title: string;
  description: string;
  input_schema: Record<string, unknown>;
};

export async function listTools() {
  return apiRequest<ToolCatalogItem[]>("/tools");
}
