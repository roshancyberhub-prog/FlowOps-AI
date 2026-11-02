"use client";
import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Draft } from "@/lib/outreach";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { QueryFeedback, Status } from "@/features/executions/shared";
import { DraftEditor } from "@/features/outreach/draft-editor";
import { QualificationPanel } from "@/features/outreach/qualification";
import { DeliveryHistory } from "@/features/outreach/delivery-history";

export default function DraftDetail() {
  const { id } = useParams<{ id: string }>();
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [notice, setNotice] = useState("");
  const draft = useQuery({
    queryKey: ["draft", organization.id, id],
    queryFn: () => api<Draft>(`/drafts/${id}`, {}, organization.id),
    refetchInterval: editing ? false : 4000,
  });
  const current = draft.data;
  const canEdit =
    organization.role !== "viewer" &&
    current?.status === "pending_review" &&
    !["succeeded", "failed", "cancelled"].includes(current.execution_status);
  return (
    <>
      <Link
        href="/leads"
        className="text-xs font-semibold text-teal-800 hover:underline"
      >
        ← Leads
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">
        Outreach draft
      </h1>
      <p className="mb-6 mt-2 text-slate-500">
        Review the message, provided facts, and provider output before an
        approval decision.
      </p>
      <QueryFeedback
        pending={draft.isPending}
        error={draft.error}
        retry={() => draft.refetch()}
      />
      {current && (
        <>
          {current.ai_metadata.draft.simulated && (
            <p className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              Mock AI output · This content came from the deterministic
              development provider. No live AI call was made.
            </p>
          )}
          {notice && (
            <p
              role="status"
              className="mb-5 rounded-lg bg-teal-50 p-3 text-teal-800"
            >
              {notice}
            </p>
          )}
          <section className="panel mb-6 p-6">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="break-all text-sm text-slate-600">
                  To: {current.recipient}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Revision {current.revision}
                  {current.last_edited_by ? " · Human edited" : ""} ·{" "}
                  {current.ai_metadata.draft.provider}
                </p>
              </div>
              <Status value={current.status} />
            </div>
            {editing ? (
              <DraftEditor
                draft={current}
                onCancel={() => setEditing(false)}
                onSaved={(saved) => {
                  client.setQueryData(["draft", organization.id, id], saved);
                  client.invalidateQueries({
                    queryKey: ["lead-drafts", organization.id],
                  });
                  client.invalidateQueries({
                    queryKey: ["approvals", organization.id],
                  });
                  setEditing(false);
                  setNotice(
                    "Draft revision saved. Review the current approval before continuing.",
                  );
                }}
              />
            ) : (
              <>
                <h2 className="break-words text-xl font-semibold">
                  {current.subject}
                </h2>
                <p className="my-5 whitespace-pre-wrap break-words leading-7 text-slate-700">
                  {current.body}
                </p>
                <div className="flex flex-wrap gap-3">
                  {canEdit && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setNotice("");
                        setEditing(true);
                      }}
                    >
                      Edit draft
                    </Button>
                  )}
                  {current.execution_status === "waiting_for_approval" && (
                    <Button asChild>
                      <Link href="/approvals">Review approval</Link>
                    </Button>
                  )}
                  <Button asChild variant="outline">
                    <Link href={`/executions/${current.execution_id}`}>
                      Inspect execution
                    </Link>
                  </Button>
                </div>
                <p className="mt-4 text-xs text-slate-500">
                  Execution: {current.execution_status.replaceAll("_", " ")} ·
                  The recipient is fixed for this draft.
                </p>
              </>
            )}
          </section>
          <QualificationPanel draft={current} />
          <DeliveryHistory
            draftId={current.id}
            active={["queued", "running", "retrying"].includes(
              current.execution_status,
            )}
          />
        </>
      )}
    </>
  );
}
