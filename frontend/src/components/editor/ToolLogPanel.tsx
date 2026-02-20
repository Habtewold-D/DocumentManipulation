import type { ToolLogItem } from "@/lib/types/domain";

type Props = {
  logs: ToolLogItem[];
};

export function ToolLogPanel({ logs }: Props) {
  return (
    <section className="rounded-lg border bg-card p-3">
      <p className="mb-2 text-sm font-medium">Tool logs</p>
      <div className="space-y-2">
        {logs.map((log) => (
          <div key={log.log_id} className="rounded-md border bg-muted/20 p-2 text-xs">
            <p>
              <strong>{log.tool}</strong> • <span className="capitalize">{log.status}</span>
            </p>
          </div>
        ))}
        {logs.length === 0 ? <p className="text-xs text-muted-foreground">No tool logs.</p> : null}
      </div>
    </section>
  );
}
