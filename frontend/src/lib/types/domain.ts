export type DocumentSummary = {
  document_id: string;
  name: string;
  created_at: string;
  original_url?: string;
  current_url?: string;
};

export type VersionItem = {
  version_id: string;
  state: string;
  pdf_url?: string;
  created_at: string;
};

export type ToolLogItem = {
  log_id: string;
  tool: string;
  status: string;
  created_at: string;
};

export type CompareResult = {
  document_id: string;
  from_version: string;
  to_version: string;
  changed_pages: number[];
};
