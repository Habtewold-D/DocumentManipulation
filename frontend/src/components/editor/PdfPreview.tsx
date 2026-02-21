import { Eye, FileText } from "lucide-react";

type Props = {
  url?: string;
};

export function PdfPreview({ url }: Props) {
  return (
    <section className="rounded-xl border border-primary/10 gradient-card p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Eye className="h-4 w-4" />
        </div>
        <p className="text-sm font-medium">Preview</p>
      </div>
      {url ? (
        <iframe title="PDF Preview" src={url} className="h-125 w-full rounded-lg border border-primary/10" />
      ) : (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-primary/15 bg-muted/30 py-12">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <FileText className="h-6 w-6" />
          </div>
          <p className="text-sm text-muted-foreground">No preview available.</p>
        </div>
      )}
    </section>
  );
}
