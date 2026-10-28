export type Execution = {
  id: string;
  workflow_id: string;
  workflow_name: string;
  workflow_version_id: string;
  version_number: number;
  status: string;
  mode: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  active_duration_ms: number;
  node_attempt: number;
  current_node_id: string | null;
  correlation_id: string;
  error_code: string | null;
  error_summary: string | null;
  dead_letter: boolean;
  cancel_requested: boolean;
  context: Record<string, unknown>;
};
export type ExecutionStep = {
  id: string;
  node_id: string;
  node_type: string;
  attempt_number: number;
  status: string;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  error_code: string | null;
  error_summary: string | null;
  error_frames: string[];
  retryable: boolean;
  uncertain: boolean;
  duration_ms: number | null;
  started_at: string;
};
export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
export type Approval = {
  id: string;
  execution_id: string;
  node_id: string;
  kind: string;
  status: string;
  payload: Record<string, unknown>;
  payload_hash: string;
  revision: number;
  requested_at: string;
  expires_at: string;
  decision_comment: string;
};
export const ended = (status: string) =>
  ["succeeded", "failed", "cancelled"].includes(status);
export const humanize = (value: string) =>
  value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
