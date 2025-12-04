import { apiRequest } from "@/lib/api/client";
import type { DocumentSummary } from "@/lib/types/domain";

export async function listDocuments() {
  return apiRequest<DocumentSummary[]>("/documents");
}

export async function getDocument(documentId: string) {
  return apiRequest<DocumentSummary>(`/documents/${documentId}`);
}

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<DocumentSummary & { original_asset_id: string }>("/documents/upload", {
    method: "POST",
    body: formData,
  });
}
