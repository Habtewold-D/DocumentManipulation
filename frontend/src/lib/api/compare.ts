import { apiRequest } from "@/lib/api/client";

export type CompareResponse = {
  document_id: string;
  from_version: string;
  to_version: string;
  changed_pages: number[];
};

export async function compareVersions(documentId: string, fromVersion: string, toVersion: string) {
  const params = new URLSearchParams({ from: fromVersion, to: toVersion });
  return apiRequest<CompareResponse>(`/documents/${documentId}/compare?${params.toString()}`);
}
