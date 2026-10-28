"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Approval, Page } from "@/lib/executions";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import {
  Pagination,
  QueryFeedback,
  Status,
} from "@/features/executions/shared";

export default function ApprovalsPage() {
  const { organization } = useWorkspace();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("pending");
  const approvals = useQuery({
    queryKey: ["approvals", organization.id, page, status],
    queryFn: () =>
      api<Page<Approval>>(
        `/approvals?page=${page}${status ? `&status=${status}` : ""}`,
        {},
        organization.id,
      ),
    refetchInterval: 5000,
  });
  return (
    <>
      <p className="eyebrow mb-2">A deliberate pause</p>
      <h1 className="text-3xl font-semibold tracking-tight">Approvals</h1>
      <p className="mb-6 mt-2 text-slate-500">
        Review the current request before a workflow continues. Owners and
        administrators can decide.
      </p>
      <div className="mb-5 max-w-xs">
        <label htmlFor="approval-status">Status</label>
        <select
          id="approval-status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All decisions</option>
          {["pending", "approved", "rejected", "expired", "cancelled"].map(
            (s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ),
          )}
        </select>
      </div>
      <QueryFeedback
        pending={approvals.isPending}
        error={approvals.error}
        retry={() => approvals.refetch()}
      />
      {approvals.data && (
        <>
          {!approvals.data.items.length ? (
            <section className="panel p-12 text-center">
              <h2 className="font-semibold">No approvals to review.</h2>
              <p className="mt-2 text-slate-500">
                Workflow checkpoints appear here when a run pauses.
              </p>
            </section>
          ) : (
            <div className="space-y-4">
              {approvals.data.items.map((approval) => (
                <ApprovalCard key={approval.id} approval={approval} />
              ))}
            </div>
          )}
          <Pagination
            page={page}
            total={approvals.data.total}
            size={25}
            change={setPage}
          />
        </>
      )}
    </>
  );
}
function ApprovalCard({ approval }: { approval: Approval }) {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [comment, setComment] = useState("");
  const decision = useMutation({
    mutationFn: (action: string) =>
      api<Approval>(
        `/approvals/${approval.id}/${action}`,
        {
          method: "POST",
          body: JSON.stringify({
            revision: approval.revision,
            payload_hash: approval.payload_hash,
            comment,
          }),
        },
        organization.id,
      ),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["approvals", organization.id] });
      client.invalidateQueries({
        queryKey: ["execution", organization.id, approval.execution_id],
      });
    },
  });
  const allowed = ["owner", "admin"].includes(organization.role);
  const draft = approval.payload.draft as
    | {
        subject?: string;
        body?: string;
        recipient?: string;
        simulated?: boolean;
        provider?: string;
      }
    | undefined;
  return (
    <article className="panel p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">
            {approval.kind === "email"
              ? "Review email draft"
              : "Review workflow checkpoint"}
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Revision {approval.revision} · Expires{" "}
            {new Date(approval.expires_at).toLocaleString()}
          </p>
        </div>
        <Status value={approval.status} />
      </div>
      <p className="mt-5 whitespace-pre-wrap break-words">
        {String(approval.payload.message ?? "")}
      </p>
      {draft?.simulated && (
        <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          Mock AI draft · No live AI call was made. Email delivery is simulated
          in the development demo.
        </p>
      )}
      {approval.payload.mode === "test" && (
        <p className="mt-3 text-xs font-semibold text-slate-500">
          Test execution · protected actions stay simulated
        </p>
      )}
      {draft && (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="break-words text-xs text-slate-500">
            To: {draft.recipient}
          </p>
          <h3 className="mt-3 break-words font-semibold">{draft.subject}</h3>
          <p className="mt-3 whitespace-pre-wrap break-words">{draft.body}</p>
        </div>
      )}
      <Link
        href={`/executions/${approval.execution_id}`}
        className="mt-4 inline-block text-sm font-semibold text-teal-800 hover:underline"
      >
        Inspect execution →
      </Link>
      {approval.status === "pending" && allowed && (
        <div className="mt-5">
          <label htmlFor={`comment-${approval.id}`}>
            Decision note (optional)
          </label>
          <textarea
            id={`comment-${approval.id}`}
            maxLength={1000}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            disabled={decision.isPending}
          />
          <div className="mt-3 flex gap-3">
            <Button
              disabled={decision.isPending}
              onClick={() => decision.mutate("approve")}
            >
              Approve and continue
            </Button>
            <Button
              variant="outline"
              disabled={decision.isPending}
              onClick={() => decision.mutate("reject")}
            >
              Reject
            </Button>
          </div>
        </div>
      )}
      {approval.decision_comment && (
        <p className="mt-4 break-words text-sm text-slate-500">
          Decision note: {approval.decision_comment}
        </p>
      )}
      {decision.error && (
        <p role="alert" className="notice mt-4">
          {decision.error.message}
        </p>
      )}
    </article>
  );
}
