type Props = {
  tools: string[];
  loading: boolean;
  error: string | null;
};

export function ToolsCatalogPanel({ tools, loading, error }: Props) {
  return (
    <section className="rounded-lg border bg-card p-3">
      <p className="text-sm font-medium">Available tools</p>
      {loading ? <p className="mt-2 text-xs text-muted-foreground">Loading tools...</p> : null}
      {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
      {!loading && !error ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {tools.map((tool) => (
            <span key={tool} className="rounded-full border bg-muted/50 px-2 py-1 text-xs">
              {tool}
            </span>
          ))}
          {tools.length === 0 ? <p className="text-xs text-muted-foreground">No tools found.</p> : null}
        </div>
      ) : null}
    </section>
  );
}
