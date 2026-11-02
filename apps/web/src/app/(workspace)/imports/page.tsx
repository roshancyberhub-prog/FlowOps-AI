"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ImportJob } from "@/lib/imports";
import type { Page } from "@/lib/executions";
import { useWorkspace } from "@/components/workspace";
import { ImportUpload } from "@/features/imports/upload";
import {
  Pagination,
  QueryFeedback,
  Status,
} from "@/features/executions/shared";

export default function ImportsPage() {
  const { organization } = useWorkspace();
  const [page, setPage] = useState(1);
  const jobs = useQuery({
    queryKey: ["imports", organization.id, page],
    queryFn: () =>
      api<Page<ImportJob>>(`/leads/imports?page=${page}`, {}, organization.id),
    refetchInterval: 4000,
  });
  return (
    <>
      <p className="eyebrow mb-2">Bring your pipeline together</p>
      <h1 className="text-3xl font-semibold tracking-tight">CSV imports</h1>
      <p className="mb-6 mt-2 text-slate-500">
        Background processing with a clear result for every record.
      </p>
      {organization.role !== "viewer" && <ImportUpload />}
      <section className="panel overflow-hidden">
        <div className="border-b border-slate-200 p-5">
          <h2 className="font-semibold">Import history</h2>
        </div>
        <QueryFeedback
          pending={jobs.isPending}
          error={jobs.error}
          retry={() => jobs.refetch()}
        />
        {jobs.data && (
          <>
            {!jobs.data.items.length ? (
              <p className="p-10 text-center text-slate-500">
                No imports yet. Upload a CSV to create a processing report.
              </p>
            ) : (
              <div className="relative min-w-0 overflow-auto">
                <table className="min-w-[720px]">
                  <thead>
                    <tr>
                      <th>File</th>
                      <th>Status</th>
                      <th>Processed</th>
                      <th>Inserted</th>
                      <th>Issues / duplicates</th>
                      <th>Requested</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.data.items.map((job) => (
                      <tr key={job.id}>
                        <td>
                          <Link
                            className="font-semibold text-teal-800 hover:underline"
                            href={`/imports/${job.id}`}
                          >
                            {job.filename}
                          </Link>
                        </td>
                        <td>
                          <Status value={job.status} />
                        </td>
                        <td>
                          {job.processed_rows}/{job.total_rows}
                        </td>
                        <td>{job.inserted_rows}</td>
                        <td>
                          {job.invalid_rows} / {job.duplicate_rows}
                        </td>
                        <td className="text-xs text-slate-500">
                          {new Date(job.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <Pagination
              page={page}
              total={jobs.data.total}
              size={25}
              change={setPage}
            />
          </>
        )}
      </section>
    </>
  );
}
