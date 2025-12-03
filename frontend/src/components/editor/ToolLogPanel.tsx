import type { ToolLogItem } from "@/lib/types/domain";

type Props = {
  logs: ToolLogItem[];
};

export function ToolLogPanel({ logs }: Props) {
  return (
    <section className="rounded border p-3">
      <p className="mb-2 text-sm font-medium">Tool logs</p>
      <div className="space-y-2">
        {logs.map((log) => (
          <div key={log.id} className="rounded border p-2 text-xs">
            <p>
              <strong>{log.tool_name}</strong> • {log.status}
            </p>
            {log.error_message ? <p className="text-destructive">{log.error_message}</p> : null}
          </div>
        ))}
        {logs.length === 0 ? <p className="text-xs text-muted-foreground">No tool logs.</p> : null}
      </div>
    </section>
  );
}
