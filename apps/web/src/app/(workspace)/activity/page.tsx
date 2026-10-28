"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { api } from "@/lib/api";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";

type Entry = {
  id: string;
  action: string;
  resource_id: string;
  created_at: string;
  correlation_id: string;
};

export default function Audit() {
  const { organization } = useWorkspace();
  const [page, setPage] = useState(1);
  const entries = useQuery({
    queryKey: ["audit", organization.id, page],
    queryFn: () => api<Entry[]>(`/audit?page=${page}`, {}, organization.id),
    enabled: ["owner", "admin"].includes(organization.role),
  });
  if (!["owner", "admin"].includes(organization.role))
    return (
      <p className="notice" role="alert">
        Audit activity is available to workspace owners and administrators.
      </p>
    );
  return (
    <>
      <p className="eyebrow mb-2">A clear trail of every change</p>
      <h1 className="text-3xl font-semibold tracking-tight">Audit activity</h1>
      <p className="mb-8 mt-2 text-slate-500">
        Recorded workspace, lead, and permission changes.
      </p>
      <section className="panel overflow-hidden">
        {entries.isPending ? (
          <p className="p-8" aria-busy>
            Loading activity…
          </p>
        ) : entries.error ? (
          <div className="p-6">
            <p className="notice" role="alert">
              {entries.error.message}
            </p>
            <Button
              className="mt-3"
              variant="outline"
              onClick={() => entries.refetch()}
            >
              Try again
            </Button>
          </div>
        ) : !entries.data?.length ? (
          <div className="p-12 text-center">
            <Activity className="mx-auto mb-3 text-slate-400" />
            <h2 className="font-semibold">No activity on this page.</h2>
          </div>
        ) : (
          <div className="overflow-auto">
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Resource</th>
                  <th>Request ID</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {entries.data.map((entry) => (
                  <tr key={entry.id}>
                    <td className="font-medium">
                      {entry.action.replaceAll(".", " · ").replaceAll("_", " ")}
                    </td>
                    <td className="font-mono text-xs text-slate-500">
                      {entry.resource_id.slice(0, 12)}…
                    </td>
                    <td className="font-mono text-xs text-slate-500">
                      {entry.correlation_id}
                    </td>
                    <td className="whitespace-nowrap text-xs">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex justify-between border-t border-slate-200 p-4">
          <Button
            variant="outline"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <span className="self-center text-xs text-slate-500">
            Page {page}
          </span>
          <Button
            variant="outline"
            disabled={(entries.data?.length ?? 0) < 50}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      </section>
    </>
  );
}
