"use client";
import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Play, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Execution } from "@/lib/executions";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/workspace";

export function RunWorkflow({
  workflowId,
  versionId,
  versionNumber,
  disabled,
}: {
  workflowId: string;
  versionId: string | null;
  versionNumber: number;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant="outline"
        disabled={disabled || !versionId}
        onClick={() => setOpen(true)}
        title={
          !versionId
            ? "Publish a version before running"
            : disabled
              ? "Save changes before running"
              : "Run this published version"
        }
      >
        <Play size={15} />
        Run workflow
      </Button>
      {open && versionId && (
        <RunDialog
          workflowId={workflowId}
          versionId={versionId}
          versionNumber={versionNumber}
          close={() => setOpen(false)}
        />
      )}
    </>
  );
}
function RunDialog({
  workflowId,
  versionId,
  versionNumber,
  close,
}: {
  workflowId: string;
  versionId: string;
  versionNumber: number;
  close: () => void;
}) {
  const { organization } = useWorkspace();
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [leadId, setLeadId] = useState("");
  const [mode, setMode] = useState("test");
  const [key, setKey] = useState(() => crypto.randomUUID());
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const run = useMutation({
    mutationFn: () =>
      api<Execution>(
        `/workflows/${workflowId}/${mode === "test" ? "test-runs" : "runs"}`,
        {
          method: "POST",
          headers: { "Idempotency-Key": key },
          body: JSON.stringify({
            workflow_version_id: versionId,
            ...(leadId.trim() ? { lead_id: leadId.trim() } : {}),
          }),
        },
        organization.id,
      ),
    onSuccess: (result) => router.push(`/executions/${result.id}`),
  });
  return (
    <dialog
      ref={dialog}
      onCancel={(event) => {
        if (run.isPending) event.preventDefault();
        else close();
      }}
      aria-labelledby="run-title"
      className="m-auto w-[min(94vw,480px)] rounded-xl p-6 backdrop:bg-slate-950/40"
    >
      <div className="flex items-center justify-between">
        <h2 id="run-title" className="text-xl font-semibold">
          Run published version {versionNumber}
        </h2>
        <Button
          variant="ghost"
          aria-label="Close run dialog"
          disabled={run.isPending}
          onClick={close}
        >
          <X size={18} />
        </Button>
      </div>
      <p className="my-4 text-sm text-slate-500">
        A background worker processes this saved version. Inspect each step
        after starting.
      </p>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          run.mutate();
        }}
      >
        <div>
          <label htmlFor="run-mode">Run mode</label>
          <select
            id="run-mode"
            value={mode}
            disabled={run.isPending}
            onChange={(e) => {
              setMode(e.target.value);
              setKey(crypto.randomUUID());
            }}
          >
            <option value="test">Test · simulate business changes</option>
            <option value="live">Live · apply business changes</option>
          </select>
        </div>
        <p className="rounded-lg bg-teal-50 p-3 text-sm text-teal-800">
          {mode === "test"
            ? "Test mode records steps and approvals. Lead changes and notifications are simulated."
            : "Live mode can update stored leads and create notifications. Protected sends require approval."}
        </p>
        <div>
          <label htmlFor="run-lead">Stored lead ID (optional)</label>
          <input
            id="run-lead"
            value={leadId}
            disabled={run.isPending}
            placeholder="UUID from your lead record"
            pattern="[0-9a-fA-F-]{36}"
            onChange={(e) => {
              setLeadId(e.target.value);
              setKey(crypto.randomUUID());
            }}
          />
          <p className="mt-2 text-xs text-slate-500">
            Lead actions require a lead. A basic Record result workflow can run
            without one.
          </p>
        </div>
        {run.error && (
          <p role="alert" className="notice">
            {run.error.message}
          </p>
        )}
        <Button disabled={run.isPending}>
          {run.isPending ? "Starting…" : "Start background run"}
        </Button>
      </form>
    </dialog>
  );
}
