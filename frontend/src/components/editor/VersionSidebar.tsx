"use client";

import type { VersionItem } from "@/lib/types/domain";

type Props = {
  versions: VersionItem[];
  onAccept: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
};

export function VersionSidebar({ versions, onAccept, onReject }: Props) {
  return (
    <aside className="space-y-2 rounded border p-3">
      <p className="text-sm font-medium">Versions</p>
      {versions.map((version) => (
        <div key={version.id} className="rounded border p-2 text-sm">
          <p className="font-medium">{version.label ?? version.status}</p>
          <p className="text-xs text-muted-foreground">{new Date(version.created_at).toLocaleString()}</p>
          {version.status === "draft" ? (
            <div className="mt-2 flex gap-2">
              <button className="text-xs underline" onClick={() => void onAccept(version.id)}>
                Accept
              </button>
              <button className="text-xs underline" onClick={() => void onReject(version.id)}>
                Reject
              </button>
            </div>
          ) : null}
        </div>
      ))}
      {versions.length === 0 ? <p className="text-xs text-muted-foreground">No versions.</p> : null}
    </aside>
  );
}
