"use client";

import Link from "next/link";
import type { DocumentSummary } from "@/lib/types/domain";

type Props = {
  documents: DocumentSummary[];
};

export function DocumentTable({ documents }: Props) {
  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <Link
          key={doc.document_id}
          href={`/documents/${doc.document_id}`}
          className="block rounded-md border bg-muted/10 p-3 transition-colors hover:bg-muted/30"
        >
          <p className="font-medium">{doc.name}</p>
          <p className="text-xs text-muted-foreground">Created: {new Date(doc.created_at).toLocaleString()}</p>
        </Link>
      ))}
      {documents.length === 0 ? <p className="text-sm text-muted-foreground">No documents yet.</p> : null}
    </div>
  );
}
