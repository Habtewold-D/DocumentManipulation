"use client";

import Link from "next/link";
import { FileText, Clock, ChevronRight } from "lucide-react";
import type { DocumentSummary } from "@/lib/types/domain";

type Props = {
  documents: DocumentSummary[];
};

export function DocumentTable({ documents }: Props) {
  return (
    <div className="space-y-2 stagger-children">
      {documents.map((doc) => (
        <Link
          key={doc.document_id}
          href={`/documents/${doc.document_id}`}
          className="animate-fade-in group flex items-center gap-3 rounded-xl border border-primary/10 bg-card p-4 transition-all hover:shadow-md hover:border-primary/25 hover:-translate-y-0.5"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-white">
            <FileText className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{doc.name}</p>
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {new Date(doc.created_at).toLocaleString()}
            </p>
          </div>
          <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
        </Link>
      ))}
      {documents.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <FileText className="h-6 w-6" />
          </div>
          <p className="text-sm text-muted-foreground">No documents yet. Upload your first PDF above.</p>
        </div>
      ) : null}
    </div>
  );
}
