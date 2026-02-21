import { ScrollText, Circle } from "lucide-react";
import type { ToolLogItem } from "@/lib/types/domain";

type Props = {
  logs: ToolLogItem[];
};

function statusDotColor(status: string): string {
  switch (status) {
    case "completed":
    case "success":
      return "text-success";
    case "failed":
    case "error":
      return "text-destructive";
    default:
      return "text-warning";
  }
}

export function ToolLogPanel({ logs }: Props) {
  return (
    <section className="rounded-xl border border-primary/10 gradient-card p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <ScrollText className="h-4 w-4" />
        </div>
        <p className="text-sm font-medium">Tool logs</p>
        {logs.length > 0 && (
          <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
            {logs.length}
          </span>
        )}
      </div>
      <div className="space-y-1.5 stagger-children">
        {logs.map((log) => (
          <div key={log.log_id} className="animate-fade-in flex items-center gap-2.5 rounded-lg border border-primary/5 bg-background/50 p-2.5 text-xs">
            <Circle className={`h-2.5 w-2.5 fill-current ${statusDotColor(log.status)}`} />
            <span className="font-mono font-medium">{log.tool}</span>
            <span className="ml-auto capitalize text-muted-foreground">{log.status}</span>
          </div>
        ))}
        {logs.length === 0 ? (
          <p className="py-4 text-center text-xs text-muted-foreground">No tool logs.</p>
        ) : null}
      </div>
    </section>
  );
}
