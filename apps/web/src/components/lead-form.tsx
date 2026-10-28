"use client";

import { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { api, type Lead } from "@/lib/api";
import { useWorkspace } from "@/components/workspace";
import { LeadScoring } from "@/features/leads/lead-scoring";
import { Button } from "@/components/ui/button";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required.").max(150),
  email: z.email("Enter a valid email."),
  company: z.string().max(200),
  job_title: z.string().max(150),
  website: z.union([z.url(), z.literal("")]),
  industry: z.string().max(100),
  company_size: z.string().max(50),
  country: z.string().max(100),
  source: z.string().max(100),
  status: z.string(),
});
type Fields = z.infer<typeof schema>;
const fields: { key: keyof Fields; label: string; required?: boolean }[] = [
  { key: "name", label: "Full name", required: true },
  { key: "email", label: "Work email", required: true },
  { key: "company", label: "Company" },
  { key: "job_title", label: "Job title" },
  { key: "website", label: "Website" },
  { key: "industry", label: "Industry" },
  { key: "company_size", label: "Company size" },
  { key: "country", label: "Country" },
  { key: "source", label: "Lead source" },
];

export function LeadForm({
  lead,
  readOnly = false,
  onClose,
  onSaved,
}: {
  lead?: Lead;
  readOnly?: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const form = useForm<Fields>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: lead?.name ?? "",
      email: lead?.email ?? "",
      company: lead?.company ?? "",
      job_title: lead?.job_title ?? "",
      website: lead?.website ?? "",
      industry: lead?.industry ?? "",
      company_size: lead?.company_size ?? "",
      country: lead?.country ?? "",
      source: lead?.source ?? "",
      status: lead?.status ?? "new",
    },
  });
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const save = useMutation({
    mutationFn: async (data: Fields) => {
      const payload: Record<string, string | null> = { ...data };
      if (!lead) delete payload.status;
      for (const field of fields)
        if (!field.required && !payload[field.key]) payload[field.key] = null;
      return api<Lead>(
        lead ? `/leads/${lead.id}` : "/leads",
        { method: lead ? "PATCH" : "POST", body: JSON.stringify(payload) },
        organization.id,
      );
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["leads", organization.id] });
      onSaved();
    },
  });
  return (
    <dialog
      ref={dialog}
      onCancel={onClose}
      aria-labelledby="lead-form-title"
      className="m-auto max-h-[90vh] w-[min(640px,calc(100%-32px))] overflow-auto rounded-2xl border-0 bg-white p-0 text-slate-800 shadow-2xl backdrop:bg-slate-950/40"
    >
      <div className="flex items-start justify-between border-b border-slate-200 px-6 py-5">
        <div>
          <h2 id="lead-form-title" className="text-xl font-semibold">
            {readOnly ? "Lead details" : lead ? "Edit lead" : "Add a lead"}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {readOnly
              ? "The information saved in your workspace."
              : "Keep the details clear. Make the next step easier."}
          </p>
        </div>
        <button
          type="button"
          aria-label="Close lead details"
          className="rounded p-2 hover:bg-slate-100"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      <form
        onSubmit={form.handleSubmit((data) => save.mutate(data))}
        className="p-6"
      >
        <div className="grid gap-5 sm:grid-cols-2">
          {fields.map((field) => (
            <div
              key={field.key}
              className={field.key === "website" ? "sm:col-span-2" : ""}
            >
              <label htmlFor={`lead-${field.key}`}>
                {field.label}
                {field.required ? " *" : ""}
              </label>
              <input
                id={`lead-${field.key}`}
                required={field.required}
                readOnly={readOnly}
                type={
                  field.key === "email"
                    ? "email"
                    : field.key === "website"
                      ? "url"
                      : "text"
                }
                {...form.register(field.key)}
              />
              {form.formState.errors[field.key] && (
                <p className="field-error">
                  {form.formState.errors[field.key]?.message}
                </p>
              )}
            </div>
          ))}
          {lead && (
            <div>
              <label htmlFor="lead-status">Status</label>
              <select
                id="lead-status"
                disabled={readOnly}
                {...form.register("status")}
              >
                {[
                  "new",
                  "qualified",
                  "contacted",
                  "won",
                  "lost",
                  "archived",
                ].map((status) => (
                  <option key={status}>{status}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        {save.error && (
          <p role="alert" className="notice mt-5">
            {save.error.message}
          </p>
        )}
        {readOnly && lead && <LeadScoring lead={lead} />}
        <div className="mt-7 flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onClose}>
            {readOnly ? "Close" : "Cancel"}
          </Button>
          {!readOnly && (
            <Button disabled={save.isPending}>
              {save.isPending ? "Saving…" : "Save lead"}
            </Button>
          )}
        </div>
      </form>
    </dialog>
  );
}
