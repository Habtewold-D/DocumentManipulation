import { apiRequest } from "@/lib/api/client";
import type { DocumentSummary } from "@/lib/types/domain";

export async function listDocuments() {
  return apiRequest<DocumentSummary[]>("/documents");
}

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<DocumentSummary & { original_asset_id?: string; original_url?: string }>("/documents/upload", {
    method: "POST",
    body: formData,
  });
}
