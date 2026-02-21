"use client";

import { useEffect } from "react";
import { LayoutDashboard, Upload, FileText } from "lucide-react";
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
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 animate-fade-in">
      {/* Welcome Banner */}
      <section className="overflow-hidden rounded-xl gradient-primary p-6 text-white shadow-lg">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/20 backdrop-blur-sm">
            <LayoutDashboard className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Dashboard</h1>
            <p className="mt-0.5 text-sm text-white/80">Manage PDFs, run edit commands, and review versions.</p>
          </div>
        </div>
      </section>

      {/* Upload Section */}
      <section className="rounded-xl border border-primary/10 gradient-card p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Upload className="h-4 w-4" />
          </div>
          <h2 className="text-lg font-semibold">Upload</h2>
        </div>
        <UploadCard onUploaded={fetchDocuments} />
      </section>

      {/* Documents Section */}
      <section className="rounded-xl border border-primary/10 gradient-card p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <FileText className="h-4 w-4" />
          </div>
          <h2 className="text-lg font-semibold">Your documents</h2>
        </div>
        <DocumentTable documents={documents} />
      </section>
    </main>
  );
}
