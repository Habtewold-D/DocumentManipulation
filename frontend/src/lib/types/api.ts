export type CommandRunResponse = {
  run_id: string;
  status: string;
  draft_version_id: string;
  created_at: string;
  error?: string | null;
};
