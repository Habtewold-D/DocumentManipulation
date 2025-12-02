"use client";

import { useState } from "react";
import { useDocuments } from "@/hooks/useDocuments";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function UploadCard() {
  const { upload, loading, error } = useDocuments();
  const [file, setFile] = useState<File | null>(null);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;
    await upload(file);
    setFile(null);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload PDF</CardTitle>
      </CardHeader>
      <CardContent>
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
      </CardContent>
    </Card>
  );
}
