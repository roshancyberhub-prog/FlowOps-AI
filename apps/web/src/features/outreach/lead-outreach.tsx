"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useInfiniteQuery, useMutation, useQuery } from "@tanstack/react-query";
import { api, type Lead } from "@/lib/api";
import type { Draft, DraftWorkflow, ProviderStatus } from "@/lib/outreach";
import type { Execution, Page } from "@/lib/executions";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { QueryFeedback, Status } from "@/features/executions/shared";

export function LeadOutreach({ lead }: { lead: Lead }) {
  const { organization } = useWorkspace();
  const router = useRouter();
  const [choice, setChoice] = useState<DraftWorkflow | null>(null);
  const [mode, setMode] = useState("test");
  const [key, setKey] = useState(() => crypto.randomUUID());
  const writable = organization.role !== "viewer" && lead.status !== "archived";
  const providers = useQuery({
    queryKey: ["providers", organization.id],
    queryFn: () =>
      api<ProviderStatus>("/providers/status", {}, organization.id),
  });
  const drafts = useInfiniteQuery({
    queryKey: ["lead-drafts", organization.id, lead.id],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      api<Page<Draft>>(
        `/leads/${lead.id}/drafts?page=${pageParam}`,
        {},
        organization.id,
      ),
    getNextPageParam: (last) =>
      last.page * last.page_size < last.total ? last.page + 1 : undefined,
  });
  const workflows = useInfiniteQuery({
    queryKey: ["draft-workflows", organization.id, lead.id],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      api<Page<DraftWorkflow>>(
        `/leads/${lead.id}/draft-workflows?page=${pageParam}`,
        {},
        organization.id,
      ),
    getNextPageParam: (last) =>
      last.page * last.page_size < last.total ? last.page + 1 : undefined,
    enabled: writable,
  });
  const allChoices = workflows.data?.pages.flatMap((page) => page.items) ?? [];
  const allDrafts = drafts.data?.pages.flatMap((page) => page.items) ?? [];
  const start = useMutation({
    mutationFn: () =>
      api<Execution>(
        `/leads/${lead.id}/drafts`,
        {
          method: "POST",
          headers: { "Idempotency-Key": key },
          body: JSON.stringify({
            workflow_id: choice!.workflow_id,
            workflow_version_id: choice!.version_id,
            mode,
          }),
        },
        organization.id,
      ),
    onSuccess: (run) => router.push(`/executions/${run.id}`),
  });
  return (
    <section
      className="mt-6 rounded-xl border border-slate-200 p-4"
      aria-label="Outreach drafts"
    >
      <h3 className="font-semibold">Outreach drafts</h3>
      <p className="mt-2 text-xs text-slate-500">
        AI: {providers.data?.ai_provider ?? "Checking…"} · Email:{" "}
        {providers.data?.email_provider ?? "Checking…"}
      </p>
      {providers.error && (
        <p role="alert" className="notice mt-3">
          {providers.error.message}
        </p>
      )}
      <QueryFeedback
        pending={drafts.isPending}
        error={drafts.error}
        retry={() => drafts.refetch()}
      />
      {!drafts.isPending && !drafts.error && !allDrafts.length && (
        <p className="mt-4 text-sm text-slate-500">
          No saved drafts for this lead yet.
        </p>
      )}
      <ul className="mt-4 space-y-3">
        {allDrafts.map((draft) => (
          <li key={draft.id} className="rounded-lg bg-slate-50 p-3">
            <Link
              href={`/drafts/${draft.id}`}
              className="break-words font-semibold text-teal-800 hover:underline"
            >
              {draft.subject}
            </Link>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Status value={draft.status} />
              <span className="text-xs text-slate-500">
                Revision {draft.revision} · {draft.ai_metadata.draft.provider}
              </span>
            </div>
          </li>
        ))}
      </ul>
      {drafts.hasNextPage && (
        <Button
          type="button"
          variant="outline"
          className="mt-3"
          disabled={drafts.isFetchingNextPage}
          onClick={() => drafts.fetchNextPage()}
        >
          Load older drafts
        </Button>
      )}
      {writable && (
        <div className="mt-5 border-t border-slate-200 pt-4">
          <h4 className="text-sm font-semibold">
            Start a reviewed draft workflow
          </h4>
          <p className="mt-2 text-xs text-slate-500">
            Published workflows keep approval checkpoints before protected
            sending. Mock outputs are labelled and do not contact a real AI or
            email provider.
          </p>
          {workflows.error && (
            <p role="alert" className="notice mt-3">
              {workflows.error.message}
            </p>
          )}
          <label htmlFor={`draft-workflow-${lead.id}`} className="mt-4">
            Published workflow
          </label>
          <select
            id={`draft-workflow-${lead.id}`}
            value={choice?.version_id ?? ""}
            disabled={start.isPending || workflows.isPending}
            onChange={(event) => {
              setChoice(
                allChoices.find(
                  (item) => item.version_id === event.target.value,
                ) ?? null,
              );
              setKey(crypto.randomUUID());
            }}
          >
            <option value="">Choose a workflow</option>
            {choice &&
              !allChoices.some(
                (item) => item.version_id === choice.version_id,
              ) && (
                <option value={choice.version_id}>
                  {choice.name} · v{choice.version_number}
                </option>
              )}
            {allChoices.map((item) => (
              <option
                key={item.version_id}
                value={item.version_id}
                disabled={!item.can_run}
              >
                {item.name} · v{item.version_number}
                {!item.can_run ? " · Requires another role" : ""}
              </option>
            ))}
          </select>
          {workflows.hasNextPage && (
            <Button
              type="button"
              variant="outline"
              className="mt-2"
              onClick={() => workflows.fetchNextPage()}
              disabled={workflows.isFetchingNextPage}
            >
              Load more workflows
            </Button>
          )}
          <label htmlFor={`draft-mode-${lead.id}`} className="mt-3">
            Run mode
          </label>
          <select
            id={`draft-mode-${lead.id}`}
            value={mode}
            disabled={start.isPending}
            onChange={(event) => {
              setMode(event.target.value);
              setKey(crypto.randomUUID());
            }}
          >
            <option value="test">Test · simulate business changes</option>
            <option value="live">Live · apply business changes</option>
          </select>
          <Button
            type="button"
            className="mt-4"
            disabled={
              !choice ||
              start.isPending ||
              providers.data?.ai_provider !== "mock"
            }
            onClick={() => start.mutate()}
          >
            {start.isPending ? "Starting…" : "Start draft workflow"}
          </Button>
          {providers.data?.ai_provider === "disabled" && (
            <p className="mt-2 text-xs text-slate-500">
              Draft generation is disabled in this environment.
            </p>
          )}
          {start.error && (
            <p role="alert" className="notice mt-3">
              {start.error.message}
            </p>
          )}
          <Link
            href="/workflows"
            className="mt-3 block text-xs font-semibold text-teal-800 hover:underline"
          >
            Open workflow builder →
          </Link>
        </div>
      )}
    </section>
  );
}
