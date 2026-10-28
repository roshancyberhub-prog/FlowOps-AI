"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ListChecks,
  ShieldCheck,
  SlidersHorizontal,
  ArrowUpRight,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Users,
  UsersRound,
} from "lucide-react";
import { api, ApiError, type Organization, type User } from "@/lib/api";
import { Button } from "@/components/ui/button";

const Context = createContext<{
  organization: Organization;
  user: User;
} | null>(null);
export function useWorkspace() {
  const context = useContext(Context);
  if (!context) throw new Error("Workspace is required");
  return context;
}

export function Workspace({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const client = useQueryClient();
  const [selected, setSelected] = useState(() =>
    typeof window === "undefined"
      ? ""
      : (localStorage.getItem("flowops.workspace") ?? ""),
  );
  const [name, setName] = useState("");
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/users/me"),
  });
  const orgs = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api<Organization[]>("/organizations"),
    enabled: me.isSuccess,
  });
  const create = useMutation({
    mutationFn: () =>
      api<Organization>("/organizations", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: (org) => {
      setSelected(org.id);
      localStorage.setItem("flowops.workspace", org.id);
      setName("");
      client.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
  const logout = useMutation({
    mutationFn: () => api("/auth/session/logout", { method: "POST" }),
    onSuccess: () => {
      client.clear();
      router.replace("/login");
    },
  });
  useEffect(() => {
    if (me.error instanceof ApiError && me.error.status === 401)
      router.replace("/login");
  }, [me.error, router]);

  const loading = me.isPending || (me.isSuccess && orgs.isPending);
  if (loading)
    return (
      <main className="grid min-h-screen place-items-center" aria-busy="true">
        <p className="text-slate-500">Opening your workspace…</p>
      </main>
    );
  if (me.error || orgs.error)
    return (
      <main className="mx-auto max-w-lg p-8">
        <div role="alert" className="notice">
          {(me.error ?? orgs.error)?.message}
        </div>
        <Button
          className="mt-4"
          onClick={() => {
            me.refetch();
            orgs.refetch();
          }}
        >
          Try again
        </Button>
      </main>
    );
  if (!me.data || !orgs.data) return null;
  if (!orgs.data.length)
    return (
      <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center p-6">
        <GitBranch className="mb-6 text-teal-700" size={36} />
        <h1 className="text-3xl font-semibold">
          Make room for better operations.
        </h1>
        <p className="my-4 text-slate-500">
          Create a workspace to start managing your leads.
        </p>
        <form
          className="panel space-y-4 p-6"
          onSubmit={(event) => {
            event.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <label htmlFor="workspace-name">Workspace name</label>
            <input
              id="workspace-name"
              required
              maxLength={120}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          {create.error && (
            <p role="alert" className="notice">
              {create.error.message}
            </p>
          )}
          <Button disabled={create.isPending}>Create workspace</Button>
        </form>
        <Button
          variant="ghost"
          className="mt-4"
          onClick={() => logout.mutate()}
        >
          Sign out
        </Button>
      </main>
    );
  const organization =
    orgs.data.find((org) => org.id === selected) ?? orgs.data[0];
  const navigation = [
    { href: "/", label: "Overview", icon: LayoutDashboard },
    { href: "/workflows", label: "Workflows", icon: GitBranch },
    { href: "/leads", label: "Leads", icon: Users },
    { href: "/scoring", label: "Scoring profiles", icon: SlidersHorizontal },
    { href: "/executions", label: "Executions", icon: ListChecks },
    { href: "/approvals", label: "Approvals", icon: ShieldCheck },
    { href: "/team", label: "Team & workspace", icon: UsersRound },
    ...(organization.role === "owner" || organization.role === "admin"
      ? [{ href: "/activity", label: "Audit activity", icon: Activity }]
      : []),
  ];
  const activeNavigation = navigation.find(
    (item) =>
      item.href === pathname ||
      (item.href !== "/" && pathname.startsWith(`${item.href}/`)),
  );
  return (
    <Context.Provider value={{ organization, user: me.data }}>
      <div className="grid min-h-screen grid-cols-[minmax(0,1fr)] lg:grid-cols-[232px_minmax(0,1fr)]">
        <aside className="flex min-w-0 flex-col bg-[#12232d] text-slate-300 lg:sticky lg:top-0 lg:h-screen">
          <Link
            href="/"
            className="flex items-center gap-2 px-6 py-7 text-xl font-semibold text-white"
          >
            <span className="rounded-lg bg-teal-400 p-1.5 text-slate-950">
              <GitBranch size={22} />
            </span>
            FlowOps <span className="font-normal text-teal-300">AI</span>
          </Link>
          <div className="px-4 pb-5">
            <label htmlFor="workspace" className="text-slate-400">
              Workspace
            </label>
            <select
              id="workspace"
              value={organization.id}
              onChange={(event) => {
                setSelected(event.target.value);
                localStorage.setItem("flowops.workspace", event.target.value);
              }}
              className="text-sm"
            >
              {orgs.data.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
          </div>
          <p className="px-6 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Workspace
          </p>
          <nav
            aria-label="Main navigation"
            className="flex gap-1 overflow-auto px-3 py-3 lg:flex-col"
          >
            {navigation.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                aria-current={
                  activeNavigation?.href === href ? "page" : undefined
                }
                className={`flex min-h-11 shrink-0 items-center gap-3 rounded-lg px-3 text-sm transition-colors ${activeNavigation?.href === href ? "bg-teal-400/10 text-teal-200" : "hover:bg-white/5 hover:text-white"}`}
              >
                <Icon size={17} />
                {label}
              </Link>
            ))}
          </nav>
          <div className="hidden flex-1 lg:block" />
          <a
            href="https://github.com/roshancyberhub-prog/FlowOps-AI"
            className="mx-4 mb-5 hidden items-center justify-between rounded-lg border border-white/10 p-3 text-xs hover:bg-white/5 lg:flex"
            target="_blank"
            rel="noreferrer"
          >
            Project documentation
            <ArrowUpRight size={14} />
          </a>
          <div className="flex items-center gap-3 border-t border-white/10 p-4">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-700 text-sm font-semibold text-white">
              {me.data.display_name.slice(0, 1).toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">
                {me.data.display_name}
              </p>
              <p className="text-xs capitalize text-slate-400">
                {organization.role}
              </p>
            </div>
            <button
              aria-label="Sign out"
              title="Sign out"
              className="rounded p-2 hover:bg-white/10"
              disabled={logout.isPending}
              onClick={() => logout.mutate()}
            >
              <LogOut size={17} />
            </button>
          </div>
        </aside>
        <div className="min-w-0">
          <header className="flex min-h-16 items-center justify-between border-b border-slate-200 bg-white px-6 lg:px-10">
            <span className="text-xs text-slate-500">
              Workspace <span className="mx-2 text-slate-300">/</span>{" "}
              <span className="font-medium text-slate-700">
                {activeNavigation?.label}
              </span>
            </span>
            <span className="rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-[11px] font-medium text-teal-800">
              Development preview
            </span>
          </header>
          {logout.error && (
            <p role="alert" className="notice m-4">
              {logout.error.message}
            </p>
          )}
          <main
            key={organization.id}
            className="mx-auto min-w-0 max-w-[1500px] px-5 py-8 lg:px-10"
          >
            {children}
          </main>
        </div>
      </div>
    </Context.Provider>
  );
}
