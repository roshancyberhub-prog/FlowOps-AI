"use client";

import { useDeferredValue, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ArrowLeft,
  ArrowRight,
  Pencil,
  Plus,
  Search,
  Users,
} from "lucide-react";
import { api, type Lead, type LeadPage } from "@/lib/api";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { LeadForm } from "@/components/lead-form";

export default function Leads() {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [editor, setEditor] = useState<{
    lead?: Lead;
    readOnly?: boolean;
  } | null>(null);
  const [notice, setNotice] = useState("");
  const canWrite = organization.role !== "viewer";
  const query = new URLSearchParams({
    search: deferredSearch,
    page: String(page),
    page_size: "20",
  });
  if (status) query.set("status", status);
  const leads = useQuery({
    queryKey: ["leads", organization.id, deferredSearch, status, page],
    queryFn: () => api<LeadPage>(`/leads?${query}`, {}, organization.id),
  });
  const archive = useMutation({
    mutationFn: (lead: Lead) =>
      api(`/leads/${lead.id}`, { method: "DELETE" }, organization.id),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["leads", organization.id] });
      setNotice("Lead archived.");
    },
  });
  return (
    <>
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="eyebrow mb-2">Build better relationships</p>
          <h1 className="text-3xl font-semibold tracking-tight">Leads</h1>
          <p className="mt-2 text-slate-500">
            The right people. The details that matter.
          </p>
        </div>
        {canWrite && (
          <Button
            onClick={() => {
              setNotice("");
              setEditor({});
            }}
          >
            <Plus size={17} />
            Add lead
          </Button>
        )}
      </div>
      {notice && (
        <p
          role="status"
          className="mb-5 rounded-lg border border-teal-200 bg-teal-50 p-3 text-sm text-teal-800"
        >
          {notice}
        </p>
      )}
      {archive.error && (
        <p role="alert" className="notice mb-5">
          {archive.error.message}
        </p>
      )}
      <section className="panel overflow-hidden">
        <div className="flex flex-wrap items-center gap-4 border-b border-slate-200 p-5">
          <div className="relative min-w-52 flex-1">
            <Search
              aria-hidden
              size={16}
              className="absolute left-3 top-3.5 text-slate-400"
            />
            <label className="sr-only" htmlFor="lead-search">
              Search leads
            </label>
            <input
              id="lead-search"
              className="pl-10!"
              type="search"
              placeholder="Search name, email or company…"
              maxLength={200}
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="w-44">
            <label className="sr-only" htmlFor="status-filter">
              Filter by status
            </label>
            <select
              id="status-filter"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Active leads</option>
              {["new", "qualified", "contacted", "won", "lost", "archived"].map(
                (item) => (
                  <option key={item} value={item}>
                    {item[0].toUpperCase() + item.slice(1)}
                  </option>
                ),
              )}
            </select>
          </div>
          <span className="text-xs text-slate-500">
            {leads.data?.total ?? "—"} records
          </span>
        </div>
        {leads.isPending ? (
          <p className="p-12 text-center text-slate-500" aria-busy>
            Loading leads…
          </p>
        ) : leads.error ? (
          <div className="p-6">
            <p role="alert" className="notice">
              {leads.error.message}
            </p>
            <Button
              className="mt-4"
              variant="outline"
              onClick={() => leads.refetch()}
            >
              Try again
            </Button>
          </div>
        ) : !leads.data?.items.length ? (
          <div className="px-6 py-20 text-center">
            <span className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-teal-50 text-teal-700">
              <Users size={25} />
            </span>
            <h2 className="text-lg font-semibold">
              {search || status
                ? "No matching leads"
                : "Meet your next opportunity."}
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              {search || status
                ? "Try a different search or status filter."
                : "Add your first lead and keep the conversation moving."}
            </p>
            {canWrite && !search && !status && (
              <Button
                variant="outline"
                className="mt-5"
                onClick={() => setEditor({})}
              >
                <Plus size={16} />
                Add your first lead
              </Button>
            )}
          </div>
        ) : (
          <div className="relative min-w-0 max-w-full overflow-x-auto">
            <table className="min-w-[640px]">
              <thead>
                <tr>
                  <th>Lead</th>
                  <th>Company / role</th>
                  <th>Status</th>
                  <th>Added</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {leads.data.items.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <button
                        className="text-left font-semibold text-slate-800 hover:text-teal-800 hover:underline"
                        onClick={() => setEditor({ lead, readOnly: true })}
                      >
                        {lead.name}
                      </button>
                      <p className="mt-1 text-xs text-slate-500">
                        {lead.email}
                      </p>
                    </td>
                    <td>
                      <p>{lead.company || "—"}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {lead.job_title || "No title added"}
                      </p>
                    </td>
                    <td>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${lead.status === "qualified" || lead.status === "won" ? "bg-teal-50 text-teal-800" : "bg-slate-100 text-slate-600"}`}
                      >
                        {lead.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap text-xs text-slate-500">
                      {new Date(lead.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      {canWrite && (
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            aria-label={`Edit ${lead.name}`}
                            onClick={() => setEditor({ lead })}
                          >
                            <Pencil size={15} />
                          </Button>
                          {lead.status !== "archived" && (
                            <Button
                              variant="ghost"
                              aria-label={`Archive ${lead.name}`}
                              disabled={archive.isPending}
                              onClick={() => {
                                if (
                                  window.confirm(
                                    `Archive ${lead.name}? You can restore this lead by changing its status from the archived list.`,
                                  )
                                )
                                  archive.mutate(lead);
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
        <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4">
          <p className="text-xs text-slate-500">
            Page {page} of{" "}
            {Math.max(1, Math.ceil((leads.data?.total ?? 0) / 20))}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={page === 1 || leads.isFetching}
              onClick={() => setPage(page - 1)}
            >
              <ArrowLeft size={14} />
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={
                !leads.data || page * 20 >= leads.data.total || leads.isFetching
              }
              onClick={() => setPage(page + 1)}
            >
              Next
              <ArrowRight size={14} />
            </Button>
          </div>
        </div>
      </section>
      {!canWrite && (
        <p className="mt-4 text-xs text-slate-500">
          Viewer access: you can inspect leads. Ask a workspace administrator
          for editing access.
        </p>
      )}
      {editor && (
        <LeadForm
          key={`${organization.id}-${editor.lead?.id ?? "new"}`}
          {...editor}
          onClose={() => setEditor(null)}
          onSaved={() => {
            setEditor(null);
            setNotice(editor.lead ? "Lead updated." : "Lead added.");
          }}
        />
      )}
    </>
  );
}
