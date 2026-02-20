"use client";

import { useEffect } from "react";
import { useAuthGuard } from "@/lib/auth/auth-guard";
import { useDocuments } from "@/hooks/useDocuments";
import { UploadCard } from "@/components/dashboard/UploadCard";
import { DocumentTable } from "@/components/dashboard/DocumentTable";

export default function DashboardPage() {
  useAuthGuard();
  const { documents, fetchDocuments } = useDocuments();

  useEffect(() => {
    void fetchDocuments();
  }, [fetchDocuments]);

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <section className="rounded-lg border bg-card p-5">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage PDFs, run edit commands, and review versions.</p>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h2 className="mb-3 text-lg font-semibold">Upload</h2>
        <UploadCard onUploaded={fetchDocuments} />
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h2 className="mb-3 text-lg font-semibold">Your documents</h2>
        <DocumentTable documents={documents} />
      </section>
    </main>
  );
}
