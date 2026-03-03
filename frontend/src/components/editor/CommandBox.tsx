"use client";

import { useState } from "react";
import { Sparkles, Send, Loader2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import Image from "next/image";
import { uploadImage } from "@/lib/api/upload";

type Props = {
  onRun: (command: string, imageUrl?: string | null) => Promise<unknown>;
  loading?: boolean;
};

export function CommandBox({ onRun, loading }: Props) {
  const [command, setCommand] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = command.trim();
    if (!value) return;
    console.log("uploadedImageUrl:", uploadedImageUrl);
    await onRun(value, uploadedImageUrl);
    setCommand("");
    setUploadedImageUrl(null);
  };

  const onFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const url = await uploadImage(file);
      setUploadedImageUrl(url);
    } catch (error) {
      console.error("Upload failed:", error);
      // Optionally show error to user
    } finally {
      setUploading(false);
    }
  };

  const removeImage = () => {
    setUploadedImageUrl(null);
  };

  return (
    <form onSubmit={onSubmit} className="space-y-3 rounded-xl border border-primary/10 gradient-card p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-medium">Command</p>
          <p className="text-xs text-muted-foreground">Describe the change you want to apply to this document.</p>
        </div>
      </div>
      <Textarea
        value={command}
        onChange={(e) => setCommand(e.target.value)}
        placeholder="e.g. insert image at the top of the first page"
        className="min-h-24 border-primary/10 bg-background/50 focus-visible:ring-primary/30"
      />
      {uploadedImageUrl && (
        <div className="flex items-center gap-2 p-2 border border-primary/10 rounded-lg">
          <Image src={uploadedImageUrl} alt="Uploaded" width={64} height={64} className="object-cover rounded" />
          <div className="flex-1">
            <p className="text-xs text-muted-foreground">Uploaded image</p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={removeImage}>
            Remove
          </Button>
        </div>
      )}
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <Upload className="h-4 w-4 text-primary" />
          <span className="text-xs text-muted-foreground">Upload Image</span>
          <input
            type="file"
            accept="image/*"
            onChange={onFileChange}
            disabled={uploading}
            className="hidden"
          />
        </label>
        {uploading && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
      </div>
      <Button
        type="submit"
        disabled={loading || !command.trim()}
        className="gap-2 gradient-primary border-0 text-white shadow-sm hover:shadow-md transition-shadow"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Running...
          </>
        ) : (
          <>
            <Send className="h-4 w-4" />
            Run Command
          </>
        )}
      </Button>
    </form>
  );
}
