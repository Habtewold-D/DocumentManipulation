"use client";

import { useCallback, useState } from "react";

import { acceptDraft, listVersions, rejectDraft } from "@/lib/api/versions";
import type { VersionItem } from "@/lib/types/domain";

export function useVersions(documentId: string) {
  const [versions, setVersions] = useState<VersionItem[]>([]);

  const fetchVersions = useCallback(async () => {
    if (!documentId) return [];
    const items = await listVersions(documentId);
    setVersions(items);
    return items;
  }, [documentId]);

  const accept = useCallback(
    async (draftId: string) => {
      await acceptDraft(documentId, draftId);
      return fetchVersions();
    },
    [documentId, fetchVersions],
  );

  const reject = useCallback(
    async (draftId: string) => {
      await rejectDraft(documentId, draftId);
      return fetchVersions();
    },
    [documentId, fetchVersions],
  );

  return { versions, fetchVersions, accept, reject };
}
