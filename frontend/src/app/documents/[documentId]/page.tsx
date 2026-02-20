"use client";

import { useEffect, useMemo } from "react";
import { useParams } from "next/navigation";
import { useAuthGuard } from "@/lib/auth/auth-guard";
import { useDocumentEditor } from "@/hooks/useDocumentEditor";
import { useVersions } from "@/hooks/useVersions";
import { useCommandRun } from "@/hooks/useCommandRun";
import { useToolLogs } from "@/hooks/useToolLogs";
import { useCompare } from "@/hooks/useCompare";
import { useToolsCatalog } from "@/hooks/useToolsCatalog";
import { CommandBox } from "@/components/editor/CommandBox";
import { PdfPreview } from "@/components/editor/PdfPreview";
import { VersionSidebar } from "@/components/editor/VersionSidebar";
import { ToolLogPanel } from "@/components/editor/ToolLogPanel";
import { ComparePanel } from "@/components/editor/ComparePanel";
import { CommandRunStatus } from "@/components/editor/CommandRunStatus";
import { ToolsCatalogPanel } from "@/components/editor/ToolsCatalogPanel";

export default function DocumentEditorPage() {
  useAuthGuard();
  const params = useParams<{ documentId?: string }>();
  const documentId = useMemo(() => params.documentId ?? "", [params.documentId]);

  const { document, fetchDocument } = useDocumentEditor(documentId);
  const { versions, fetchVersions, accept, reject } = useVersions(documentId);
  const { run, loading, result, error: runError } = useCommandRun(documentId);
  const { logs, fetchLogs } = useToolLogs(documentId);
  const { compareResult, loading: compareLoading, error: compareError, runCompare } = useCompare(documentId);
  const { tools, loading: toolsLoading, error: toolsError, fetchTools } = useToolsCatalog();

  const onAccept = async (draftId: string) => {
    await accept(draftId);
    await Promise.all([fetchVersions(), fetchLogs()]);
  };

  const onReject = async (draftId: string) => {
    await reject(draftId);
    await Promise.all([fetchVersions(), fetchLogs()]);
  };

  const onRunCommand = async (command: string) => {
    await run(command);
    await Promise.all([fetchVersions(), fetchLogs(), fetchDocument()]);
  };

  useEffect(() => {
    if (!documentId) return;
    void Promise.all([fetchVersions(), fetchLogs(), fetchTools(), fetchDocument()]);
  }, [documentId, fetchDocument, fetchLogs, fetchTools, fetchVersions]);

  const fromVersionUrl =
    versions.find((version) => version.version_id === compareResult?.from_version)?.pdf_url ?? null;
  const toVersionUrl =
    versions.find((version) => version.version_id === compareResult?.to_version)?.pdf_url ?? null;

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-4 py-6 lg:grid-cols-12">
      <div className="space-y-4 lg:col-span-8">
        <section className="rounded-lg border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Document Workspace</p>
          <h1 className="mt-1 text-xl font-semibold">{document?.name ?? "Document Editor"}</h1>
        </section>
        <CommandBox loading={loading} onRun={onRunCommand} />
        <CommandRunStatus result={result} requestError={runError} />
        <PdfPreview url={document?.current_url ?? document?.original_url} />
        <ComparePanel
          compare={compareResult}
          versions={versions}
          loading={compareLoading}
          error={compareError}
          onCompare={runCompare}
        />
        {compareResult ? (
          <section className="grid gap-4 rounded-lg border bg-card p-3 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">From version</p>
              <PdfPreview url={fromVersionUrl ?? undefined} />
            </div>
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">To version</p>
              <PdfPreview url={toVersionUrl ?? undefined} />
            </div>
          </section>
        ) : null}
        <ToolLogPanel logs={logs} />
      </div>

      <div className="space-y-4 lg:col-span-4">
        <VersionSidebar versions={versions} onAccept={onAccept} onReject={onReject} />
        <ToolsCatalogPanel tools={tools} loading={toolsLoading} error={toolsError} />
      </div>
    </main>
  );
}
