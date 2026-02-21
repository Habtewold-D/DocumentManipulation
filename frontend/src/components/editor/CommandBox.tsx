"use client";

import { useState } from "react";
import { Sparkles, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  onRun: (command: string) => Promise<unknown>;
  loading?: boolean;
};

export function CommandBox({ onRun, loading }: Props) {
  const [command, setCommand] = useState("");

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = command.trim();
    if (!value) return;
    await onRun(value);
    setCommand("");
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
        placeholder="e.g. remove page 2 and add footer"
        className="min-h-24 border-primary/10 bg-background/50 focus-visible:ring-primary/30"
      />
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
