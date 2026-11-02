"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, GitBranch, Pause, Play, Plus, Archive } from "lucide-react";
import { api } from "@/lib/api";
import type { Workflow } from "@/lib/workflows";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { CreateWorkflow } from "@/components/workflows/create-workflow";

export default function Workflows() {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [create, setCreate] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [notice, setNotice] = useState("");
  const canWrite = organization.role !== "viewer";
  const list = useQuery({
    queryKey: ["workflows", organization.id, page, status],
    queryFn: () =>
      api<{ items: Workflow[]; total: number }>(
        `/workflows?page=${page}${status ? `&status=${status}` : ""}`,
        {},
        organization.id,
      ),
  });
  const action = useMutation({
    mutationFn: ({
      workflow,
      action,
    }: {
      workflow: Workflow;
      action: string;
    }) =>
      api<Workflow>(
        `/workflows/${workflow.id}/${action}`,
        {
          method: "POST",
          ...(action !== "duplicate"
            ? { body: JSON.stringify({ expected_revision: workflow.revision }) }
            : {}),
        },
        organization.id,
      ),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["workflows", organization.id] });
      setNotice("Workflow updated.");
    },
  });
  return (
    <>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow mb-2">Turn a process into a clear path</p>
          <h1 className="text-3xl font-semibold tracking-tight">Workflows</h1>
          <p className="mt-2 text-slate-500">
            Design your process. Validate every connection.
          </p>
        </div>
        {canWrite && (
          <Button onClick={() => setCreate(true)}>
            <Plus size={17} />
            New workflow
          </Button>
        )}
      </div>
      {notice && (
        <p
          role="status"
          className="mb-4 rounded-lg bg-teal-50 p-3 text-teal-800"
        >
          {notice}
        </p>
      )}
      {action.error && (
        <p className="notice mb-4" role="alert">
          {action.error.message}
        </p>
      )}
      <section className="panel overflow-hidden">
        <div className="border-b border-slate-200 p-5">
          <label htmlFor="workflow-filter" className="sr-only">
            Filter workflows by status
          </label>
          <select
            id="workflow-filter"
            className="max-w-52"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Current workflows</option>
            {["draft", "active", "paused", "archived"].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </div>
        {list.isPending ? (
          <p className="p-10" aria-busy>
            Loading workflows…
          </p>
        ) : list.error ? (
          <div className="p-6">
            <p role="alert" className="notice">
              {list.error.message}
            </p>
            <Button
              className="mt-3"
              variant="outline"
              onClick={() => list.refetch()}
            >
              Try again
            </Button>
          </div>
        ) : !list.data?.items.length ? (
          <div className="p-16 text-center">
            <GitBranch className="mx-auto mb-4 text-teal-700" size={30} />
            <h2 className="text-lg font-semibold">
              Make your next process repeatable.
            </h2>
            <p className="mt-2 text-slate-500">
              Create a workflow from a template to get started.
            </p>
          </div>
        ) : (
          <div className="relative overflow-x-auto">
            <table className="min-w-[600px]">
              <thead>
                <tr>
                  <th>Workflow</th>
                  <th>Status</th>
                  <th>Version</th>
                  <th>Runs</th>
                  <th>Last run</th>
                  <th>Updated</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.data.items.map((workflow) => (
                  <tr key={workflow.id}>
                    <td>
                      <Link
                        href={`/workflows/${workflow.id}`}
                        className="font-semibold text-slate-800 hover:text-teal-700 hover:underline"
                      >
                        {workflow.name}
                      </Link>
                    </td>
                    <td>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs capitalize ${workflow.status === "active" ? "bg-teal-50 text-teal-800" : "bg-slate-100 text-slate-600"}`}
                      >
                        {workflow.status}
                      </span>
                    </td>
                    <td>{workflow.execution_count ?? 0}</td>
                    <td className="text-xs text-slate-500">
                      {workflow.last_execution_at
                        ? new Date(workflow.last_execution_at).toLocaleString()
                        : "No runs yet"}
                    </td>
                    <td className="text-xs text-slate-500">
                      {workflow.version_number
                        ? `Published v${workflow.version_number}`
                        : "Unpublished"}
                    </td>
                    <td className="text-xs text-slate-500">
                      {new Date(workflow.updated_at).toLocaleDateString()}
                    </td>
                    <td>
                      {canWrite && (
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            aria-label={`Duplicate ${workflow.name}`}
                            disabled={action.isPending}
                            onClick={() =>
                              action.mutate({ workflow, action: "duplicate" })
                            }
                          >
                            <Copy size={15} />
                          </Button>
                          {["active", "paused"].includes(workflow.status) && (
                            <Button
                              variant="ghost"
                              aria-label={`${workflow.status === "active" ? "Pause" : "Resume"} ${workflow.name}`}
                              disabled={action.isPending}
                              onClick={() =>
                                action.mutate({
                                  workflow,
                                  action:
                                    workflow.status === "active"
                                      ? "pause"
                                      : "resume",
                                })
                              }
                            >
                              {workflow.status === "active" ? (
                                <Pause size={15} />
                              ) : (
                                <Play size={15} />
                              )}
                            </Button>
                          )}
                          {workflow.status !== "archived" && (
                            <Button
                              variant="ghost"
                              aria-label={`Archive ${workflow.name}`}
                              disabled={action.isPending}
                              onClick={() => {
                                if (window.confirm(`Archive ${workflow.name}?`))
                                  action.mutate({
                                    workflow,
                                    action: "archive",
                                  });
                              }}
                            >
                              <Archive size={15} />
                            </Button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex items-center justify-between border-t border-slate-200 p-4">
          <Button
            variant="outline"
            disabled={page === 1 || list.isFetching}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <span className="text-xs text-slate-500">Page {page}</span>
          <Button
            variant="outline"
            disabled={
              !list.data || page * 20 >= list.data.total || list.isFetching
            }
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      </section>
      {create && <CreateWorkflow onClose={() => setCreate(false)} />}
    </>
  );
}
