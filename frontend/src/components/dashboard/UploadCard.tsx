"use client";

import { useState } from "react";
import { Upload, FileUp, Loader2 } from "lucide-react";
import { useDocuments } from "@/hooks/useDocuments";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = {
  onUploaded?: () => Promise<unknown>;
};

export function UploadCard({ onUploaded }: Props) {
  const { upload, loading, error } = useDocuments();
  const [file, setFile] = useState<File | null>(null);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;
    const result = await upload(file);
    if (result) {
      setFile(null);
      if (onUploaded) {
        await onUploaded();
      }
    }
  };

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <label className="flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed border-primary/20 bg-primary/[0.03] p-8 transition-colors hover:border-primary/40 hover:bg-primary/[0.06]">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Upload className="h-6 w-6" />
        </div>
        <div className="text-center">
          <p className="font-medium text-foreground">Drop a PDF here or click to browse</p>
          <p className="mt-1 text-xs text-muted-foreground">{file ? file.name : "Only .pdf files are accepted"}</p>
        </div>
        <Input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="sr-only"
          required
        />
      </label>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button disabled={loading || !file} type="submit" className="gap-2 gradient-primary border-0 text-white shadow-sm hover:shadow-md transition-shadow">
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Uploading...
          </>
        ) : (
          <>
            <FileUp className="h-4 w-4" />
            Upload
          </>
        )}
      </Button>
    </form>
  );
}
