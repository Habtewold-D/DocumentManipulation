"use client";

import { useMemo, useState } from "react";
import { GitCompareArrows, Loader2, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { CompareResult, VersionItem } from "@/lib/types/domain";

type Props = {
  compare?: CompareResult | null;
  versions: VersionItem[];
  loading: boolean;
  error: string | null;
  onCompare: (fromVersion: string, toVersion: string) => Promise<unknown>;
};

export function ComparePanel({ compare, versions, loading, error, onCompare }: Props) {
  const acceptedVersions = useMemo(() => versions.filter((version) => version.state === "accepted"), [versions]);
  const [fromVersion, setFromVersion] = useState("");
  const [toVersion, setToVersion] = useState("");

  const canRun = Boolean(fromVersion && toVersion && fromVersion !== toVersion);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canRun) return;
    await onCompare(fromVersion, toVersion);
  };

  return (
    <section className="rounded-xl border border-primary/10 gradient-card p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[oklch(0.93_0.05_310)] text-[oklch(0.45_0.18_310)]">
          <GitCompareArrows className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-medium">Compare versions</p>
          <p className="text-xs text-muted-foreground">Pick two accepted versions to see changed pages.</p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-[1fr_auto_1fr]">
        <select
          value={fromVersion}
          onChange={(event) => setFromVersion(event.target.value)}
          className="h-9 rounded-lg border border-primary/15 bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="">From version</option>
          {acceptedVersions.map((version) => (
            <option key={version.version_id} value={version.version_id}>
              {version.version_id.slice(0, 8)} · {new Date(version.created_at).toLocaleDateString()}
            </option>
          ))}
        </select>

        <div className="hidden sm:flex items-center justify-center">
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>

        <select
          value={toVersion}
          onChange={(event) => setToVersion(event.target.value)}
          className="h-9 rounded-lg border border-primary/15 bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="">To version</option>
          {acceptedVersions.map((version) => (
            <option key={version.version_id} value={version.version_id}>
              {version.version_id.slice(0, 8)} · {new Date(version.created_at).toLocaleDateString()}
            </option>
          ))}
        </select>

        <div className="sm:col-span-3">
          <Button type="submit" disabled={!canRun || loading} className="gap-2 gradient-primary border-0 text-white shadow-sm hover:shadow-md transition-shadow">
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Comparing...
              </>
            ) : (
              <>
                <GitCompareArrows className="h-4 w-4" />
                Compare
              </>
            )}
          </Button>
        </div>
      </form>

      {error ? <p className="mt-3 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">{error}</p> : null}

      {compare ? (
        <div className="mt-3 rounded-lg bg-primary/5 border border-primary/10 p-3">
          <p className="text-sm text-foreground">
            Changed pages:{" "}
            {compare.changed_pages.length > 0 ? (
              <span className="inline-flex flex-wrap gap-1.5">
                {compare.changed_pages.map((page) => (
                  <span key={page} className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    Page {page}
                  </span>
                ))}
              </span>
            ) : (
              <span className="text-muted-foreground">none</span>
            )}
          </p>
        </div>
      ) : null}

      {!compare && !error ? (
        <p className="mt-3 text-xs text-muted-foreground">No comparison run yet.</p>
      ) : null}
    </section>
  );
}
