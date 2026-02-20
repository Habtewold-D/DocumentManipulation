"use client";

import { useState } from "react";
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
    <form className="space-y-3" onSubmit={onSubmit}>
      <Input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        required
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button disabled={loading || !file} type="submit">
        {loading ? "Uploading..." : "Upload"}
      </Button>
    </form>
  );
}
