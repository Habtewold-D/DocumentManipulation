"use client";

import { useState } from "react";
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
    <form onSubmit={onSubmit} className="space-y-3 rounded-lg border bg-card p-3">
      <div>
        <p className="text-sm font-medium">Command</p>
        <p className="text-xs text-muted-foreground">Describe the change you want to apply to this document.</p>
      </div>
      <Textarea
        value={command}
        onChange={(e) => setCommand(e.target.value)}
        placeholder="e.g. remove page 2 and add footer"
        className="min-h-24"
      />
      <Button type="submit" disabled={loading || !command.trim()}>
        {loading ? "Running..." : "Run Command"}
      </Button>
    </form>
  );
}
