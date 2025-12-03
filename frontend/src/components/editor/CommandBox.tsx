"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  onRun: (command: string) => Promise<void>;
  loading?: boolean;
};

export function CommandBox({ onRun, loading }: Props) {
  const [command, setCommand] = useState("");

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = command.trim();
    if (!value) return;
    await onRun(value);
  };

  return (
    <form onSubmit={onSubmit} className="space-y-2">
      <Textarea
        value={command}
        onChange={(e) => setCommand(e.target.value)}
        placeholder="e.g. remove page 2 and add footer"
      />
      <Button type="submit" disabled={loading}>
        {loading ? "Running..." : "Run Command"}
      </Button>
    </form>
  );
}
