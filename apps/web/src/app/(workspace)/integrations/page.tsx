"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cable, GitBranch, Webhook } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/workspace";

type Integration = {
  id: string;
  name: string;
  provider: "github" | "webhook";
  configuration: {
    owner?: string;
    repo?: string;
    workflow_id?: string;
    destination?: string;
    receiver_deduplicates?: boolean;
  };
  enabled: boolean;
  revision: number;
  last_test_status: string;
  last_test_at: string | null;
  last_error: string | null;
  last_result: {
    full_name?: string;
    description?: string;
    stargazers_count?: number;
    url?: string;
  };
};
type Event = {
  id: string;
  external_id: string;
  lead_id: string;
  execution_id: string | null;
  created_at: string;
};
type Delivery = {
  id: string;
  status: string;
  error_code: string | null;
  created_at: string;
  attempts: {
    number: number;
    status: string;
    http_status: number | null;
    error_code: string | null;
    uncertain: boolean;
  }[];
};

export default function Integrations() {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const canManage = ["owner", "admin"].includes(organization.role);
  const [page, setPage] = useState(1);
  const [provider, setProvider] = useState<"github" | "webhook">("github");
  const [name, setName] = useState("");
  const [owner, setOwner] = useState("octocat");
  const [repo, setRepo] = useState("Hello-World");
  const [workflow, setWorkflow] = useState("");
  const [destination, setDestination] = useState("");
  const [deduplicates, setDeduplicates] = useState(false);
  const rows = useQuery({
    queryKey: ["integrations", organization.id, page],
    queryFn: () =>
      api<{ items: Integration[]; total: number }>(
        `/integrations?page=${page}`,
        {},
        organization.id,
      ),
  });
  const workflows = useQuery({
    queryKey: ["webhook-workflows", organization.id],
    queryFn: () =>
      api<{ items: { id: string; name: string; status: string }[] }>(
        "/workflows?page_size=50",
        {},
        organization.id,
      ),
    enabled: canManage && provider === "webhook",
  });
  const create = useMutation({
    mutationFn: () =>
      api<Integration>(
        "/integrations",
        {
          method: "POST",
          body: JSON.stringify({
            name,
            provider,
            configuration:
              provider === "github"
                ? { owner, repo }
                : {
                    workflow_id: workflow || null,
                    destination: destination || null,
                    receiver_deduplicates: deduplicates,
                  },
          }),
        },
        organization.id,
      ),
    onSuccess: () => {
      setName("");
      setPage(1);
      client.invalidateQueries({ queryKey: ["integrations", organization.id] });
    },
  });
  return (
    <>
      <div className="mb-8">
        <p className="eyebrow mb-2">Connected operations</p>
        <h1 className="text-3xl font-semibold tracking-tight">Integrations</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          Read public GitHub repository data or receive signed lead events.
          Outgoing webhooks send operational IDs and status, with inspectable
          delivery attempts.
        </p>
      </div>
      {canManage && (
        <form
          className="panel mb-8 space-y-4 p-6"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <h2 className="text-lg font-semibold">Add integration</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="integration-name">Name</label>
              <input
                id="integration-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={100}
              />
            </div>
            <div>
              <label htmlFor="provider">Provider</label>
              <select
                id="provider"
                value={provider}
                onChange={(e) =>
                  setProvider(e.target.value as "github" | "webhook")
                }
              >
                <option value="github">GitHub · public repository</option>
                <option value="webhook">Signed webhook</option>
              </select>
            </div>
          </div>
          {provider === "github" ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label htmlFor="repo-owner">Repository owner</label>
                  <input
                    id="repo-owner"
                    required
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                    maxLength={100}
                    pattern="[a-zA-Z0-9][a-zA-Z0-9_.-]*"
                  />
                </div>
                <div>
                  <label htmlFor="repo-name">Repository name</label>
                  <input
                    id="repo-name"
                    required
                    value={repo}
                    onChange={(e) => setRepo(e.target.value)}
                    maxLength={100}
                    pattern="[a-zA-Z0-9][a-zA-Z0-9_.-]*"
                  />
                </div>
              </div>
              <p className="text-xs text-slate-500">
                Uses GitHub’s public API. No account credentials are required.
                Private repositories are unavailable.
              </p>
            </>
          ) : (
            <>
              <div>
                <label htmlFor="webhook-workflow">
                  Workflow to trigger (optional)
                </label>
                <select
                  id="webhook-workflow"
                  value={workflow}
                  onChange={(e) => setWorkflow(e.target.value)}
                >
                  <option value="">Save lead only</option>
                  {workflows.data?.items
                    .filter((w) => w.status === "active")
                    .map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name}
                      </option>
                    ))}
                </select>
                <p className="mt-1 text-xs text-slate-500">
                  Selected workflows must have a published Webhook trigger. New
                  leads also trigger active Lead Created workflows.
                </p>
                {workflows.error && (
                  <p role="alert" className="notice mt-2">
                    {workflows.error.message}
                  </p>
                )}
              </div>
              <div>
                <label htmlFor="webhook-destination">
                  Outgoing HTTPS destination (optional)
                </label>
                <input
                  id="webhook-destination"
                  type="url"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  maxLength={2048}
                  placeholder="https://receiver.example/events"
                />
                <p className="mt-1 text-xs text-slate-500">
                  The server operator must allowlist the exact public hostname.
                  Credentials and query strings are blocked.
                </p>
              </div>
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={deduplicates}
                  onChange={(e) => setDeduplicates(e.target.checked)}
                />
                <span>
                  The receiver guarantees deduplication by event ID.
                  <span className="mt-1 block text-xs font-normal text-slate-500">
                    Enable retries only when the receiver implements this
                    contract. Otherwise, an unknown delivery outcome stops for
                    investigation.
                  </span>
                </span>
              </label>
              <p className="text-xs text-slate-500">
                Signing credentials stay on the server. Follow
                docs/INTEGRATIONS.md to configure a sender. Settings are fixed
                when created; disable and replace a connection to change them.
              </p>
            </>
          )}
          {create.error && (
            <p role="alert" className="notice">
              {create.error.message}
            </p>
          )}
          {create.isSuccess && (
            <p role="status" className="text-sm text-teal-800">
              Integration saved.
            </p>
          )}
          <Button disabled={create.isPending}>
            <Cable size={16} />
            {create.isPending ? "Saving…" : "Add integration"}
          </Button>
        </form>
      )}
      {rows.isPending ? (
        <p aria-busy="true">Loading integrations…</p>
      ) : rows.error ? (
        <div role="alert" className="notice">
          {rows.error.message}
          <Button variant="outline" onClick={() => rows.refetch()}>
            Try again
          </Button>
        </div>
      ) : !rows.data?.items.length ? (
        <div className="panel p-10 text-center">
          <Cable className="mx-auto mb-3 text-slate-400" />
          <h2 className="font-semibold">No integrations yet</h2>
          <p className="mt-2 text-sm text-slate-500">
            An owner or admin can connect a public repository or add a signed
            webhook.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {rows.data.items.map((item) => (
            <Connection key={item.id} item={item} canManage={canManage} />
          ))}
        </div>
      )}
      {rows.data && rows.data.total > 25 && (
        <div className="mt-5 flex items-center gap-4">
          <Button
            variant="outline"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm">Page {page}</span>
          <Button
            variant="outline"
            disabled={page * 25 >= rows.data.total}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </>
  );
}

