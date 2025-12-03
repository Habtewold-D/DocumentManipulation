"use client";

import { useEffect, useMemo } from "react";
import { useParams } from "next/navigation";
import { useAuthGuard } from "@/lib/auth/auth-guard";
import { useDocumentEditor } from "@/hooks/useDocumentEditor";
import { useVersions } from "@/hooks/useVersions";
import { useCommandRun } from "@/hooks/useCommandRun";
import { useToolLogs } from "@/hooks/useToolLogs";
import { CommandBox } from "@/components/editor/CommandBox";
import { PdfPreview } from "@/components/editor/PdfPreview";
import { VersionSidebar } from "@/components/editor/VersionSidebar";
import { ToolLogPanel } from "@/components/editor/ToolLogPanel";
import { ComparePanel } from "@/components/editor/ComparePanel";

export default function DocumentEditorPage() {
  useAuthGuard();
  const params = useParams<{ documentId: string }>();
  const documentId = useMemo(() => params.documentId, [params.documentId]);

  const { document } = useDocumentEditor(documentId);
  const { versions, fetchVersions, accept, reject } = useVersions(documentId);
  const { run, loading } = useCommandRun(documentId);
  const { logs, fetchLogs } = useToolLogs(documentId);

  useEffect(() => {
    void fetchVersions();
    void fetchLogs();
  }, [fetchLogs, fetchVersions]);

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-4 py-6 lg:grid-cols-4">
      <div className="space-y-4 lg:col-span-3">
        <h1 className="text-xl font-semibold">{document?.filename ?? "Document Editor"}</h1>
        <CommandBox loading={loading} onRun={run} />
        <PdfPreview url={document?.current_url} />
        <ComparePanel compare={null} />
        <ToolLogPanel logs={logs} />
      </div>
      <VersionSidebar versions={versions} onAccept={accept} onReject={reject} />
    </main>
  );
}
