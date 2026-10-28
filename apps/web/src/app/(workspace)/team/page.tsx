"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, UsersRound } from "lucide-react";
import { api } from "@/lib/api";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";

type Member = {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: string;
};

export default function Team() {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [workspaceName, setWorkspaceName] = useState("");
  const [notice, setNotice] = useState("");
  const canManage = ["owner", "admin"].includes(organization.role);
  const prefix = `/organizations/${organization.id}/members`;
  const members = useQuery({
    queryKey: ["members", organization.id],
    queryFn: () => api<Member[]>(prefix, {}, organization.id),
  });
  const add = useMutation({
    mutationFn: () =>
      api(
        prefix,
        { method: "POST", body: JSON.stringify({ email, role }) },
        organization.id,
      ),
    onSuccess: () => {
      setEmail("");
      setNotice("Member added.");
      client.invalidateQueries({ queryKey: ["members", organization.id] });
    },
  });
  const update = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      api(
        `${prefix}/${id}`,
        { method: "PATCH", body: JSON.stringify({ role }) },
        organization.id,
      ),
    onSuccess: () => {
      setNotice("Role updated.");
      client.invalidateQueries({ queryKey: ["members", organization.id] });
      client.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
  const create = useMutation({
    mutationFn: () =>
      api("/organizations", {
        method: "POST",
        body: JSON.stringify({ name: workspaceName }),
      }),
    onSuccess: () => {
      setWorkspaceName("");
      setNotice("Workspace created. Select it from the workspace menu.");
      client.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
  return (
    <>
      <p className="eyebrow mb-2">Good work is a team effort</p>
      <h1 className="text-3xl font-semibold tracking-tight">
        Team & workspace
      </h1>
      <p className="mb-8 mt-2 text-slate-500">
        Manage access to {organization.name}.
      </p>
      {notice && (
        <p
          role="status"
          className="mb-5 rounded-lg border border-teal-200 bg-teal-50 p-3 text-teal-800"
        >
          {notice}
        </p>
      )}
      {(add.error || update.error || create.error) && (
        <p role="alert" className="notice mb-5">
          {(add.error || update.error || create.error)?.message}
        </p>
      )}
      <section className="panel mb-6 overflow-hidden">
        <div className="flex items-center gap-3 border-b border-slate-200 p-5">
          <UsersRound size={19} className="text-teal-700" />
          <h2 className="font-semibold">Workspace members</h2>
        </div>
        {members.isPending ? (
          <p className="p-8" aria-busy>
            Loading members…
          </p>
        ) : members.error ? (
          <div className="p-6">
            <p role="alert" className="notice">
              {members.error.message}
            </p>
            <Button
              variant="outline"
              className="mt-3"
              onClick={() => members.refetch()}
            >
              Try again
            </Button>
          </div>
        ) : (
          <div className="overflow-auto">
            <table>
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Email</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {members.data?.map((member) => (
                  <tr key={member.id}>
                    <td className="font-medium">{member.display_name}</td>
                    <td className="text-sm text-slate-500">{member.email}</td>
                    <td className="w-40">
                      {canManage &&
                      member.role !== "owner" &&
                      (organization.role === "owner" ||
                        member.role !== "admin") ? (
                        <>
                          <label
                            className="sr-only"
                            htmlFor={`role-${member.id}`}
                          >
                            Role for {member.display_name}
                          </label>
                          <select
                            id={`role-${member.id}`}
                            value={member.role}
                            disabled={update.isPending}
                            onChange={(event) => {
                              if (
                                window.confirm(
                                  `Change ${member.display_name} to ${event.target.value}?`,
                                )
                              )
                                update.mutate({
                                  id: member.id,
                                  role: event.target.value,
                                });
                            }}
                          >
                            <option value="viewer">Viewer</option>
                            <option value="member">Member</option>
                            {organization.role === "owner" && (
                              <option value="admin">Admin</option>
                            )}
                          </select>
                        </>
                      ) : (
                        <span className="capitalize">{member.role}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <div className="grid gap-6 xl:grid-cols-2">
        {canManage && (
          <section className="panel p-6">
            <h2 className="text-base font-semibold">Add a team member</h2>
            <p className="mb-6 mt-2 text-sm text-slate-500">
              They must create a FlowOps account first. Adding them grants
              immediate workspace access.
            </p>
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                add.mutate();
              }}
            >
              <div>
                <label htmlFor="member-email">Member email</label>
                <input
                  type="email"
                  id="member-email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
              <div>
                <label htmlFor="member-role">Access role</label>
                <select
                  id="member-role"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                >
                  <option value="viewer">Viewer — read only</option>
                  <option value="member">Member — manage leads</option>
                  {organization.role === "owner" && (
                    <option value="admin">Admin — manage leads and team</option>
                  )}
                </select>
              </div>
              <Button disabled={add.isPending}>
                <Plus size={16} />
                Add member
              </Button>
            </form>
          </section>
        )}
        <section className="panel p-6">
          <h2 className="text-base font-semibold">Create another workspace</h2>
          <p className="mb-6 mt-2 text-sm text-slate-500">
            Keep a separate team and lead pipeline in a new workspace.
          </p>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              create.mutate();
            }}
          >
            <div>
              <label htmlFor="new-workspace">Workspace name</label>
              <input
                id="new-workspace"
                required
                maxLength={120}
                value={workspaceName}
                onChange={(event) => setWorkspaceName(event.target.value)}
              />
            </div>
            <Button variant="outline" disabled={create.isPending}>
              Create workspace
            </Button>
          </form>
        </section>
      </div>
    </>
  );
}
