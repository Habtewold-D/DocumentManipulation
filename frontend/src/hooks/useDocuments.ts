"use client";

import { useEffect, useState } from "react";

import { listDocuments } from "@/lib/api/documents";
import type { DocumentSummary } from "@/lib/types/domain";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    listDocuments()
      .then(setDocuments)
      .finally(() => setLoading(false));
  }, []);

  return { documents, loading };
}
