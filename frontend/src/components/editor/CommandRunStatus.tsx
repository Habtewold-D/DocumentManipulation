import { CheckCircle, AlertCircle, Clock, Loader2 } from "lucide-react";
import type { CommandRunResponse } from "@/lib/types/api";

type Props = {
  result: CommandRunResponse | null;
  requestError?: string | null;
};

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return <CheckCircle className="h-4 w-4 text-success" />;
    case "failed":
      return <AlertCircle className="h-4 w-4 text-destructive" />;
    case "running":
      return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
    default:
      return <Clock className="h-4 w-4 text-warning" />;
  }
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "completed":
      return "badge-accepted";
    case "failed":
      return "badge-rejected";
    default:
      return "badge-draft";
  }
}

export function CommandRunStatus({ result, requestError }: Props) {
  if (!result) {
    return (
      <section className="rounded-xl border border-primary/10 gradient-card p-4 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
            <Clock className="h-4 w-4" />
          </div>
          <p className="text-sm font-medium">Latest command run</p>
        </div>
        {requestError ? (
          <p className="mt-3 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {requestError}
          </p>
        ) : (
          <p className="mt-2 text-xs text-muted-foreground">No command run yet.</p>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-primary/10 gradient-card p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <StatusIcon status={result.status} />
        <p className="text-sm font-medium">Latest command run</p>
        <span className={`ml-auto rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadgeClass(result.status)}`}>
          {result.status}
        </span>
      </div>
      <div className="mt-3 space-y-1.5 text-xs">
        <p>
          <span className="text-muted-foreground">Draft Version:</span>{" "}
          <span className="font-mono font-medium">{result.draft_version_id.slice(0, 12)}</span>
        </p>
        <p>
          <span className="text-muted-foreground">Created:</span>{" "}
          <span className="font-medium">{new Date(result.created_at).toLocaleString()}</span>
        </p>
        {result.error ? (
          <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive">{result.error}</p>
        ) : null}
        {requestError ? (
          <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive">{requestError}</p>
        ) : null}
      </div>
    </section>
  );
}
