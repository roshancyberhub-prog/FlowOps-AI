"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { importEnded, type ImportJob, type ImportRow } from "@/lib/imports";
import type { Page } from "@/lib/executions";
import { useWorkspace } from "@/components/workspace";
import {
  Pagination,
  QueryFeedback,
  Status,
} from "@/features/executions/shared";

export default function ImportDetail() {
  const { id } = useParams<{ id: string }>();
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const job = useQuery({
    queryKey: ["import", organization.id, id],
    queryFn: () => api<ImportJob>(`/leads/imports/${id}`, {}, organization.id),
    refetchInterval: (query) =>
      query.state.data && importEnded(query.state.data.status) ? false : 2500,
  });
  const records = useQuery({
    queryKey: ["import-rows", organization.id, id, status, page],
    queryFn: () =>
      api<Page<ImportRow>>(
        `/leads/imports/${id}/rows?page=${page}${status ? `&status=${status}` : ""}`,
        {},
        organization.id,
      ),
    refetchInterval: job.data && importEnded(job.data.status) ? false : 2500,
  });
  const jobStatus = job.data?.status;
  useEffect(() => {
    if (jobStatus && importEnded(jobStatus)) {
      client.invalidateQueries({ queryKey: ["import-rows", organization.id, id] });
      client.invalidateQueries({ queryKey: ["imports", organization.id] });
      client.invalidateQueries({ queryKey: ["leads", organization.id] });
    }
  }, [jobStatus, client, organization.id, id]);
  return (
    <>
      <Link
        href="/imports"
        className="text-xs font-semibold text-teal-800 hover:underline"
      >
        ← All imports
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">
        Import report
      </h1>
      <QueryFeedback
        pending={job.isPending}
        error={job.error}
        retry={() => job.refetch()}
      />
      {job.data && (
        <>
          <section className="panel my-6 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h2 className="break-all text-lg font-semibold">
                {job.data.filename}
              </h2>
              <div data-testid="import-status">
                <Status value={job.data.status} />
              </div>
            </div>
            <label htmlFor="import-progress" className="mt-5">
              {job.data.processed_rows} of {job.data.total_rows} records
              processed
            </label>
            <progress
              id="import-progress"
              className="h-3 w-full accent-teal-700"
              value={job.data.processed_rows}
              max={job.data.total_rows}
            />
            <dl className="mt-6 grid grid-cols-3 gap-4">
              <div>
                <dt className="text-xs text-slate-500">Inserted</dt>
                <dd
                  className="mt-1 text-2xl font-semibold text-teal-800"
                  data-testid="import-inserted"
                >
                  {job.data.inserted_rows}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Invalid</dt>
                <dd
                  className="mt-1 text-2xl font-semibold"
                  data-testid="import-invalid"
                >
                  {job.data.invalid_rows}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Duplicates skipped</dt>
                <dd
                  className="mt-1 text-2xl font-semibold"
                  data-testid="import-duplicates"
                >
                  {job.data.duplicate_rows}
                </dd>
              </div>
            </dl>
            {job.data.status === "succeeded" && (
              <p className="mt-5 rounded-lg bg-teal-50 p-3 text-sm text-teal-800">
                Processing finished. Review invalid and duplicate records below.
                Existing leads were preserved.
              </p>
            )}
            {job.data.error_summary && (
              <p role="alert" className="notice mt-5">
                {job.data.error_code}: {job.data.error_summary} Previously
                committed records remain in your workspace.
              </p>
            )}
            <Link
              href="/leads"
              className="mt-5 inline-block text-sm font-semibold text-teal-800 hover:underline"
            >
              View leads →
            </Link>
            <details className="mt-4 text-xs text-slate-500">
              <summary className="cursor-pointer">
                Request and column mapping
              </summary>
              <p className="mt-2 break-all">
                Request: {job.data.correlation_id}
              </p>
              <pre className="mt-3 overflow-auto whitespace-pre-wrap break-all">
                {JSON.stringify(job.data.column_mapping, null, 2)}
              </pre>
            </details>
          </section>
          <section className="panel overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 p-5">
              <h2 className="font-semibold">Record results</h2>
              <div className="w-48">
                <label htmlFor="record-status">Filter records</label>
                <select
                  id="record-status"
                  value={status}
                  onChange={(event) => {
                    setStatus(event.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">All records</option>
                  <option value="inserted">Inserted</option>
                  <option value="invalid">Invalid</option>
                  <option value="duplicate">Duplicates</option>
                </select>
              </div>
            </div>
            <QueryFeedback
              pending={records.isPending}
              error={records.error}
              retry={() => records.refetch()}
            />
            {records.data && (
              <>
                {!records.data.items.length ? (
                  <p className="p-8 text-slate-500">
                    No results for this filter yet.
                  </p>
                ) : (
                  <div className="relative min-w-0 overflow-auto">
                    <table className="min-w-[700px]">
                      <thead>
                        <tr>
                          <th>Record</th>
                          <th>Email</th>
                          <th>Result</th>
                          <th>Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {records.data.items.map((row) => (
                          <tr key={row.row_number}>
                            <td>{row.row_number}</td>
                            <td className="max-w-64 break-all text-xs">
                              {row.email ?? row.input_values.email ?? "—"}
                            </td>
                            <td>
                              <Status value={row.status} />
                            </td>
                            <td className="max-w-sm text-xs">
                              {row.errors.map((error, index) => (
                                <p
                                  key={index}
                                  className="mb-2 break-words text-slate-600"
                                >
                                  {error.field}: {error.message}
                                </p>
                              ))}
                              <details>
                                <summary className="cursor-pointer font-semibold text-teal-800">
                                  Record details
                                </summary>
                                <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-all rounded bg-slate-50 p-2">
                                  {JSON.stringify(row.input_values, null, 2)}
                                </pre>
                              </details>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <Pagination
                  page={page}
                  total={records.data.total}
                  size={100}
                  change={setPage}
                />
              </>
            )}
          </section>
        </>
      )}
    </>
  );
}
