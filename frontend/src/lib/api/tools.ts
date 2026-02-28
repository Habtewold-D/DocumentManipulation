import { apiRequest } from "@/lib/api/client";

type ToolsResponse = {
  tools: string[];
};

const SUPPORTED_TOOLS = new Set([
  "replace_text",
  "add_text",
  "search_replace",
  "change_font_size",
  "change_font_color",
  "set_text_style",
  "convert_case",
  "highlight_text",
  "underline_text",
  "strikethrough_text",
  "extract_text",
]);

export async function listTools() {
  const response = await apiRequest<ToolsResponse>("/tools");
  return response.tools.filter((tool) => SUPPORTED_TOOLS.has(tool));
}
