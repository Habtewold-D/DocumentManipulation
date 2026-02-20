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

export function buildDocumentPreviewUrl(documentId: string, accessToken?: string | null) {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const tokenQuery = accessToken ? `?access_token=${encodeURIComponent(accessToken)}` : "";
  return `${base}/documents/${documentId}/preview${tokenQuery}`;
}
