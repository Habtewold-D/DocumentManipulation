"use client";

import Link from "next/link";
import type { DocumentSummary } from "@/lib/types/domain";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Props = {
  documents: DocumentSummary[];
};

export function DocumentTable({ documents }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Documents</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {documents.map((doc) => (
            <Link
              key={doc.id}
              href={`/documents/${doc.id}`}
              className="block rounded border p-3 hover:bg-muted/40"
            >
              <p className="font-medium">{doc.filename}</p>
              <p className="text-xs text-muted-foreground">Created: {new Date(doc.created_at).toLocaleString()}</p>
            </Link>
          ))}
          {documents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No documents yet.</p>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
