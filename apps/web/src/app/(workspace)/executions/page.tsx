"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Execution, Page } from "@/lib/executions";
import { humanize } from "@/lib/executions";
import { useWorkspace } from "@/components/workspace";
import {
  Pagination,
  QueryFeedback,
  Status,
} from "@/features/executions/shared";

export default function ExecutionsPage() {
  const { organization } = useWorkspace();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const runs = useQuery({
    queryKey: ["executions", organization.id, page, status],
    queryFn: () =>
      api<Page<Execution>>(
        `/executions?page=${page}${status ? `&status=${status}` : ""}`,
        {},
        organization.id,
      ),
    refetchInterval: 4000,
  });
  const health = useQuery({
    queryKey: ["execution-health", organization.id],
    queryFn: () =>
      api<{
        status: string;
        last_dispatch_at: string | null;
        oldest_due_seconds: number;
        pending_imports: number;
        executions_by_status: Record<string, number>;
        webhooks_by_status: Record<string, number>;
      }>("/execution-health", {}, organization.id),
    refetchInterval: 10000,
  });
  return (
    <>
      <p className="eyebrow mb-2">Every run, accounted for</p>
      <h1 className="text-3xl font-semibold tracking-tight">Executions</h1>
      <p className="mb-6 mt-2 text-slate-500">
        Inspect the published version, attempts, and outcome of each background
        run.
      </p>
      <div className="mb-5 max-w-xs">
        <label htmlFor="execution-status">Status</label>
        <select
          id="execution-status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          {[
            "queued",
            "running",
            "waiting_for_approval",
            "retrying",
            "succeeded",
            "failed",
            "cancelled",
          ].map((s) => (
            <option key={s} value={s}>
              {humanize(s)}
            </option>
          ))}
        </select>
      </div>
      <p className="mb-4 text-xs text-slate-500">
        Worker dispatch:{" "}
        {health.data?.status ??
          (health.error ? "Unable to check" : "Checking…")}
      </p>
      {health.data && (
        <div className="mb-5 grid gap-3 sm:grid-cols-3">
          <div className="panel p-4">
            <p className="text-xs text-slate-500">Runs queued / retrying</p>
            <p className="mt-2 text-xl font-semibold">
              {(health.data.executions_by_status.queued ?? 0) +
                (health.data.executions_by_status.retrying ?? 0)}
            </p>
          </div>
          <div className="panel p-4">
            <p className="text-xs text-slate-500">Oldest due work</p>
            <p className="mt-2 text-xl font-semibold">
              {health.data.oldest_due_seconds} seconds
            </p>
          </div>
          <div className="panel p-4">
            <p className="text-xs text-slate-500">
              Webhooks needing investigation
            </p>
            <p className="mt-2 text-xl font-semibold">
              {(health.data.webhooks_by_status.failed ?? 0) +
                (health.data.webhooks_by_status.uncertain ?? 0)}
            </p>
          </div>
        </div>
      )}
      <section className="panel min-w-0 overflow-hidden">
        <QueryFeedback
          pending={runs.isPending}
          error={runs.error}
          retry={() => runs.refetch()}
        />
        {runs.data && (
          <>
            {!runs.data.items.length ? (
              <div className="p-12 text-center">
                <h2 className="font-semibold">No executions found.</h2>
                <p className="mt-2 text-slate-500">
                  Publish a workflow and start a run from the builder.
                </p>
                <Link
                  className="mt-4 inline-block font-semibold text-teal-800 hover:underline"
                  href="/workflows"
                >
                  Open workflows →
                </Link>
              </div>
            ) : (
              <div className="overflow-auto">
                <table className="min-w-[700px]">
                  <thead>
                    <tr>
                      <th>Workflow</th>
                      <th>Status</th>
                      <th>Mode</th>
                      <th>Active time</th>
                      <th>Started</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.data.items.map((run) => (
                      <tr key={run.id}>
                        <td>
                          <Link
                            className="font-semibold text-teal-800 hover:underline"
                            href={`/executions/${run.id}`}
                          >
                            {run.workflow_name}
                          </Link>
                          <p className="mt-1 text-xs text-slate-500">
                            Version {run.version_number} · {run.id.slice(0, 8)}
                          </p>
                        </td>
                        <td>
                          <Status value={run.status} />
                        </td>
                        <td className="capitalize">{run.mode}</td>
                        <td>{(run.active_duration_ms / 1000).toFixed(2)}s</td>
                        <td className="text-xs text-slate-500">
                          {new Date(run.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <Pagination
              page={page}
              total={runs.data.total}
              size={25}
              change={setPage}
            />
          </>
        )}
      </section>
    </>
  );
}
