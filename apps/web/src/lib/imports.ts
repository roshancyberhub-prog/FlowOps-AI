export type ImportJob = {
  id: string;
  status: string;
  filename: string;
  column_mapping: Record<string, string>;
  total_rows: number;
  processed_rows: number;
  inserted_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  failure_count: number;
  error_code: string | null;
  error_summary: string | null;
  correlation_id: string;
  created_at: string;
  completed_at: string | null;
};
export type ImportRow = {
  row_number: number;
  status: string;
  email: string | null;
  input_values: Record<string, string>;
  errors: { field: string; message: string }[];
  lead_id: string | null;
};
export type ImportPreview = {
  headers: string[];
  row_count: number;
  suggested_mapping: Record<string, string>;
  max_bytes: number;
  max_rows: number;
};
export const importEnded = (status: string) =>
  ["succeeded", "failed"].includes(status);
