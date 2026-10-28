"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Workflow, WorkflowGraph } from "@/lib/workflows";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";

export function CreateWorkflow({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { organization } = useWorkspace();
  const router = useRouter();
  const client = useQueryClient();
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("basic");
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const templates = useQuery({
    queryKey: ["workflow-templates", organization.id],
    queryFn: () =>
      api<{ id: string; name: string; graph: WorkflowGraph }[]>(
        "/workflows/templates",
        {},
        organization.id,
      ),
  });
  const create = useMutation({
    mutationFn: () =>
      api<Workflow>(
        "/workflows",
        {
          method: "POST",
          body: JSON.stringify({
            name,
            graph: templates.data?.find((item) => item.id === template)?.graph,
          }),
        },
        organization.id,
      ),
    onSuccess: (workflow) => {
      client.invalidateQueries({ queryKey: ["workflows", organization.id] });
      router.push(`/workflows/${workflow.id}`);
      onClose();
    },
  });
  return (
    <dialog
      ref={dialog}
      onCancel={onClose}
      aria-labelledby="create-workflow-title"
      className="m-auto w-[min(460px,calc(100%-32px))] rounded-xl border-0 bg-white p-6 text-slate-800 shadow-2xl backdrop:bg-slate-950/40"
    >
      <h2 id="create-workflow-title" className="text-xl font-semibold">
        Create a workflow
      </h2>
      <p className="mb-6 mt-2 text-sm text-slate-500">
        Start from a template, then make it your own.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate();
        }}
        className="space-y-5"
      >
        <div>
          <label htmlFor="new-workflow-name">Workflow name</label>
          <input
            id="new-workflow-name"
            required
            maxLength={150}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="workflow-template">Starting template</label>
          <select
            id="workflow-template"
            value={template}
            disabled={templates.isPending || !!templates.error}
            onChange={(event) => setTemplate(event.target.value)}
          >
            {templates.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
        {(create.error || templates.error) && (
          <p className="notice" role="alert">
            {(create.error || templates.error)?.message}
          </p>
        )}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={create.isPending || !templates.data}>
            Create workflow
          </Button>
        </div>
      </form>
    </dialog>
  );
}
