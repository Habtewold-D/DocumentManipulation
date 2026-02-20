import type { CommandRunResponse } from "@/lib/types/api";

type Props = {
  result: CommandRunResponse | null;
  requestError?: string | null;
};

export function CommandRunStatus({ result, requestError }: Props) {
  if (!result) {
    return (
      <section className="rounded-lg border bg-card p-3">
        <p className="text-sm font-medium">Latest command run</p>
        {requestError ? (
          <p className="mt-2 rounded border border-destructive/30 bg-destructive/10 px-2 py-1 text-xs text-destructive">
            {requestError}
          </p>
        ) : (
          <p className="mt-1 text-xs text-muted-foreground">No command run yet.</p>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-card p-3">
      <p className="text-sm font-medium">Latest command run</p>
      <div className="mt-2 space-y-1 text-xs">
        <p>
          <span className="text-muted-foreground">Status:</span> <span className="font-medium">{result.status}</span>
        </p>
        <p>
          <span className="text-muted-foreground">Draft Version:</span> <span className="font-medium">{result.draft_version_id}</span>
        </p>
        <p>
          <span className="text-muted-foreground">Created:</span>{" "}
          <span className="font-medium">{new Date(result.created_at).toLocaleString()}</span>
        </p>
        {result.error ? (
          <p className="rounded border border-destructive/30 bg-destructive/10 px-2 py-1 text-destructive">{result.error}</p>
        ) : null}
        {requestError ? (
          <p className="rounded border border-destructive/30 bg-destructive/10 px-2 py-1 text-destructive">{requestError}</p>
        ) : null}
      </div>
    </section>
  );
}
