import { Wrench } from "lucide-react";

type Props = {
  tools: string[];
  loading: boolean;
  error: string | null;
};

export function ToolsCatalogPanel({ tools, loading, error }: Props) {
  return (
    <section className="rounded-xl border border-primary/10 gradient-card p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Wrench className="h-4 w-4" />
        </div>
        <p className="text-sm font-medium">Available tools</p>
      </div>
      {loading ? <p className="text-xs text-muted-foreground animate-pulse-soft">Loading tools...</p> : null}
      {error ? <p className="text-xs text-destructive">{error}</p> : null}
      {!loading && !error ? (
        <div className="flex flex-wrap gap-2 stagger-children">
          {tools.map((tool) => (
            <span
              key={tool}
              className="animate-fade-in rounded-full border border-primary/10 bg-gradient-to-r from-primary/5 to-primary/10 px-3 py-1 text-xs font-medium text-foreground transition-colors hover:from-primary/10 hover:to-primary/20"
            >
              {tool}
            </span>
          ))}
          {tools.length === 0 ? <p className="text-xs text-muted-foreground">No tools found.</p> : null}
        </div>
      ) : null}
    </section>
  );
}
