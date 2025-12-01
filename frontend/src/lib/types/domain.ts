export type DocumentSummary = {
  document_id: string;
  name: string;
  created_at: string;
};

export type VersionItem = {
  version_id: string;
  state: string;
  created_at: string;
};

export type ToolLogItem = {
  log_id: string;
  tool: string;
  status: string;
  created_at: string;
};
