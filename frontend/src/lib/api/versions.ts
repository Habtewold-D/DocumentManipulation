import { apiRequest } from "@/lib/api/client";
import type { VersionItem } from "@/lib/types/domain";

export async function listVersions(documentId: string) {
  return apiRequest<VersionItem[]>(`/documents/${documentId}/versions`);
}

export async function acceptDraft(documentId: string, draftId: string) {
  return apiRequest<VersionItem>(`/documents/${documentId}/drafts/${draftId}/accept`, { method: "POST" });
}

export async function rejectDraft(documentId: string, draftId: string) {
  return apiRequest<VersionItem>(`/documents/${documentId}/drafts/${draftId}/reject`, { method: "POST" });
}

export function buildVersionPreviewUrl(documentId: string, versionId: string, accessToken?: string | null) {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const tokenQuery = accessToken ? `?access_token=${encodeURIComponent(accessToken)}` : "";
  return `${base}/documents/${documentId}/versions/${versionId}/preview${tokenQuery}`;
}
