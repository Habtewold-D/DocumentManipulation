type Props = {
  url?: string;
};

export function PdfPreview({ url }: Props) {
  return (
    <div className="rounded border p-3">
      <p className="mb-2 text-sm font-medium">Preview</p>
      {url ? (
        <iframe title="PDF Preview" src={url} className="h-125 w-full rounded" />
      ) : (
        <p className="text-sm text-muted-foreground">No preview available.</p>
      )}
    </div>
  );
}
