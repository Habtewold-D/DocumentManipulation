import type { CompareResult } from "@/lib/types/domain";

type Props = {
  compare?: CompareResult | null;
};

export function ComparePanel({ compare }: Props) {
  return (
    <section className="rounded border p-3">
      <p className="mb-2 text-sm font-medium">Compare</p>
      {compare ? (
        <p className="text-sm">Changed pages: {compare.changed_pages.join(", ") || "none"}</p>
      ) : (
        <p className="text-xs text-muted-foreground">No comparison selected.</p>
      )}
    </section>
  );
}
