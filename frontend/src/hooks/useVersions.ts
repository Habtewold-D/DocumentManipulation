"use client";

import { useEffect, useState } from "react";

import { listVersions } from "@/lib/api/versions";
import type { VersionItem } from "@/lib/types/domain";

export function useVersions(documentId: string) {
  const [versions, setVersions] = useState<VersionItem[]>([]);

  useEffect(() => {
    listVersions(documentId).then(setVersions);
  }, [documentId]);

  return { versions, refresh: () => listVersions(documentId).then(setVersions) };
}
