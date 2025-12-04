"use client";

import { useCallback, useEffect, useState } from "react";

import { getDocument } from "@/lib/api/documents";
import type { DocumentSummary } from "@/lib/types/domain";
import { toErrorMessage } from "@/lib/utils/errors";

export function useDocumentEditor(documentId: string) {
  const [document, setDocument] = useState<DocumentSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocument = useCallback(async () => {
    if (!documentId) return null;
    setLoading(true);
    setError(null);
    try {
      const item = await getDocument(documentId);
      setDocument(item);
      return item;
    } catch (unknownError) {
      setError(toErrorMessage(unknownError));
      return null;
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    void fetchDocument();
  }, [fetchDocument]);

  return {
    document,
    loading,
    error,
    fetchDocument,
  };
}
