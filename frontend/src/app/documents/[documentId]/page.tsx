"use client";

import { useEffect, useMemo, useSyncExternalStore, useState } from "react";
import { useParams } from "next/navigation";
import { useAuthGuard } from "@/lib/auth/auth-guard";
import { getAccessToken, subscribeAuthToken } from "@/lib/auth/token-storage";
import { useDocumentEditor } from "@/hooks/useDocumentEditor";
import { useVersions } from "@/hooks/useVersions";
import { useCommandRun } from "@/hooks/useCommandRun";
import { useToolLogs } from "@/hooks/useToolLogs";
import { useCompare } from "@/hooks/useCompare";
import { useToolsCatalog } from "@/hooks/useToolsCatalog";
import { buildDocumentPreviewUrl } from "@/lib/api/documents";
import { buildVersionPreviewUrl } from "@/lib/api/versions";
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
  const accessToken = useSyncExternalStore(subscribeAuthToken, getAccessToken, () => null);
  const [previewMode, setPreviewMode] = useState<"current" | "draft">("draft");

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

  const fromVersionUrl = compareResult?.from_version
    ? buildVersionPreviewUrl(documentId, compareResult.from_version, accessToken)
    : null;
  const toVersionUrl = compareResult?.to_version
    ? buildVersionPreviewUrl(documentId, compareResult.to_version, accessToken)
    : null;
  const currentPreviewUrl = documentId ? buildDocumentPreviewUrl(documentId, accessToken) : undefined;
  const latestDraft = useMemo(() => versions.find((version) => version.state === "draft"), [versions]);
  const draftPreviewUrl = latestDraft
    ? buildVersionPreviewUrl(documentId, latestDraft.version_id, accessToken)
    : undefined;
  const activePreviewUrl = previewMode === "draft" && draftPreviewUrl ? draftPreviewUrl : currentPreviewUrl;

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-4 py-6 lg:grid-cols-12">
      <div className="space-y-4 lg:col-span-8">
        <section className="rounded-lg border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Document Workspace</p>
          <h1 className="mt-1 text-xl font-semibold">{document?.name ?? "Document Editor"}</h1>
        </section>
        <CommandBox loading={loading} onRun={onRunCommand} />
        <CommandRunStatus result={result} requestError={runError} />
        <section className="rounded-lg border bg-card p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-medium">Preview</p>
              <p className="text-xs text-muted-foreground">
                {previewMode === "draft" && latestDraft ? "Previewing latest draft" : "Previewing current version"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className={`rounded-full border px-3 py-1 text-xs ${
                  previewMode === "current" ? "bg-muted/60" : "bg-transparent"
                }`}
                onClick={() => setPreviewMode("current")}
              >
                Current
              </button>
              <button
                type="button"
                className={`rounded-full border px-3 py-1 text-xs ${
                  previewMode === "draft" ? "bg-muted/60" : "bg-transparent"
                }`}
                onClick={() => setPreviewMode("draft")}
                disabled={!latestDraft}
              >
                Draft
              </button>
            </div>
          </div>
          <div className="mt-3">
            <PdfPreview url={activePreviewUrl} />
          </div>
        </section>
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
