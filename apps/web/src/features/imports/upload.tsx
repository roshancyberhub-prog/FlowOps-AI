"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { FileUp } from "lucide-react";
import { api } from "@/lib/api";
import type { ImportJob, ImportPreview } from "@/lib/imports";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/workspace";

const fields = [
  { key: "name", label: "Full name", required: true },
  { key: "email", label: "Email", required: true },
  { key: "company", label: "Company" },
  { key: "job_title", label: "Job title" },
  { key: "industry", label: "Industry" },
  { key: "company_size", label: "Company size" },
  { key: "website", label: "Website" },
  { key: "country", label: "Country" },
  { key: "source", label: "Source" },
];
export function ImportUpload() {
  const { organization } = useWorkspace();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [inspection, setInspection] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [key, setKey] = useState(() => crypto.randomUUID());
  const preview = useMutation({
    mutationFn: () => {
      const body = new FormData();
      body.append("file", file!);
      return api<ImportPreview>(
        "/leads/imports/preview",
        { method: "POST", body },
        organization.id,
      );
    },
    onSuccess: (data) => {
      setInspection(data);
      setMapping(data.suggested_mapping);
      setKey(crypto.randomUUID());
    },
  });
  const start = useMutation({
    mutationFn: () => {
      const body = new FormData();
      body.append("file", file!);
      body.append(
        "column_mapping",
        JSON.stringify(
          Object.fromEntries(
            Object.entries(mapping).filter(([, value]) => value),
          ),
        ),
      );
      return api<ImportJob>(
        "/leads/imports",
        { method: "POST", body, headers: { "Idempotency-Key": key } },
        organization.id,
      );
    },
    onSuccess: (job) => router.push(`/imports/${job.id}`),
  });
  const tooLarge = file && file.size > 512 * 1024;
  return (
    <section className="panel mb-8 p-6">
      <div className="mb-4 flex items-center gap-3">
        <FileUp className="text-teal-700" />
        <h2 className="text-lg font-semibold">Import a CSV</h2>
      </div>
      <p className="mb-5 max-w-3xl text-sm text-slate-500">
        Upload a UTF-8 CSV up to 512 KiB and 2,000 records. New valid leads are
        inserted. Duplicates within the file or workspace, including archived
        leads, are skipped.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          start.mutate();
        }}
      >
        <fieldset disabled={start.isPending || preview.isPending}>
          <div className="flex flex-wrap items-end gap-4">
            <div className="max-w-lg flex-1">
              <label htmlFor="import-file">CSV file</label>
              <input
                id="import-file"
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setInspection(null);
                  setMapping({});
                  preview.reset();
                  start.reset();
                  setKey(crypto.randomUUID());
                }}
              />
            </div>
            <Button
              type="button"
              variant="outline"
              disabled={!file || !!tooLarge}
              onClick={() => preview.mutate()}
            >
              {preview.isPending ? "Reading…" : "Preview columns"}
            </Button>
            <a
              className="mb-2 text-xs font-semibold text-teal-800 hover:underline"
              href="/sample-leads.csv"
              download
            >
              Download fictional sample
            </a>
          </div>
          {tooLarge && (
            <p role="alert" className="notice mt-4">
              Choose a file smaller than 512 KiB.
            </p>
          )}
          {inspection && (
            <div className="mt-6">
              <h3 className="font-semibold">
                Map columns · {inspection.row_count} records
              </h3>
              <p className="mt-2 text-xs text-slate-500">
                Choose each source column once. Name and email are required.
                Unmapped columns are ignored.
              </p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {fields.map((field) => (
                  <div key={field.key}>
                    <label htmlFor={`map-${field.key}`}>
                      {field.label}
                      {field.required ? " *" : ""}
                    </label>
                    <select
                      id={`map-${field.key}`}
                      required={field.required}
                      value={mapping[field.key] ?? ""}
                      onChange={(event) => {
                        setMapping({
                          ...mapping,
                          [field.key]: event.target.value,
                        });
                        setKey(crypto.randomUUID());
                      }}
                    >
                      <option value="">
                        {field.required ? "Choose column" : "Skip field"}
                      </option>
                      {inspection.headers.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
              <Button className="mt-5" disabled={start.isPending}>
                {start.isPending ? "Starting…" : "Start CSV import"}
              </Button>
            </div>
          )}
        </fieldset>
        {(preview.error || start.error) && (
          <p role="alert" className="notice mt-4">
            {(start.error || preview.error)?.message}
          </p>
        )}
      </form>
    </section>
  );
}
