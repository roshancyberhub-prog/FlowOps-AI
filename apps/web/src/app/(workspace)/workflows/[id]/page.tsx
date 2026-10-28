"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { NodeSpec, Workflow, WorkflowVersion } from "@/lib/workflows";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { RunWorkflow } from "@/features/executions/run-workflow";
import { WorkflowCanvas } from "@/components/workflows/canvas";

export default function WorkflowPage() {
  const { id } = useParams<{ id: string }>();
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [notice, setNotice] = useState("");
  const workflow = useQuery({
    queryKey: ["workflow", organization.id, id],
    queryFn: () => api<Workflow>(`/workflows/${id}`, {}, organization.id),
    refetchOnWindowFocus: false,
  });
  const specs = useQuery({
    queryKey: ["node-types", organization.id],
    queryFn: () =>
      api<NodeSpec[]>("/workflows/node-types", {}, organization.id),
  });
  if (workflow.isPending || specs.isPending)
    return <p aria-busy>Loading workflow editor…</p>;
  if (workflow.error || specs.error)
    return (
      <>
        <p role="alert" className="notice">
          {(workflow.error || specs.error)?.message}
        </p>
        <Button
          className="mt-4"
          onClick={() => {
            workflow.refetch();
            specs.refetch();
          }}
        >
          Try again
        </Button>
      </>
    );
  if (!workflow.data || !specs.data) return null;
  return (
    <>
      <Link
        href="/workflows"
        className="mb-4 inline-block text-xs font-semibold text-teal-800 hover:underline"
      >
        ← All workflows
      </Link>
      <h1 className="text-3xl font-semibold tracking-tight">
        Workflow builder
      </h1>
      <p className="mb-6 mt-2 text-slate-500">
        Draft freely. Publish a version you can rely on.
      </p>
      {notice && (
        <p
          role="status"
          aria-label="Workflow update"
          className="mb-4 rounded-lg bg-teal-50 p-3 text-teal-800"
        >
          {notice}
        </p>
      )}
      <Editor
        key={workflow.data.revision}
        workflow={workflow.data}
        specs={specs.data}
        onSaved={(result, message) => {
          client.setQueryData(["workflow", organization.id, id], result);
          client.invalidateQueries({
            queryKey: ["workflows", organization.id],
          });
          client.invalidateQueries({
            queryKey: ["workflow-versions", organization.id, id],
          });
          setNotice(message);
        }}
      />
    </>
  );
}

function Editor({
  workflow,
  specs,
  onSaved,
}: {
  workflow: Workflow;
  specs: NodeSpec[];
  onSaved: (workflow: Workflow, message: string) => void;
}) {
  const { organization } = useWorkspace();
  const [selectedVersion, setSelectedVersion] = useState("draft");
  const [dirty, setDirty] = useState(false);
  const versions = useInfiniteQuery({
    queryKey: ["workflow-versions", organization.id, workflow.id],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      api<{
        items: WorkflowVersion[];
        total: number;
        page: number;
        page_size: number;
      }>(
        `/workflows/${workflow.id}/versions?page=${pageParam}`,
        {},
        organization.id,
      ),
    getNextPageParam: (last) =>
      last.page * last.page_size < last.total ? last.page + 1 : undefined,
  });
  const allVersions = versions.data?.pages.flatMap((page) => page.items) ?? [];
  const version = allVersions.find((item) => item.id === selectedVersion);
  return (
    <>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="w-60">
          <label htmlFor="workflow-version">Definition</label>
          <select
            id="workflow-version"
            value={selectedVersion}
            onChange={(event) => {
              if (dirty && !window.confirm("Discard unsaved draft changes?"))
                return;
              setDirty(false);
              setSelectedVersion(event.target.value);
            }}
          >
            <option value="draft">Current draft</option>
            {allVersions.map((item) => (
              <option key={item.id} value={item.id}>
                Published version {item.version_number}
              </option>
            ))}
          </select>
        </div>
        <span className="mt-5 text-xs text-slate-500">
          {version
            ? `Published version ${version.version_number} · Read only`
            : workflow.version_number
              ? `Latest published: v${workflow.version_number}`
              : "Not yet published"}
        </span>
        <RunWorkflow
          workflowId={workflow.id}
          versionId={version?.id ?? workflow.current_version_id}
          versionNumber={version?.version_number ?? workflow.version_number}
          disabled={
            dirty ||
            organization.role === "viewer" ||
            workflow.status === "archived"
          }
        />
        {versions.hasNextPage && (
          <Button
            variant="outline"
            disabled={versions.isFetchingNextPage}
            onClick={() => versions.fetchNextPage()}
          >
            Load older versions
          </Button>
        )}
      </div>
      {versions.error && (
        <p className="notice mb-4" role="alert">
          {versions.error.message}
        </p>
      )}
      <WorkflowCanvas
        key={selectedVersion}
        workflow={workflow}
        graph={version?.graph_definition ?? workflow.draft_graph}
        specs={specs}
        readOnly={
          !!version ||
          organization.role === "viewer" ||
          workflow.status === "archived"
        }
        onDirtyChange={setDirty}
        onSaved={onSaved}
      />
    </>
  );
}
