type Props = {
  url?: string;
};

export function PdfPreview({ url }: Props) {
  return (
    <section className="rounded-lg border bg-card p-3">
      <p className="mb-2 text-sm font-medium">Preview</p>
      {url ? (
        <iframe title="PDF Preview" src={url} className="h-125 w-full rounded-md border" />
      ) : (
        <p className="text-sm text-muted-foreground">No preview available.</p>
      )}
    </section>
  );
}
