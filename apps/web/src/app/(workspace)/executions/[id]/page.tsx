"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DeliveryHistory } from "@/features/outreach/delivery-history";
import { api } from "@/lib/api";
import {
  ended,
  humanize,
  type Execution,
  type ExecutionStep,
  type Page,
} from "@/lib/executions";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import {
  Pagination,
  QueryFeedback,
  Status,
} from "@/features/executions/shared";

export default function ExecutionDetail() {
  const { id } = useParams<{ id: string }>();
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const run = useQuery({
    queryKey: ["execution", organization.id, id],
    queryFn: () => api<Execution>(`/executions/${id}`, {}, organization.id),
    refetchInterval: (query) =>
      query.state.data && ended(query.state.data.status) ? false : 2500,
  });
  const steps = useQuery({
    queryKey: ["execution-steps", organization.id, id, page],
    queryFn: () =>
      api<Page<ExecutionStep>>(
        `/executions/${id}/steps?page=${page}`,
        {},
        organization.id,
      ),
    refetchInterval: run.data && ended(run.data.status) ? false : 2500,
  });
  const runStatus = run.data?.status;
  useEffect(() => {
    if (runStatus && ended(runStatus)) {
      client.invalidateQueries({ queryKey: ["execution-steps", organization.id, id] });
      client.invalidateQueries({ queryKey: ["leads", organization.id] });
      client.invalidateQueries({ queryKey: ["lead", organization.id] });
      client.invalidateQueries({ queryKey: ["lead-drafts", organization.id] });
      client.invalidateQueries({ queryKey: ["draft", organization.id] });
    }
  }, [runStatus, client, organization.id, id]);
  const control = useMutation({
    mutationFn: (action: string) =>
      api<Execution>(
        `/executions/${id}/${action}`,
        { method: "POST" },
        organization.id,
      ),
    onSuccess: (result) => {
      client.setQueryData(["execution", organization.id, id], result);
      client.invalidateQueries({
        queryKey: ["execution-steps", organization.id, id],
      });
    },
  });
  const lastStep = steps.data?.items.at(-1);
  const writable = organization.role !== "viewer";
  return (
    <>
      <Link
        href="/executions"
        className="text-xs font-semibold text-teal-800 hover:underline"
      >
        ← All executions
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">
        Execution details
      </h1>
      <QueryFeedback
        pending={run.isPending}
        error={run.error}
        retry={() => run.refetch()}
      />
      {run.data && (
        <>
          <section className="panel my-6 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">
                  {run.data.workflow_name}
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                  Published version {run.data.version_number} ·{" "}
                  <span className="capitalize">{run.data.mode}</span> mode
                </p>
              </div>
              <div data-testid="execution-status">
                <Status value={run.data.status} />
              </div>
            </div>
            <dl className="mt-6 grid gap-5 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-xs text-slate-500">Requested</dt>
                <dd className="mt-1">
                  {new Date(run.data.created_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Active processing</dt>
                <dd className="mt-1">
                  {(run.data.active_duration_ms / 1000).toFixed(2)} seconds
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Current node</dt>
                <dd className="mt-1 break-all font-mono text-xs">
                  {run.data.current_node_id ?? "Complete"}
                </dd>
              </div>
            </dl>
            {run.data.error_summary && (
              <p role="alert" className="notice mt-5">
                {run.data.error_code}: {run.data.error_summary}
                {run.data.dead_letter && " · Saved for review."}
              </p>
            )}
            {run.data.cancel_requested && !ended(run.data.status) && (
              <p role="status" className="mt-4 text-sm text-slate-500">
                Cancellation requested. The current step will reach a safe
                stopping point.
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-3">
              {run.data.status === "waiting_for_approval" && (
                <Button asChild>
                  <Link href="/approvals">Review pending approval</Link>
                </Button>
              )}
              {writable && !ended(run.data.status) && (
                <Button
                  variant="outline"
                  disabled={control.isPending || run.data.cancel_requested}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Cancel this run at the next safe boundary? Completed actions are retained.",
                      )
                    )
                      control.mutate("cancel");
                  }}
                >
                  Cancel run
                </Button>
              )}
              {writable &&
                run.data.status === "failed" &&
                lastStep?.retryable &&
                !lastStep.uncertain && (
                  <Button
                    disabled={control.isPending}
                    onClick={() => control.mutate("retry")}
                  >
                    Retry eligible failure
                  </Button>
                )}
              <Button asChild variant="outline">
                <Link href={`/workflows/${run.data.workflow_id}`}>
                  Open workflow
                </Link>
              </Button>
            </div>
            {control.error && (
              <p role="alert" className="notice mt-4">
                {control.error.message}
              </p>
            )}
            <details className="mt-5 text-xs text-slate-500">
              <summary className="cursor-pointer">
                Run identifiers and context
              </summary>
              <p className="mt-3 break-all">
                Execution: {id}
                <br />
                Request: {run.data.correlation_id}
              </p>
              <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-50 p-3">
                {JSON.stringify(run.data.context, null, 2)}
              </pre>
            </details>
          </section>
          <section className="panel overflow-hidden">
            <div className="border-b border-slate-200 px-6 py-4">
              <h2 className="font-semibold">Step timeline</h2>
              <p className="mt-1 text-xs text-slate-500">
                Every recorded attempt stays visible, including retries.
              </p>
            </div>
            <QueryFeedback
              pending={steps.isPending}
              error={steps.error}
              retry={() => steps.refetch()}
            />
            {steps.data && (
              <>
                {!steps.data.items.length ? (
                  <p className="p-8 text-slate-500">
                    No steps recorded yet. Queued runs wait for an available
                    worker.
                  </p>
                ) : (
                  <ol className="divide-y divide-slate-100">
                    {steps.data.items.map((step) => (
                      <li key={step.id} className="p-6">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="font-semibold">
                              {humanize(
                                step.node_type.split(".").at(-1) ??
                                  step.node_type,
                              )}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {step.node_id} · Attempt {step.attempt_number} ·{" "}
                              {step.duration_ms === null
                                ? "In progress"
                                : `${step.duration_ms} ms`}
                            </p>
                          </div>
                          <Status value={step.status} />
                        </div>
                        {step.error_summary && (
                          <p className="notice mt-4">
                            {step.error_code}: {step.error_summary}
                            {step.uncertain &&
                              " External outcome needs reconciliation."}
                          </p>
                        )}
                        <details className="mt-3 text-xs">
                          <summary className="cursor-pointer font-semibold text-teal-800">
                            Inputs, outputs, and failure details
                          </summary>
                          <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-50 p-3">
                            {JSON.stringify(
                              {
                                input: step.input_summary,
                                output: step.output_summary,
                                ...(step.error_frames.length
                                  ? { frames: step.error_frames }
                                  : {}),
                              },
                              null,
                              2,
                            )}
                          </pre>
                        </details>
                      </li>
                    ))}
                  </ol>
                )}
                <Pagination
                  page={page}
                  total={steps.data.total}
                  size={100}
                  change={setPage}
                />
              </>
            )}
          </section>
          <DeliveryHistory
            executionId={id}
            active={
              !ended(run.data.status) &&
              run.data.status !== "waiting_for_approval"
            }
          />
        </>
      )}
    </>
  );
}
