"use client";
import { Check, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { useWorkflowCanvas } from "./use-workflow-canvas";
export function WorkflowToolbar({
  state,
  readOnly,
}: {
  state: ReturnType<typeof useWorkflowCanvas>;
  readOnly: boolean;
}) {
  const {
    name,
    setName,
    markDirty,
    dirty,
    validate,
    save,
    publish,
    error,
    nodes,
  } = state;
  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
        <div className="w-full max-w-sm">
          <label htmlFor="workflow-name">Workflow name</label>
          <input
            id="workflow-name"
            value={name}
            readOnly={readOnly}
            maxLength={150}
            onChange={(event) => {
              setName(event.target.value);
              markDirty();
            }}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="mr-2 text-xs text-slate-500">
            {readOnly ? "Read only" : dirty ? "Unsaved changes" : "Saved draft"}
          </span>
          <Button
            variant="outline"
            onClick={() => validate.mutate()}
            disabled={validate.isPending}
          >
            Validate
          </Button>
          {!readOnly && (
            <>
              <Button
                variant="outline"
                disabled={save.isPending || !dirty || !name.trim()}
                onClick={() => save.mutate()}
              >
                <Save size={15} />
                Save draft
              </Button>
              <Button
                disabled={publish.isPending || dirty}
                title={
                  dirty
                    ? "Save your draft before publishing"
                    : "Publish an immutable version"
                }
                onClick={() => publish.mutate()}
              >
                Publish version
              </Button>
            </>
          )}
        </div>
      </div>
      {error && (
        <p role="alert" className="notice mb-4">
          {error.message}
        </p>
      )}
      {validate.data && (
        <div
          role="status"
          aria-label="Workflow validation"
          className={`mb-4 rounded-lg border p-4 ${validate.data.valid ? "border-teal-200 bg-teal-50 text-teal-800" : "border-red-200 bg-red-50 text-red-800"}`}
        >
          {validate.data.valid ? (
            <p className="flex items-center gap-2">
              <Check size={17} />
              Workflow is valid. {validate.data.order.length} nodes in the plan.
            </p>
          ) : (
            <>
              <p className="mb-2 font-semibold">Fix these workflow issues:</p>
              <ul className="list-inside list-disc space-y-1">
                {validate.data.errors.map((issue, index) => (
                  <li key={index}>
                    {issue.node_id
                      ? `${nodes.find((node) => node.id === issue.node_id)?.data.label ?? issue.node_id}: `
                      : ""}
                    {issue.message}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </>
  );
}
