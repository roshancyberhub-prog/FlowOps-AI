"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Building2, ShieldCheck, Users } from "lucide-react";
import { api, type LeadPage } from "@/lib/api";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";

export default function Overview() {
  const { organization, user } = useWorkspace();
  const leads = useQuery({
    queryKey: ["leads", organization.id, "overview"],
    queryFn: () => api<LeadPage>("/leads?page_size=5", {}, organization.id),
  });
  return (
    <>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow mb-2">Your operations at a glance</p>
          <h1 className="text-3xl font-semibold tracking-tight">
            Welcome back, {user.display_name.split(" ")[0]}.
          </h1>
          <p className="mt-2 text-slate-500">
            A clear view of your workspace. A focused next step.
          </p>
        </div>
        <Button asChild>
          <Link href="/leads">
            Manage leads
            <ArrowRight size={16} />
          </Link>
        </Button>
      </div>
      <section
        className="mb-8 grid gap-4 md:grid-cols-3"
        aria-label="Workspace summary"
      >
        <div className="panel p-6">
          <div className="mb-5 flex items-center justify-between">
            <span className="text-sm text-slate-500">Active leads</span>
            <Users size={19} className="text-teal-700" />
          </div>
          <p className="text-4xl font-semibold tracking-tight">
            {leads.data?.total ?? "—"}
          </p>
          <p className="mt-3 text-xs text-slate-500">
            Excludes archived records
          </p>
        </div>
        <div className="panel p-6">
          <div className="mb-5 flex items-center justify-between">
            <span className="text-sm text-slate-500">Workspace</span>
            <Building2 size={19} className="text-slate-400" />
          </div>
          <p className="truncate text-2xl font-semibold">{organization.name}</p>
          <p className="mt-4 text-xs text-slate-500">
            Your organization’s data, together
          </p>
        </div>
        <div className="panel p-6">
          <div className="mb-5 flex items-center justify-between">
            <span className="text-sm text-slate-500">Your access</span>
            <ShieldCheck size={19} className="text-slate-400" />
          </div>
          <p className="text-2xl font-semibold capitalize">
            {organization.role}
          </p>
          <p className="mt-4 text-xs text-slate-500">
            Permissions enforced by the API
          </p>
        </div>
      </section>
      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5">
          <div>
            <h2 className="text-base font-semibold">Recently added leads</h2>
            <p className="mt-1 text-xs text-slate-500">
              The latest additions to your pipeline
            </p>
          </div>
          <Link
            href="/leads"
            className="text-xs font-semibold text-teal-800 hover:underline"
          >
            View all →
          </Link>
        </div>
        {leads.isPending ? (
          <p className="p-8 text-slate-500" aria-busy>
            Loading leads…
          </p>
        ) : leads.error ? (
          <div className="p-6">
            <p role="alert" className="notice">
              {leads.error.message}
            </p>
            <Button
              variant="outline"
              className="mt-3"
              onClick={() => leads.refetch()}
            >
              Try again
            </Button>
          </div>
        ) : !leads.data?.items.length ? (
          <div className="px-6 py-16 text-center">
            <Users className="mx-auto mb-4 text-slate-300" size={32} />
            <h3 className="text-base font-semibold">
              Your pipeline starts with a person.
            </h3>
            <p className="mt-2 text-sm text-slate-500">
              Add your first lead to put this workspace to work.
            </p>
            <Button asChild variant="outline" className="mt-5">
              <Link href="/leads">
                Go to leads
                <ArrowRight size={15} />
              </Link>
            </Button>
          </div>
        ) : (
          <div className="overflow-auto">
            <table>
              <thead>
                <tr>
                  <th>Lead</th>
                  <th>Company</th>
                  <th>Status</th>
                  <th>Added</th>
                </tr>
              </thead>
              <tbody>
                {leads.data.items.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <p className="font-medium">{lead.name}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {lead.email}
                      </p>
                    </td>
                    <td>{lead.company ?? "—"}</td>
                    <td>
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs capitalize text-slate-600">
                        {lead.status}
                      </span>
                    </td>
                    <td className="text-xs text-slate-500">
                      {new Date(lead.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <p className="mt-6 text-xs text-slate-500">
        Lead management and workflow design are available. Workflow execution
        and AI processing are not available in this release.
      </p>
    </>
  );
}
