"use client";

import { useCallback, useState } from "react";

import { listDocuments, uploadDocument } from "@/lib/api/documents";
import type { DocumentSummary } from "@/lib/types/domain";
import { toErrorMessage } from "@/lib/utils/errors";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listDocuments();
      setDocuments(items);
      return items;
    } catch (unknownError) {
      setError(toErrorMessage(unknownError));
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const upload = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        const uploaded = await uploadDocument(file);
        setDocuments((previous) => [uploaded, ...previous]);
        return uploaded;
      } catch (unknownError) {
        setError(toErrorMessage(unknownError));
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { documents, loading, error, fetchDocuments, upload };
}