function Connection({
  item,
  canManage,
}: {
  item: Integration;
  canManage: boolean;
}) {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const refresh = () =>
    client.invalidateQueries({ queryKey: ["integrations", organization.id] });
  const test = useMutation({
    mutationFn: () =>
      api(`/integrations/${item.id}/test`, { method: "POST" }, organization.id),
    onSuccess: refresh,
  });
  const toggle = useMutation({
    mutationFn: () =>
      api(
        `/integrations/${item.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            expected_revision: item.revision,
            enabled: !item.enabled,
          }),
        },
        organization.id,
      ),
    onSuccess: refresh,
  });
  return (
    <section className="panel min-w-0 p-6" aria-label={item.name}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          {item.provider === "github" ? (
            <GitBranch size={22} className="mt-1 shrink-0 text-slate-500" />
          ) : (
            <Webhook size={22} className="mt-1 shrink-0 text-teal-700" />
          )}
          <div className="min-w-0">
            <h2 className="break-words text-lg font-semibold">{item.name}</h2>
            <p className="mt-1 break-all text-xs text-slate-500">
              {item.provider === "github"
                ? `${item.configuration.owner}/${item.configuration.repo}`
                : "Signed incoming / outgoing webhook"}
            </p>
          </div>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs ${item.enabled ? "bg-teal-50 text-teal-800" : "bg-slate-100 text-slate-600"}`}
        >
          {item.enabled ? "Enabled" : "Disabled"}
        </span>
      </div>
      <p className="mt-4 text-sm">
        Connection:{" "}
        <strong className="capitalize">
          {item.last_test_status.replaceAll("_", " ")}
        </strong>
        {item.last_test_at && (
          <span className="ml-2 text-xs text-slate-500">
            {new Date(item.last_test_at).toLocaleString()}
          </span>
        )}
      </p>
      {item.last_error && (
        <p className="notice mt-3" role="status">
          {item.last_error.replaceAll("_", " ")}
        </p>
      )}
      {item.last_result.full_name && (
        <div className="mt-3 rounded-lg bg-slate-50 p-4">
          <a
            className="font-medium text-teal-800 hover:underline"
            href={item.last_result.url}
            target="_blank"
            rel="noreferrer"
          >
            {item.last_result.full_name}
          </a>
          <p className="mt-1 text-sm text-slate-600">
            {item.last_result.description}
          </p>
          <p className="mt-2 text-xs text-slate-500">
            {item.last_result.stargazers_count ?? 0} stars · Live public API
            result
          </p>
        </div>
      )}
      {(test.error || toggle.error) && (
        <p role="alert" className="notice mt-3">
          {(test.error ?? toggle.error)?.message}
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {canManage && (
          <>
            <Button
              variant="outline"
              disabled={test.isPending || !item.enabled}
              onClick={() => test.mutate()}
            >
              {test.isPending ? "Checking…" : "Test connection"}
            </Button>
            <Button
              variant="outline"
              disabled={toggle.isPending}
              onClick={() => toggle.mutate()}
            >
              {item.enabled ? "Disable" : "Enable"}
            </Button>
          </>
        )}
        {item.provider === "webhook" && (
          <Button
            variant="outline"
            aria-expanded={expanded}
            onClick={() => setExpanded((x) => !x)}
          >
            {expanded ? "Hide events" : "View events & deliveries"}
          </Button>
        )}
      </div>
      {expanded && <WebhookHistory item={item} canManage={canManage} />}
    </section>
  );
}

function WebhookHistory({
  item,
  canManage,
}: {
  item: Integration;
  canManage: boolean;
}) {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const events = useQuery({
    queryKey: ["webhook-events", organization.id, item.id],
    queryFn: () =>
      api<{ items: Event[] }>(
        `/integrations/${item.id}/events`,
        {},
        organization.id,
      ),
    refetchInterval: 5000,
  });
  const deliveries = useQuery({
    queryKey: ["webhook-deliveries", organization.id, item.id],
    queryFn: () =>
      api<{ items: Delivery[] }>(
        `/integrations/${item.id}/deliveries`,
        {},
        organization.id,
      ),
    refetchInterval: 5000,
  });
  const send = useMutation({
    mutationFn: () =>
      api(
        `/integrations/${item.id}/deliveries`,
        {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID() },
          body: "{}",
        },
        organization.id,
      ),
    onSuccess: () =>
      client.invalidateQueries({
        queryKey: ["webhook-deliveries", organization.id, item.id],
      }),
  });
  return (
    <div className="mt-5 space-y-5 border-t border-slate-100 pt-5">
      <div>
        <p className="text-sm font-medium">Incoming endpoint</p>
        <code className="mt-2 block break-all rounded bg-slate-50 p-3 text-xs">
          /api/v1/webhooks/{item.id}
        </code>
        <p className="mt-2 text-xs text-slate-500">
          Requires timestamp and endpoint-bound HMAC signature. Events are
          limited to 64 KiB; IDs deduplicate exact retries.
        </p>
      </div>
      <div>
        <h3 className="text-sm font-semibold">Incoming events · latest 50</h3>
        {events.isPending ? (
          <p className="mt-2 text-sm" aria-busy="true">
            Loading events…
          </p>
        ) : events.error ? (
          <p role="alert" className="notice mt-2">
            {events.error.message}
          </p>
        ) : !events.data?.items.length ? (
          <p className="mt-2 text-sm text-slate-500">
            No signed events received.
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {events.data.items.map((e) => (
              <li
                key={e.id}
                className="flex flex-wrap justify-between gap-2 rounded bg-slate-50 p-3 text-xs"
              >
                <span className="break-all">{e.external_id}</span>
                {e.execution_id ? (
                  <Link
                    className="font-medium text-teal-800"
                    href={`/executions/${e.execution_id}`}
                  >
                    View execution →
                  </Link>
                ) : (
                  <span>Lead saved</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h3 className="text-sm font-semibold">
          Outgoing deliveries · latest 50
        </h3>
        <p className="mt-2 break-all text-xs text-slate-500">
          {item.configuration.destination ??
            "No outgoing destination configured."}
        </p>
        {canManage && item.configuration.destination && (
          <Button
            className="mt-3"
            variant="outline"
            disabled={send.isPending || !item.enabled}
            onClick={() => send.mutate()}
          >
            Send operational test event
          </Button>
        )}
        {send.error && (
          <p role="alert" className="notice mt-2">
            {send.error.message}
          </p>
        )}
        {send.isSuccess && (
          <p role="status" className="mt-2 text-xs text-teal-800">
            Test queued. Delivery updates below.
          </p>
        )}
        {deliveries.isPending ? (
          <p className="mt-2 text-sm" aria-busy="true">
            Loading deliveries…
          </p>
        ) : deliveries.error ? (
          <p role="alert" className="notice mt-2">
            {deliveries.error.message}
          </p>
        ) : !deliveries.data?.items.length ? (
          <p className="mt-2 text-sm text-slate-500">No outgoing events.</p>
        ) : (
          <ul className="mt-3 space-y-3">
            {deliveries.data.items.map((d) => (
              <li key={d.id} className="rounded bg-slate-50 p-3 text-xs">
                <p className="break-all font-medium">
                  {d.status} · {d.id}
                </p>
                {d.error_code && (
                  <p className="mt-1 text-amber-800">{d.error_code}</p>
                )}
                <ol className="mt-2 space-y-1">
                  {d.attempts.map((a) => (
                    <li key={a.number}>
                      Attempt {a.number}: {a.status}
                      {a.http_status ? ` · HTTP ${a.http_status}` : ""}
                      {a.uncertain ? " · Receiver outcome unknown" : ""}
                    </li>
                  ))}
                </ol>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
