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
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <UploadCard onUploaded={fetchDocuments} />
      <DocumentTable documents={documents} />
    </main>
  );
}
