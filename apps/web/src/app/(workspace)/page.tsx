"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  GitBranch,
  ListChecks,
  ShieldCheck,
  Users,
} from "lucide-react";
import { api, type LeadPage } from "@/lib/api";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Status } from "@/features/executions/shared";
import type { Daily } from "@/features/analytics/execution-chart";

const ExecutionChart = dynamic(
  () => import("@/features/analytics/execution-chart"),
  {
    ssr: false,
    loading: () => (
      <p className="h-64 p-6" aria-busy="true">
        Loading chart…
      </p>
    ),
  },
);
type Overview = {
  active_leads: number;
  active_workflows: number;
  pending_approvals: number;
  executions: number;
  succeeded: number;
  failed: number;
  success_rate: number | null;
  average_active_ms: number | null;
  generated_at: string;
  daily: Daily[];
  recent_executions: {
    id: string;
    workflow_name: string;
    status: string;
    mode: string;
    created_at: string;
  }[];
};

export default function Overview() {
  const { organization, user } = useWorkspace();
  const summary = useQuery({
    queryKey: ["overview", organization.id],
    queryFn: () => api<Overview>("/analytics/overview", {}, organization.id),
    refetchInterval: 15000,
  });
  const leads = useQuery({
    queryKey: ["leads", organization.id, "overview"],
    queryFn: () => api<LeadPage>("/leads?page_size=5", {}, organization.id),
  });
  const data = summary.data;
  const cards = [
    {
      label: "Active leads",
      value: data?.active_leads,
      icon: Users,
      href: "/leads",
    },
    {
      label: "Active workflows",
      value: data?.active_workflows,
      icon: GitBranch,
      href: "/workflows",
    },
    {
      label: "Runs · 7 UTC days",
      value: data?.executions,
      icon: ListChecks,
      href: "/executions",
    },
    {
      label: "Pending approvals",
      value: data?.pending_approvals,
      icon: ShieldCheck,
      href: "/approvals",
    },
  ];
  return (
    <>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow mb-2">Your operations at a glance</p>
          <h1 className="text-3xl font-semibold tracking-tight">
            Welcome back, {user.display_name.split(" ")[0]}.
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            {organization.name} · Counts and outcomes from your workspace.
          </p>
        </div>
        <Button asChild>
          <Link href="/leads">
            Manage leads
            <ArrowRight size={16} />
          </Link>
        </Button>
      </div>
      {summary.error && (
        <div className="notice mb-5" role="alert">
          {summary.error.message}
          <Button
            className="ml-3"
            variant="outline"
            onClick={() => summary.refetch()}
          >
            Try again
          </Button>
        </div>
      )}
      <section
        className="mb-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Workspace summary"
        aria-busy={summary.isPending}
      >
        {cards.map(({ label, value, icon: Icon, href }) => (
          <Link
            key={label}
            href={href}
            className="panel p-6 transition-colors hover:border-teal-300"
          >
            <div className="mb-5 flex items-center justify-between gap-3">
              <span className="text-sm text-slate-500">{label}</span>
              <Icon size={19} className="text-teal-700" />
            </div>
            <p
              className="text-4xl font-semibold tracking-tight"
              data-testid={`metric-${href.slice(1)}`}
            >
              {value === undefined ? "—" : value.toLocaleString()}
            </p>
          </Link>
        ))}
      </section>
      <div className="mb-7 grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section className="panel min-w-0 p-6">
          <h2 className="font-semibold">Execution outcomes</h2>
          <p className="mt-1 text-xs text-slate-500">
            Last 7 UTC days, including today · grouped by request date and
            current status · test and live runs
          </p>
          {summary.isPending ? (
            <p className="h-64 p-8" aria-busy="true">
              Loading outcomes…
            </p>
          ) : !data ? (
            <p className="p-8 text-sm text-slate-500">
              Outcomes unavailable. Retry the request above.
            </p>
          ) : data.executions === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center text-center">
              <GitBranch className="mb-3 text-slate-300" size={30} />
              <h3 className="font-medium">No executions in this period</h3>
              <p className="mt-2 max-w-xs text-sm text-slate-500">
                Publish a workflow and start a run to see its recorded outcomes
                here.
              </p>
              <Link
                className="mt-4 text-sm font-semibold text-teal-800 hover:underline"
                href="/workflows"
              >
                Open workflows →
              </Link>
            </div>
          ) : (
            <ExecutionChart daily={data.daily} />
          )}
        </section>
        <section className="panel p-6">
          <h2 className="font-semibold">Completion health</h2>
          <p className="mt-1 text-xs text-slate-500">
            Runs requested within the same 7-day period
          </p>
          <dl className="mt-6 space-y-5">
            <div>
              <dt className="text-xs text-slate-500">
                Success rate among succeeded + failed runs
              </dt>
              <dd className="mt-2 text-4xl font-semibold text-teal-800">
                {data?.success_rate == null ? "—" : `${data.success_rate}%`}
              </dd>
            </div>
            <div className="grid grid-cols-2 gap-4 border-y border-slate-100 py-4">
              <div>
                <dt className="text-xs text-slate-500">Succeeded</dt>
                <dd className="mt-1 text-xl font-semibold">
                  {data?.succeeded ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Failed</dt>
                <dd className="mt-1 text-xl font-semibold">
                  {data?.failed ?? "—"}
                </dd>
              </div>
            </div>
            <div>
              <dt className="text-xs text-slate-500">
                Average active processing · completed runs
              </dt>
              <dd className="mt-2 text-xl font-semibold">
                {data?.average_active_ms == null
                  ? "—"
                  : `${(data.average_active_ms / 1000).toFixed(2)} seconds`}
              </dd>
              <p className="mt-2 text-xs text-slate-500">
                Excludes waiting for approval, queued time and scheduled delays.
                A dash means no completed runs.
              </p>
            </div>
          </dl>
        </section>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="panel min-w-0 overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 p-5">
            <h2 className="font-semibold">Recent executions</h2>
            <Link
              href="/executions"
              className="text-xs font-semibold text-teal-800 hover:underline"
            >
              View all →
            </Link>
          </div>
          {summary.isPending ? (
            <p className="p-6" aria-busy="true">
              Loading executions…
            </p>
          ) : !data?.recent_executions.length ? (
            <p className="p-8 text-sm text-slate-500">
              No executions in this period.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.recent_executions.map((run) => (
                <li key={run.id}>
                  <Link
                    href={`/executions/${run.id}`}
                    className="flex flex-wrap items-center justify-between gap-3 p-5 hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <p className="break-words text-sm font-medium">
                        {run.workflow_name}
                      </p>
                      <p className="mt-1 text-xs capitalize text-slate-500">
                        {run.mode} · {new Date(run.created_at).toLocaleString()}
                      </p>
                    </div>
                    <Status value={run.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="panel min-w-0 overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 p-5">
            <h2 className="font-semibold">Recently added leads</h2>
            <Link
              href="/leads"
              className="text-xs font-semibold text-teal-800 hover:underline"
            >
              View all →
            </Link>
          </div>
          {leads.isPending ? (
            <p className="p-6" aria-busy="true">
              Loading leads…
            </p>
          ) : leads.error ? (
            <div role="alert" className="notice m-4">
              {leads.error.message}
              <Button variant="outline" onClick={() => leads.refetch()}>
                Try again
              </Button>
            </div>
          ) : !leads.data?.items.length ? (
            <p className="p-8 text-sm text-slate-500">
              Your pipeline starts with a person. Add a lead to get started.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {leads.data.items.map((lead) => (
                <li
                  key={lead.id}
                  className="flex flex-wrap items-center justify-between gap-3 p-5"
                >
                  <div className="min-w-0">
                    <p className="break-words text-sm font-medium">
                      {lead.name}
                    </p>
                    <p className="mt-1 break-all text-xs text-slate-500">
                      {lead.company ?? lead.email}
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs capitalize text-slate-600">
                    {lead.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      <p className="mt-6 text-xs text-slate-500">
        AI drafts and email receipts use explicitly labelled mock providers in
        the development setup. No external email is sent.
        {data &&
          ` · Metrics updated ${new Date(data.generated_at).toLocaleTimeString()}.`}
      </p>
    </>
  );
}
