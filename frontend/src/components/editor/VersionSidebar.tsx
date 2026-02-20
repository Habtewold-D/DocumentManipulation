"use client";

import { Button } from "@/components/ui/button";
import type { VersionItem } from "@/lib/types/domain";

type Props = {
  versions: VersionItem[];
  onAccept: (id: string) => Promise<unknown>;
  onReject: (id: string) => Promise<unknown>;
};

export function VersionSidebar({ versions, onAccept, onReject }: Props) {
  return (
    <aside className="space-y-3 rounded-lg border bg-card p-3">
      <p className="text-sm font-medium">Versions</p>
      {versions.map((version) => (
        <div key={version.version_id} className="rounded-md border bg-muted/20 p-2 text-sm">
          <p className="font-medium capitalize">{version.state}</p>
          <p className="text-xs text-muted-foreground">{new Date(version.created_at).toLocaleString()}</p>
          {version.state === "draft" ? (
            <div className="mt-2 flex gap-2">
              <Button size="sm" onClick={() => void onAccept(version.version_id)}>
                Accept
              </Button>
              <Button size="sm" variant="outline" onClick={() => void onReject(version.version_id)}>
                Reject
              </Button>
            </div>
          ) : null}
        </div>
      ))}
      {versions.length === 0 ? <p className="text-xs text-muted-foreground">No versions.</p> : null}
    </aside>
  );
}
