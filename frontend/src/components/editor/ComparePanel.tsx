"use client";

import { useMemo, useState } from "react";

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
    <section className="rounded-lg border bg-card p-3">
      <p className="text-sm font-medium">Compare versions</p>
      <p className="mt-1 text-xs text-muted-foreground">Pick two accepted versions to see changed pages.</p>

      <form onSubmit={onSubmit} className="mt-3 grid gap-2 sm:grid-cols-2">
        <select
          value={fromVersion}
          onChange={(event) => setFromVersion(event.target.value)}
          className="h-9 rounded-md border bg-background px-3 text-sm"
        >
          <option value="">From version</option>
          {acceptedVersions.map((version) => (
            <option key={version.version_id} value={version.version_id}>
              {version.version_id.slice(0, 8)} · {new Date(version.created_at).toLocaleDateString()}
            </option>
          ))}
        </select>

        <select
          value={toVersion}
          onChange={(event) => setToVersion(event.target.value)}
          className="h-9 rounded-md border bg-background px-3 text-sm"
        >
          <option value="">To version</option>
          {acceptedVersions.map((version) => (
            <option key={version.version_id} value={version.version_id}>
              {version.version_id.slice(0, 8)} · {new Date(version.created_at).toLocaleDateString()}
            </option>
          ))}
        </select>

        <div className="sm:col-span-2">
          <Button type="submit" disabled={!canRun || loading}>
            {loading ? "Comparing..." : "Compare"}
          </Button>
        </div>
      </form>

      {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}

      {compare ? (
        <p className="mt-2 rounded-md border bg-muted/40 p-2 text-sm">
          Changed pages: <span className="font-medium">{compare.changed_pages.join(", ") || "none"}</span>
        </p>
      ) : null}

      {!compare && !error ? (
        <p className="mt-2 text-xs text-muted-foreground">No comparison run yet.</p>
      ) : null}
    </section>
  );
}
