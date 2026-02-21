"use client";

import { GitBranch, Check, X, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { VersionItem } from "@/lib/types/domain";

type Props = {
  versions: VersionItem[];
  onAccept: (id: string) => Promise<unknown>;
  onReject: (id: string) => Promise<unknown>;
};

function stateBadgeClass(state: string): string {
  switch (state) {
    case "accepted":
      return "badge-accepted";
    case "rejected":
      return "badge-rejected";
    default:
      return "badge-draft";
  }
}

export function VersionSidebar({ versions, onAccept, onReject }: Props) {
  return (
    <aside className="rounded-xl border border-primary/10 gradient-card p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <GitBranch className="h-4 w-4" />
        </div>
        <p className="text-sm font-medium">Versions</p>
        {versions.length > 0 && (
          <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
            {versions.length}
          </span>
        )}
      </div>

      <div className="space-y-2 stagger-children">
        {versions.map((version, index) => (
          <div key={version.version_id} className="animate-fade-in relative">
            {/* Timeline connector */}
            {index < versions.length - 1 && (
              <div className="absolute left-4 top-full h-2 w-0.5 bg-border" />
            )}
            <div className="rounded-lg border border-primary/10 bg-background/50 p-3 text-sm">
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${stateBadgeClass(version.state)}`}>
                  {version.state}
                </span>
                <span className="ml-auto font-mono text-xs text-muted-foreground">
                  {version.version_id.slice(0, 8)}
                </span>
              </div>
              <p className="mt-1.5 flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {new Date(version.created_at).toLocaleString()}
              </p>
              {version.state === "draft" ? (
                <div className="mt-2.5 flex gap-2">
                  <Button
                    size="sm"
                    className="gap-1 bg-success text-success-foreground border-0 hover:bg-success/90 shadow-sm"
                    onClick={() => void onAccept(version.version_id)}
                  >
                    <Check className="h-3.5 w-3.5" />
                    Accept
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1 border-destructive/30 text-destructive hover:bg-destructive/10"
                    onClick={() => void onReject(version.version_id)}
                  >
                    <X className="h-3.5 w-3.5" />
                    Reject
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {versions.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <GitBranch className="h-5 w-5" />
          </div>
          <p className="text-xs text-muted-foreground">No versions yet.</p>
        </div>
      ) : null}
    </aside>
  );
}
